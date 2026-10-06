import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from flask import Flask
from flask_node import CommandResult, CommandRunner, ConfigurationError, Node, NodeError

from flask_tailwind import TailwindCSS


@pytest.fixture
def runner():
    runner = Mock(spec=CommandRunner)

    def run(executable, args, *, cwd, capture_output):
        if executable == "npm" and args == ("install",):
            for name in ("tailwindcss", "@tailwindcss/cli"):
                package = cwd / "node_modules" / name
                package.mkdir(parents=True, exist_ok=True)
                (package / "package.json").write_text(json.dumps({"version": "4.0.0"}))
                if name == "tailwindcss":
                    (package / "index.css").write_text("/* Tailwind */")
        return CommandResult((executable, *args), 0)

    runner.run.side_effect = run
    return runner


@pytest.fixture
def app(tmp_path, runner):
    app = Flask(__name__, root_path=str(tmp_path))
    app.config.update(TESTING=True, SERVER_NAME="localhost:5000")
    Node(app, runner=runner)
    TailwindCSS(app)
    return app


def test_extension_registers_and_reuses_manager(app, runner):
    assert isinstance(app.extensions["tailwind"], TailwindCSS)
    with app.app_context():
        assert app.extensions["tailwind"].node is app.extensions["node"]
    assert not app.extensions["node"].directory.exists()
    runner.run.assert_not_called()
    runner.locate.assert_not_called()


def test_convenience_initialization(tmp_path):
    app = Flask(__name__, root_path=str(tmp_path))
    TailwindCSS(app)
    assert "node" in app.extensions
    assert "node" in app.cli.commands
    assert app.extensions["node"].directory == tmp_path / ".node"
    assert not (tmp_path / ".node").exists()
    assert not (tmp_path / ".tailwind").exists()


def test_template_global(app):
    with app.app_context():
        html = app.jinja_env.globals["tailwind_css"]()
        assert "stylesheet" in html
        assert "/static/css/style.css" in html


def test_init_merges_shared_requirements_and_preserves_css(app):
    manager = app.extensions["node"]
    manager.require("chart.js", "^4")
    manager.initialize()
    manager.manifest_path.write_text(
        json.dumps(
            {"scripts": {"custom": "echo hi"}, "dependencies": {"preline": "^3"}}
        )
    )
    cli = app.test_cli_runner()
    result = cli.invoke(args=["tailwind", "init"])
    assert result.exit_code == 0, result.output
    manifest = json.loads(manager.manifest_path.read_text())
    assert manifest["dependencies"] == {
        "tailwindcss": "^4",
        "@tailwindcss/cli": "^4",
        "chart.js": "^4",
        "preline": "^3",
    }
    assert manifest["scripts"] == {"custom": "echo hi"}
    path = Path(app.static_folder) / "src/input.css"
    assert (
        '@import "../../.node/node_modules/tailwindcss/index.css"' in path.read_text()
    )
    assert 'source("../../templates/")' in path.read_text()
    path.write_text("/* custom */")
    assert cli.invoke(args=["tailwind", "init"]).exit_code == 0
    assert path.read_text() == "/* custom */"
    assert not (manager.directory.parent / ".tailwind").exists()


@pytest.mark.parametrize("command,flag", [("build", "--minify"), ("start", "--watch")])
def test_execution_and_first_use(app, runner, command, flag):
    result = app.test_cli_runner().invoke(
        args=["tailwind", command, "--", "--verbose", "with spaces"]
    )
    assert result.exit_code == 0, result.output
    manager = app.extensions["node"]
    runner.run.assert_called_with(
        "npx",
        (
            "@tailwindcss/cli",
            "-i",
            str(Path(app.static_folder) / "src/input.css"),
            "-o",
            str(app.static_folder + "/css/style.css"),
            flag,
            "--verbose",
            "with spaces",
        ),
        cwd=manager.directory,
        capture_output=False,
    )
    runner.run.reset_mock()
    assert app.test_cli_runner().invoke(args=["tailwind", command]).exit_code == 0
    assert runner.run.call_count == 1  # no redundant installation


@pytest.mark.parametrize("command", ["init", "build", "start"])
def test_install_failure(app, runner, command):
    runner.run.side_effect = NodeError("npm missing")
    result = app.test_cli_runner().invoke(args=["tailwind", command])
    assert result.exit_code == 1
    assert "Tailwind: npm missing" in result.output


def test_build_failure(app, runner):
    assert app.test_cli_runner().invoke(args=["tailwind", "init"]).exit_code == 0
    runner.run.side_effect = NodeError("npx exited with status 7")
    result = app.test_cli_runner().invoke(args=["tailwind", "build"])
    assert result.exit_code == 1
    assert "status 7" in result.output


