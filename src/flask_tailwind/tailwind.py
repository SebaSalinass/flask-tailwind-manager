"""Tailwind integration backed by the application's shared Flask-Node manager."""

import warnings
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakKeyDictionary

from flask import Blueprint, Flask, current_app, render_template
from flask_node import ConfigurationError, Node, NodeManager, PackageNotFoundError
from jinja2 import Environment, PackageLoader, StrictUndefined

from .cli import tailwind
from .integrations import REGISTRY, Integration, select_integrations
from .paths import css_string, package_path, relative_css_path

DEFAULT_OUTPUT_PATH = "css/style.css"
DEFAULT_TEMPLATE_FOLDER = "templates"
DEFAULT_INPUT_PATH = "src/input.css"
TAILWIND_PACKAGES = ("tailwindcss", "@tailwindcss/cli")

# Source generation must not inherit application templates or request context.
_internal_templates = Environment(
    loader=PackageLoader("flask_tailwind", "templates"),
    autoescape=False,
    undefined=StrictUndefined,
)


@dataclass(frozen=True)
class TailwindState:
    node: NodeManager
    input_path: Path
    output_css_path: str
    static_folder: Path
    template_path: Path | None
    integrations: tuple[Integration, ...]


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
        templates = app.config.get("TAILWIND_TEMPLATE_FOLDER", app.template_folder)
        enabled = select_integrations(app.config.get("TAILWIND_INTEGRATIONS", []))
        for key, value in (
            ("TAILWIND_OUTPUT_PATH", output),
            ("TAILWIND_INPUT_PATH", input_value),
        ):
            if not isinstance(value, (str, Path)) or not str(value).strip():
                raise ConfigurationError(f"{key} must be a nonempty path.")
        if templates is not None and (
            not isinstance(templates, (str, Path)) or not str(templates).strip()
        ):
            raise ConfigurationError(
                "TAILWIND_TEMPLATE_FOLDER must be a nonempty path or None."
            )
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
        for integration in enabled:
            for requirement in integration.packages:
                node.require(requirement.name, requirement.version, dev=requirement.dev)
            for asset in integration.assets:
                node.register_asset(asset.package, asset.source, asset.destination)
        input_path = Path(input_value)
        if not input_path.is_absolute():
            input_path = Path(app.static_folder) / input_path
        self._states[app] = TailwindState(
            node,
            input_path.resolve(),
            str(output),
            Path(app.static_folder),
            (Path(app.root_path) / templates).resolve()
            if templates is not None
            else None,
            enabled,
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

    @property
    def input_path(self) -> Path:
        return self.get_input_path()

    @property
    def integrations(self) -> tuple[Integration, ...]:
        return self._state().integrations

    def node_path(self, package: str, path: str) -> str:
        return package_path(self.node, package, path, self.input_path.parent)

    def source(self, package: str, path: str) -> str:
        return f"@source {css_string(self.node_path(package, path))};"

    def import_package(self, package: str, path: str) -> str:
        return f"@import {css_string(self.node_path(package, path))};"

    def plugin(self, package: str, subpath: str | None = None) -> str:
        target = self.node.resolve_entry(package, subpath)
        return (
            f"@plugin {css_string(relative_css_path(target, self.input_path.parent))};"
        )

    def integration_config(self, name: str) -> str:
        if name not in REGISTRY:
            raise ConfigurationError(
                f"Unknown integration {name!r}. Available: {', '.join(sorted(REGISTRY))}."
            )
        integration = REGISTRY[name]
        status = (
            "enabled" if integration in self.integrations else "available, not enabled"
        )
        lines = [
            f"{name} integration ({status})",
            f"Tailwind input: {self.input_path}",
            "",
            "Required npm packages:",
        ]
        lines.extend(f"  {r.name}@{r.version}" for r in integration.packages)
        lines.extend(["", "Required Tailwind configuration:"])
        # CSS imports precede other directives so their ordering remains valid.
        lines.extend(
            self.import_package(p.package, p.path) for p in integration.imports
        )
        lines.extend(self.source(p.package, p.path) for p in integration.sources)
        lines.extend(self.plugin(p.package, p.subpath) for p in integration.plugins)
        lines.extend(["", "Browser assets:"])
        registered = self.node.assets
        lines.extend(
            f"  {a.destination} ({'registered' if any(x.package == a.package and x.source == a.source and x.destination == a.destination for x in registered) else 'not registered'})"
            for a in integration.assets
        )
        if not integration.assets:
            lines.append("  None")
        return "\n".join(lines)

    def paths(self) -> dict[str, str | None]:
        state = self._state()
        return {
            "Tailwind input": str(self.input_path),
            "Tailwind output": str(self.get_absolute_output_path()),
            "Flask templates": str(state.template_path)
            if state.template_path
            else None,
            "Flask static": str(state.static_folder),
            "Node environment": str(self.node.directory),
        }

    def input_css_str(self) -> str:
        state = self._state()
        source = (
            css_string(
                relative_css_path(state.template_path, self.input_path.parent) + "/"
            )
            if state.template_path
            else None
        )
        return _internal_templates.get_template("input.css.jinja").render(
            css_import=css_string(self.node_path("tailwindcss", "index.css")),
            source=source,
        )

    def initialize(self) -> None:
        try:
            for package in TAILWIND_PACKAGES:
                self.node.package(package)
        except PackageNotFoundError:
            self.node.install(capture_output=False)
        path = self.input_path
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
