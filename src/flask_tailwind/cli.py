"""Tailwind commands; generic Node operations belong to Flask-Node."""

from functools import wraps

import click
from flask import current_app
from flask.cli import with_appcontext
from flask_node import NodeError, PackageNotFoundError


def operation(function):
    @wraps(function)
    @with_appcontext
    def wrapped(*args, **kwargs):
        try:
            return function(current_app.extensions["tailwind"], *args, **kwargs)
        except PackageNotFoundError as exc:
            raise click.ClickException(
                f"Tailwind: {exc} Run 'flask node sync' after enabling the integration."
            ) from exc
        except (NodeError, OSError) as exc:
            raise click.ClickException(f"Tailwind: {exc}") from exc

    return wrapped


@click.group()
def tailwind():
    """Configure, build, and watch Tailwind CSS."""


@tailwind.command()
@operation
def init(extension):
    """Install Tailwind requirements and create missing input CSS."""
    extension.initialize()
    click.echo(f"Tailwind ready: {extension.get_input_path()}")


@tailwind.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@operation
def start(extension, args):
    """Watch CSS changes for development."""
    extension.run(*args, watch=True)


@tailwind.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@operation
def build(extension, args):
    """Build minified CSS for production."""
    extension.run(*args)


@tailwind.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@operation
def npm(extension, args):
    """Deprecated alias for flask node npm."""
    click.echo("Deprecated: use 'flask node npm -- ...'.", err=True)
    extension.node.npm(*args, capture_output=False)


@tailwind.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@operation
def npx(extension, args):
    """Deprecated alias for flask node npx."""
    click.echo("Deprecated: use 'flask node npx -- ...'.", err=True)
    extension.node.npx(*args, capture_output=False)


@tailwind.command("paths")
@operation
def paths(extension):
    """Show the actual application and tooling paths."""
    for label, path in extension.paths().items():
        click.echo(f"{label}: {path if path is not None else '(not configured)'}")


@tailwind.command("path")
@click.argument("package")
@click.argument("path")
@operation
def package_path(extension, package, path):
    """Print a stylesheet-relative installed package path or glob."""
    click.echo(extension.node_path(package, path))


@tailwind.command("source")
@click.argument("package")
@click.argument("path")
@operation
def source(extension, package, path):
    """Print a Tailwind source directive."""
    click.echo(extension.source(package, path))


@tailwind.command("import")
@click.argument("package")
@click.argument("path")
@operation
def import_package(extension, package, path):
    """Print a Tailwind CSS import directive."""
    click.echo(extension.import_package(package, path))


@tailwind.command("plugin")
@click.argument("package")
@click.argument("subpath", required=False)
@operation
def plugin(extension, package, subpath):
    """Print a plugin directive using Flask-Node entry resolution."""
    click.echo(extension.plugin(package, subpath))


@tailwind.command("integrations")
@operation
def integrations(extension):
    """List available and enabled integrations."""
    from .integrations import REGISTRY

    enabled = {item.name for item in extension.integrations}
    for name in sorted(REGISTRY):
        click.echo(f"{name}: {'enabled' if name in enabled else 'available'}")


@tailwind.command("integration")
@click.argument("name")
@operation
def integration(extension, name):
    """Display integration configuration without editing source files."""
    click.echo(extension.integration_config(name))