def test_factory_isolation(tmp_path, runner):
    extension = TailwindCSS()
    apps = []
    for name in ("one", "two"):
        app = Flask(name, root_path=str(tmp_path / name))
        app.config["TAILWIND_OUTPUT_PATH"] = name + ".css"
        Node(app, runner=runner)
        extension.init_app(app)
        apps.append(app)
    for app in apps:
        with app.app_context():
            assert extension.node is app.extensions["node"]
            assert extension.output_css_path == app.name + ".css"
            assert extension.get_output_path().name == app.name + ".css"
    assert apps[0].extensions["node"] is not apps[1].extensions["node"]


@pytest.mark.parametrize("command", ["npm", "npx"])
def test_deprecated_cli_alias(app, runner, command):
    app.extensions["node"].initialize()
    result = app.test_cli_runner().invoke(args=["tailwind", command, "--", "--help"])
    assert result.exit_code == 0, result.output
    assert f"flask node {command}" in result.output
    runner.run.assert_called_once_with(
        command, ("--help",), cwd=app.extensions["node"].directory, capture_output=False
    )


def test_legacy_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = Flask(__name__, root_path=str(tmp_path / "app"))
    app.config.update(
        TAILWIND_CWD="legacy",
        TAILWIND_NPM_BIN_PATH="custom-npm",
        TAILWIND_NPX_BIN_PATH="custom-npx",
    )
    with pytest.warns(FutureWarning) as warnings:
        TailwindCSS(app)
    assert len(warnings) == 3
    manager = app.extensions["node"]
    assert manager.directory == tmp_path / "legacy"
    assert manager.npm_bin == "custom-npm"
    assert manager.npx_bin == "custom-npx"


def test_legacy_conflict_with_initialized_node(app):
    other = Flask("other", root_path=app.root_path)
    Node(other)
    other.config["TAILWIND_CWD"] = "conflicting"
    with (
        pytest.warns(FutureWarning),
        pytest.raises(ConfigurationError, match="conflicts"),
    ):
        TailwindCSS(other)
    assert "tailwind" not in other.extensions


def test_external_paths(tmp_path, runner):
    app = Flask(
        __name__,
        root_path=str(tmp_path / "application"),
        static_folder=str(tmp_path / "assets"),
    )
    app.config.update(
        NODE_DIR=tmp_path / "shared-node",
        TAILWIND_INPUT_PATH=tmp_path / "styles/input.css",
        TAILWIND_TEMPLATE_FOLDER=tmp_path / "views",
    )
    Node(app, runner=runner)
    TailwindCSS(app)
    result = app.test_cli_runner().invoke(args=["tailwind", "build"])
    assert result.exit_code == 0, result.output
    css = (tmp_path / "styles/input.css").read_text()
    assert "../shared-node/node_modules/tailwindcss/index.css" in css
    assert 'source("../views/")' in css
    assert runner.run.call_args.args[1][4] == str(tmp_path / "assets/css/style.css")


def test_registration_validation(tmp_path):
    app = Flask(__name__, root_path=str(tmp_path), static_folder=None)
    with pytest.raises(AttributeError):
        TailwindCSS(app)
    assert not app.extensions
    app = Flask(__name__, root_path=str(tmp_path))
    ext = TailwindCSS(app)
    with pytest.raises(RuntimeError, match="already registered"):
        ext.init_app(app)


@pytest.mark.parametrize("output", ["../escape.css", "/absolute.css", ""])
def test_invalid_output(tmp_path, output):
    app = Flask(__name__, root_path=str(tmp_path))
    app.config["TAILWIND_OUTPUT_PATH"] = output
    with pytest.raises(ConfigurationError):
        TailwindCSS(app)
    assert not app.extensions


def test_requirement_conflict_is_not_hidden(tmp_path, runner):
    from flask_node import DependencyConflictError

    app = Flask(__name__, root_path=str(tmp_path))
    Node(app, runner=runner)
    app.extensions["node"].require("tailwindcss", "^3")
    with pytest.raises(DependencyConflictError):
        TailwindCSS(app)
    assert "tailwind" not in app.extensions
    runner.run.assert_not_called()


def test_legacy_settings_agree_with_existing_manager(app):
    manager = app.extensions["node"]
    other = Flask("other", root_path=app.root_path)
    Node(other)
    other.config.update(
        TAILWIND_CWD=manager.directory,
        TAILWIND_NPM_BIN_PATH=manager.npm_bin,
        TAILWIND_NPX_BIN_PATH=manager.npx_bin,
    )
    existing = other.extensions["node"]
    with pytest.warns(FutureWarning):
        TailwindCSS(other)
    assert other.extensions["node"] is existing


def test_generated_css_quotes_special_paths(tmp_path, runner):
    app = Flask(__name__, root_path=str(tmp_path))
    app.config["TAILWIND_TEMPLATE_FOLDER"] = 'views "quoted"'
    Node(app, runner=runner)
    TailwindCSS(app)
    result = app.test_cli_runner().invoke(args=["tailwind", "init"])
    assert result.exit_code == 0, result.output
    css = (Path(app.static_folder) / "src/input.css").read_text()
    assert r"views \"quoted\"" in css
