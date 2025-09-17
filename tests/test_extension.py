import pytest
from flask import Flask
from flask_tailwind import TailwindCSS


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost:5000"
    app.config["APPLICATION_ROOT"] = "/app"
    app.config["PREFERRED_URL_SCHEME"] = "https"
    app.static_folder = "static"
    TailwindCSS(app)  # init extension
    return app


def test_extension_registers(app):
    # Extension should be in app.extensions
    assert "tailwind" in app.extensions
    ext = app.extensions["tailwind"]
    assert isinstance(ext, TailwindCSS)


def test_template_global(app):
    # tailwind_css tag should render <link ...>
    with app.app_context():
        html = app.jinja_env.globals["tailwind_css"]()
        assert "stylesheet" in html
        assert "static" in html


def test_package_json_render(app):
    with app.app_context():
        ext = app.extensions["tailwind"]
        result = ext.package_json_str()
        assert '"name":' in result
        assert "-tailwind" in result
