import json
import shutil
from pathlib import Path, PureWindowsPath
from unittest.mock import Mock

import pytest
from flask import Flask
from flask_node import (
    AssetResolutionError,
    CommandResult,
    CommandRunner,
    ConfigurationError,
    Node,
)

from flask_tailwind import TailwindCSS
from flask_tailwind.integrations import REGISTRY
from flask_tailwind.paths import css_string, relative_css_path


def package(manager, name, files=(), main="index.js", exports=None):
    root = manager.directory / "node_modules" / name
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"name": name, "version": "1.0.0", "main": main}
    if exports is not None:
        manifest["exports"] = exports
    (root / "package.json").write_text(json.dumps(manifest))
    for file in files:
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('throw new Error("Package code must never execute");')
    return root


@pytest.fixture
def integrated(tmp_path):
    runner = Mock(spec=CommandRunner)

    def execute(executable, args, *, cwd, capture_output):
        # Exercise Flask-Node's real entry-resolution boundary without spawning Node.
        assert executable == "node"
        specifier = args[-1]
        entries = {
            "daisyui": ("daisyui", "index.js"),
            "flowbite/plugin": ("flowbite", "plugin.js"),
            "@tailwindcss/forms": ("@tailwindcss/forms", "src/index.js"),
        }
        name, entry = entries[specifier]
        return CommandResult(
            (executable, *args),
            0,
            json.dumps({"path": str(cwd / "node_modules" / name / entry)}),
        )

    runner.run.side_effect = execute
    app = Flask(
        __name__,
        root_path=str(tmp_path / "app"),
        static_folder="public",
        template_folder="views",
    )
    app.config.update(
        NODE_DIR=tmp_path / "tools",
        TAILWIND_INTEGRATIONS=["preline", "flowbite", "daisyui", "preline"],
    )
    Node(app, runner=runner)
    extension = TailwindCSS(app)
    manager = app.extensions["node"]
    runner.run.assert_not_called()
    assert not manager.directory.exists()
    package(manager, "preline", ["variants.css", "dist/preline.js"])
    package(manager, "flowbite", ["plugin.js", "dist/flowbite.min.js"])
    package(manager, "daisyui", ["index.js"])
    package(manager, "@tailwindcss/forms", ["src/index.js"], main="src/index.js")
    package(manager, "tailwindcss", ["index.css"])
    package(manager, "@tailwindcss/cli")
    return app, extension, runner


def test_registry_and_declarations(integrated):
    app, extension, runner = integrated
    assert set(REGISTRY) == {"preline", "flowbite", "daisyui"}
    with pytest.raises(TypeError):
        REGISTRY["other"] = REGISTRY["preline"]
    with app.app_context():
        assert [item.name for item in extension.integrations] == [
            "daisyui",
            "flowbite",
            "preline",
        ]
        requirements = extension.node.requirements
        assert requirements["preline"].version == "^3"
        assert requirements["@tailwindcss/forms"].version == "^0.5"
        assert requirements["flowbite"].version == "^3"
        assert requirements["daisyui"].version == "^5"
        assert len(extension.node.assets) == 2
    runner.run.assert_not_called()


@pytest.mark.parametrize("names", [["unknown"], "preline", [None]])
def test_bad_integrations(tmp_path, names):
    app = Flask(__name__, root_path=str(tmp_path))
    app.config["TAILWIND_INTEGRATIONS"] = names
    with pytest.raises(ConfigurationError, match="integration"):
        TailwindCSS(app)
    assert not app.extensions


def test_application_source_and_template_defaults(integrated):
    app, _, runner = integrated
    cli = app.test_cli_runner()
    result = cli.invoke(args=["tailwind", "init"])
    assert result.exit_code == 0, result.output
    path = Path(app.static_folder) / "src/input.css"
    assert path.exists()
    css = path.read_text()
    assert 'source("../../views/")' in css
    assert "belongs to your application" in css
    assert "preline" not in css  # integrations are rendered for manual application
    path.write_text("/* developer owns this */")
    result = cli.invoke(args=["tailwind", "init"])
    assert result.exit_code == 0, result.output
    assert path.read_text() == "/* developer owns this */"
    runner.run.assert_not_called()  # already synchronized packages do not reinstall


def test_relative_custom_input_and_no_templates(tmp_path):
    app = Flask(
        __name__, root_path=str(tmp_path), static_folder="assets", template_folder=None
    )
    app.config["TAILWIND_INPUT_PATH"] = "styles/tailwind.css"
    ext = TailwindCSS(app)
    package(app.extensions["node"], "tailwindcss", ["index.css"])
    with app.app_context():
        assert ext.input_path == tmp_path / "assets/styles/tailwind.css"
        assert "source(" not in ext.input_css_str()
        assert ext.paths()["Flask templates"] is None


def test_paths_and_directives(integrated):
    app, ext, runner = integrated
    with app.app_context():
        assert (
            ext.node_path("preline", "dist/*.js")
            == "../../../tools/node_modules/preline/dist/*.js"
        )
        assert (
            ext.source("preline", "dist/*.js")
            == '@source "../../../tools/node_modules/preline/dist/*.js";'
        )
        assert (
            ext.import_package("preline", "variants.css")
            == '@import "../../../tools/node_modules/preline/variants.css";'
        )
        assert ext.node_path("@tailwindcss/forms", "src/index.js").endswith(
            "/@tailwindcss/forms/src/index.js"
        )
        assert ext.source("flowbite", "**/*.js").endswith('/flowbite/**/*.js";')
        assert ext.plugin("daisyui").endswith('/daisyui/index.js";')
        assert ext.plugin("flowbite", "plugin").endswith('/flowbite/plugin.js";')
        result = ext.integration_config("preline")
        assert result == ext.integration_config("preline")
        assert result.index("@import") < result.index("@source")
        assert "@plugin" in result
        assert "vendor/preline/preline.js (registered)" in result
        assert "None" in ext.integration_config("daisyui")
    assert runner.run.call_args.kwargs["capture_output"] is True


