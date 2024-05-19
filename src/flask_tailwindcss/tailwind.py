from typing import Optional
from pathlib import Path
from flask import Flask, Blueprint, render_template
from .console import ConsoleInterface, DEFAULT_NPM_BIN_PATH, DEFAULT_NPX_BIN_PATH
from .cli import tailwind

DEFAULT_CWD = ".tailwind"
DEFAULT_OUTPUT_PATH = "css/style.css"
DEFAULT_TEMPLATE_FOLDER = "templates"


class TailwindCSS:
    cwd: str = DEFAULT_CWD
    npm_bin_path: str = DEFAULT_NPM_BIN_PATH
    npx_bin_path: str = DEFAULT_NPX_BIN_PATH
    output_css_path: str = DEFAULT_OUTPUT_PATH
    template_folder: str = DEFAULT_TEMPLATE_FOLDER
    app_static_folder: Optional[str] = None

    def __init__(self, app: Optional[Flask] = None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        if "tailwind" in app.extensions:
            raise RuntimeError(
                "This extension is already registered on this Flask app."
            )
        app.extensions["tailwind"] = self
        self.cwd = app.config.get("TAILWIND_CWD", DEFAULT_CWD)
        self.output_css_path: str = app.config.get(
            "TAILWIND_OUTPUT_PATH", DEFAULT_OUTPUT_PATH
        )
        self.npm_bin_path: str = app.config.get(
            "TAILWIND_NPM_BIN_PATH", DEFAULT_NPM_BIN_PATH
        )
        self.npx_bin_path: str = app.config.get(
            "TAILWIND_NPX_BIN_PATH", DEFAULT_NPX_BIN_PATH
        )
        self.template_folder: str = app.config.get(
            "TAILWIND_TEMPLATE_FOLDER", DEFAULT_TEMPLATE_FOLDER
        )

        if not app.static_folder:
            raise AttributeError("Given app static_folder must be setted.")

        self.app_static_folder = app.static_folder
        self.app_name = app.name
        self.__register_blueprint(app)
        self.__register_app_global(app)
        self.__register_tailwind_command(app)

    def __register_tailwind_command(self, app: Flask) -> None:
        app.cli.add_command(tailwind)

    def get_console_interface(self) -> ConsoleInterface:
        return ConsoleInterface(self.cwd, self.npm_bin_path, self.npx_bin_path)

    def node_config_starter_path(self) -> Path:
        return Path(__file__).parent / "starter"

    def node_destination_path(self) -> Path:
        return Path(self.cwd)

    def get_output_path(self) -> Path:
        if not self.app_static_folder:
            raise AttributeError(
                "There is no `app_static_folder` set. You must call `init_app` method or pass the app on extension creation."
            )
        static_path = Path(self.app_static_folder)
        static_relative = static_path.relative_to(static_path.parent.parent)
        output_path = static_relative / self.output_css_path
        return output_path

    def package_json_str(self) -> str:
        app_name = self.app_name or "tailwind-app"
        output_path = self.get_output_path()
        return render_template(
            "package.json.jinja", app_name=app_name, output_path=output_path
        )

    def tailwind_config_js_str(self) -> str:
        app_name = self.app_name or "tailwind-app"
        return render_template(
            "tailwind.config.js.jinja",
            app_name=app_name,
            templates_folder=self.template_folder,
        )

    def __tailwind_css_tag(self) -> str:
        return render_template("load.jinja", filename=self.output_css_path)

    def __register_app_global(self, app: Flask) -> None:
        app.add_template_global(self.__tailwind_css_tag, "tailwind_css")

    def __register_blueprint(self, app: Flask) -> None:
        app.register_blueprint(
            Blueprint(
                name="tailwind", import_name=__name__, template_folder="templates"
            )
        )
