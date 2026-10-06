"""Tailwind commands; generic Node operations belong to Flask-Node."""

from functools import wraps

import click
from flask import current_app
from flask.cli import with_appcontext
from flask_node import NodeError


def operation(function):
    @wraps(function)
    @with_appcontext
    def wrapped(*args, **kwargs):
        try:
            return function(current_app.extensions["tailwind"], *args, **kwargs)
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
