"""Tailwind integration backed by the application's shared Flask-Node manager."""

import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakKeyDictionary

from flask import Blueprint, Flask, current_app, render_template
from flask_node import ConfigurationError, Node, NodeManager, PackageNotFoundError

from .cli import tailwind

DEFAULT_OUTPUT_PATH = "css/style.css"
DEFAULT_TEMPLATE_FOLDER = "templates"
DEFAULT_INPUT_PATH = "tailwind/input.css"
TAILWIND_PACKAGES = ("tailwindcss", "@tailwindcss/cli")


@dataclass(frozen=True)
class TailwindState:
    node: NodeManager
    input_path: Path
    output_css_path: str
    static_folder: Path
    template_path: Path


class TailwindCSS:
    def __init__(self, app: Flask | None = None):
        self._states: WeakKeyDictionary = WeakKeyDictionary()
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        if "tailwind" in app.extensions:
            raise RuntimeError(
                "This extension is already registered on this Flask app."
            )
        if not app.static_folder:
            raise AttributeError("Given app static_folder must be set.")
        output = app.config.get("TAILWIND_OUTPUT_PATH", DEFAULT_OUTPUT_PATH)
        input_value = app.config.get("TAILWIND_INPUT_PATH", DEFAULT_INPUT_PATH)
        templates = app.config.get("TAILWIND_TEMPLATE_FOLDER", DEFAULT_TEMPLATE_FOLDER)
        for key, value in (
            ("TAILWIND_OUTPUT_PATH", output),
            ("TAILWIND_INPUT_PATH", input_value),
            ("TAILWIND_TEMPLATE_FOLDER", templates),
        ):
            if not isinstance(value, (str, Path)) or not str(value).strip():
                raise ConfigurationError(f"{key} must be a nonempty path.")
        output_path = Path(output)
        if output_path.is_absolute() or ".." in output_path.parts:
            raise ConfigurationError(
                "TAILWIND_OUTPUT_PATH must be inside app.static_folder."
            )
        self._legacy_config(app)
        if "node" not in app.extensions:
            Node().init_app(app)
        node = Node().get_manager(app)
        for package in TAILWIND_PACKAGES:
            node.require(package, "^4")
        input_path = Path(input_value)
        if not input_path.is_absolute():
            input_path = node.directory / input_path
        self._states[app] = TailwindState(
            node,
            input_path.resolve(),
            str(output),
            Path(app.static_folder),
            (Path(app.root_path) / templates).resolve(),
        )
        app.extensions["tailwind"] = self
        app.register_blueprint(
            Blueprint("tailwind", __name__, template_folder="templates")
        )
        app.add_template_global(self._css_tag, "tailwind_css")
        app.cli.add_command(tailwind)

    @staticmethod
    def _legacy_config(app: Flask) -> None:
        aliases = {
            "TAILWIND_CWD": "NODE_DIR",
            "TAILWIND_NPM_BIN_PATH": "NODE_NPM_BIN",
            "TAILWIND_NPX_BIN_PATH": "NODE_NPX_BIN",
        }
        for old, new in aliases.items():
            if old not in app.config:
                continue
            warnings.warn(
                f"{old} is deprecated; configure {new} before Node initialization.",
                FutureWarning,
                stacklevel=3,
            )
            value = app.config[old]
            if not isinstance(value, (str, Path)) or not str(value).strip():
                raise ConfigurationError(f"{old} must be a nonempty path.")
            if old == "TAILWIND_CWD":
                value = Path(value).resolve()
            if "node" in app.extensions:
                manager = Node().get_manager(app)
                existing = {
                    "NODE_DIR": manager.directory,
                    "NODE_NPM_BIN": manager.npm_bin,
                    "NODE_NPX_BIN": manager.npx_bin,
                }[new]
            else:
                existing = app.config.get(new, value)
                if new == "NODE_DIR":
                    existing = Path(existing)
                    if not existing.is_absolute():
                        existing = Path(app.root_path) / existing
                    existing = existing.resolve()
            if existing != value:
                raise ConfigurationError(
                    f"{old} conflicts with {new}; remove {old} and configure Flask-Node."
                )
            if "node" not in app.extensions:
                app.config[new] = value

    def _state(self) -> TailwindState:
        app = current_app._get_current_object()
        if app not in self._states:
            raise ConfigurationError(
                "Initialize TailwindCSS on the current Flask application."
            )
        return self._states[app]

    @property
    def node(self) -> NodeManager:
        return self._state().node

    @property
    def output_css_path(self) -> str:
        return self._state().output_css_path

    def get_input_path(self) -> Path:
        return self._state().input_path

    def get_output_path(self) -> Path:
        """Retain the historical relative output path for existing Python callers."""
        state = self._state()
        return (
            state.static_folder.relative_to(state.static_folder.parent.parent)
            / state.output_css_path
        )

    def get_absolute_output_path(self) -> Path:
        state = self._state()
        return state.static_folder / state.output_css_path

    def input_css_str(self) -> str:
        state = self._state()
        source = os.path.relpath(state.template_path, state.input_path.parent).replace(
            os.sep, "/"
        )
        # Explicitly resolve the import to the shared environment, including external input files.
        stylesheet = self.node.resolve("tailwindcss", "index.css")
        css_import = os.path.relpath(stylesheet, state.input_path.parent).replace(
            os.sep, "/"
        )
        if not css_import.startswith("."):
            css_import = "./" + css_import
        return render_template(
            "input.css.jinja",
            css_import=json.dumps(css_import),
            source=json.dumps(source + "/"),
        )

    def initialize(self) -> None:
        self.node.install(capture_output=False)
        path = self.get_input_path()
        if not path.exists():
            contents = self.input_css_str()
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("x", encoding="utf-8") as stream:
                    stream.write(contents)
            except FileExistsError:
                pass

    def ensure_initialized(self) -> None:
        try:
            for package in TAILWIND_PACKAGES:
                self.node.package(package)
        except PackageNotFoundError:
            self.initialize()
            return
        if not self.get_input_path().is_file():
            self.initialize()

    def run(self, *args: str, watch: bool = False):
        self.ensure_initialized()
        output = self.get_absolute_output_path()
        output.parent.mkdir(parents=True, exist_ok=True)
        return self.node.npx(
            "@tailwindcss/cli",
            "-i",
            str(self.get_input_path()),
            "-o",
            str(output),
            "--watch" if watch else "--minify",
            *args,
            capture_output=False,
        )

    def _css_tag(self) -> str:
        return render_template("load.jinja", filename=self.output_css_path)