@pytest.mark.parametrize(
    "path",
    [
        "../outside",
        "/outside",
        "dist/../../outside",
        "dist/../*.js",
        r"C:\outside",
        r"dist\*.js",
        "",
        "dist//*.js",
    ],
)
def test_unsafe_package_paths(integrated, path):
    app, ext, _ = integrated
    with app.app_context(), pytest.raises(AssetResolutionError):
        ext.node_path("preline", path)


def test_glob_symlink_containment(integrated, tmp_path):
    app, ext, _ = integrated
    (app.extensions["node"].package("preline").root / "escape").symlink_to(
        tmp_path, target_is_directory=True
    )
    with app.app_context(), pytest.raises(AssetResolutionError):
        ext.source("preline", "escape/*.js")


def test_windows_paths_and_css_escaping():
    assert (
        relative_css_path(
            PureWindowsPath("C:/project/.node/preline/dist/*.js"),
            PureWindowsPath("C:/project/app/static/src"),
        )
        == "../../../.node/preline/dist/*.js"
    )
    with pytest.raises(AssetResolutionError, match="drive"):
        relative_css_path(PureWindowsPath("D:/file"), PureWindowsPath("C:/app"))
    assert css_string('a"b\nc') == '"a\\"b\\a c"'
    assert css_string("café") == '"café"'


@pytest.mark.parametrize(
    "arguments, expected",
    [
        (["paths"], "Flask templates:"),
        (
            ["path", "preline", "dist/*.js"],
            "../../../tools/node_modules/preline/dist/*.js",
        ),
        (["source", "preline", "dist/*.js"], "@source"),
        (["import", "preline", "variants.css"], "@import"),
        (["plugin", "daisyui"], "@plugin"),
        (["plugin", "flowbite", "plugin"], "/flowbite/plugin.js"),
        (["integrations"], "preline: enabled"),
        (["integration", "preline"], "vendor/preline/preline.js (registered)"),
        (["integration", "daisyui"], "None"),
    ],
)
def test_cli_helpers(integrated, arguments, expected):
    app, _, _ = integrated
    result = app.test_cli_runner().invoke(args=["tailwind", *arguments])
    assert result.exit_code == 0, result.output
    assert expected in result.output
    assert not (Path(app.static_folder) / "src/input.css").exists()


def test_cli_missing_package_and_unknown_integration(tmp_path):
    app = Flask(__name__, root_path=str(tmp_path))
    TailwindCSS(app)
    cli = app.test_cli_runner()
    result = cli.invoke(args=["tailwind", "source", "preline", "dist/*.js"])
    assert result.exit_code == 1
    assert "flask node sync" in result.output
    result = cli.invoke(args=["tailwind", "integration", "unknown"])
    assert result.exit_code == 1
    assert "Available:" in result.output
    result = cli.invoke(args=["tailwind", "integrations"])
    assert "preline: available" in result.output


def test_factory_integration_isolation(tmp_path):
    ext = TailwindCSS()
    apps = []
    for name, integrations in [("one", ["preline"]), ("two", ["daisyui"])]:
        app = Flask(name, root_path=str(tmp_path / name))
        app.config["TAILWIND_INTEGRATIONS"] = integrations
        ext.init_app(app)
        apps.append(app)
        with app.app_context():
            assert [i.name for i in ext.integrations] == integrations
    assert "preline" not in apps[1].extensions["node"].requirements
    assert "daisyui" not in apps[0].extensions["node"].requirements
    assert len(apps[0].extensions["node"].assets) == 1
    assert not apps[1].extensions["node"].assets


@pytest.mark.skipif(shutil.which("node") is None, reason="Node unavailable")
def test_real_node_entry_resolution_is_offline_and_does_not_evaluate(tmp_path):
    app = Flask(__name__, root_path=str(tmp_path))
    ext = TailwindCSS(app)
    manager = app.extensions["node"]
    package(manager, "example", ["dist/plugin.cjs"], exports={".": "./dist/plugin.cjs"})
    with app.app_context():
        assert (
            ext.plugin("example")
            == '@plugin "../../.node/node_modules/example/dist/plugin.cjs";'
        )


def test_sync_and_publication_are_owned_by_node(integrated):
    app, _, runner = integrated
    runner.run.return_value = CommandResult(("npm", "install"), 0)
    runner.run.side_effect = None
    cli = app.test_cli_runner()
    result = cli.invoke(args=["node", "sync"])
    assert result.exit_code == 0, result.output
    manager = app.extensions["node"]
    data = json.loads(manager.manifest_path.read_text())
    assert data["dependencies"]["preline"] == "^3"
    assert data["dependencies"]["daisyui"] == "^5"
    runner.run.assert_called_once_with(
        "npm", ("install",), cwd=manager.directory, capture_output=False
    )
    result = cli.invoke(args=["node", "publish"])
    assert result.exit_code == 0, result.output
    assert "2 assets published" in result.output
    for destination in ["vendor/preline/preline.js", "vendor/flowbite/flowbite.min.js"]:
        assert (Path(app.static_folder) / destination).is_file()
    assert not (Path(app.static_folder) / "src/input.css").exists()
