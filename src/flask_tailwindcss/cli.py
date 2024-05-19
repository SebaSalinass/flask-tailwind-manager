from typing import TYPE_CHECKING, Tuple
import shutil
import sys
import logging

import click
from flask.cli import with_appcontext
from flask import current_app

if TYPE_CHECKING:
    from .tailwind import TailwindCSS


def install_if_needed(tailwind: "TailwindCSS"):
    if not tailwind.node_destination_path().exists():
        logging.info(
            f"No {tailwind.node_destination_path()} directory found. Running 'npm install'."
        )
        init()


@click.group()
def tailwind():
    """Perform TailwindCSS operations."""
    pass


@tailwind.command()
@with_appcontext
def init():
    tailwind: "TailwindCSS" = current_app.extensions["tailwind"]

    source_dir = tailwind.node_config_starter_path()
    dest_dir = tailwind.node_destination_path()

    if dest_dir.exists():
        logging.info("🍃 Destination path already exists. Aborting")
        sys.exit(1)

    shutil.copytree(source_dir, dest_dir)
    logging.info(f"🍃 Copying default configuration files into {dest_dir}")

    with open(dest_dir / "package.json", "w") as file:
        file.write(tailwind.package_json_str())

    with open(dest_dir / "tailwind.config.js", "w") as file:
        file.write(tailwind.tailwind_config_js_str())

    logging.info(f"🍃 Installing dependencies in {tailwind.cwd}")
    console = tailwind.get_console_interface()
    console.npm_run("-D", "install", "tailwindcss")


@tailwind.command()
@with_appcontext
def start():
    """Start watching CSS changes for dev."""
    tailwind: "TailwindCSS" = current_app.extensions["tailwind"]
    install_if_needed(tailwind)
    console = tailwind.get_console_interface()
    console.npx_run(
        "tailwindcss",
        "-i",
        "./src/input.css",
        "-o",
        "../" + str(tailwind.get_output_path()),
        "--watch",
    )


@tailwind.command()
@click.argument("args", nargs=-1)
@with_appcontext
def npm(args: Tuple[str]) -> None:
    tailwind: "TailwindCSS" = current_app.extensions["tailwind"]
    install_if_needed(tailwind)
    console = tailwind.get_console_interface()
    console.npm_run(*args)


@tailwind.command()
@click.argument("args", nargs=-1)
@with_appcontext
def npx(args: Tuple[str]) -> None:
    tailwind: "TailwindCSS" = current_app.extensions["tailwind"]
    install_if_needed(tailwind)
    console = tailwind.get_console_interface()
    console.npx_run(*args)
