import logging
import shutil
import sys
from typing import TYPE_CHECKING, Optional, Tuple

import click
from flask import current_app
from flask.cli import with_appcontext

if TYPE_CHECKING:
    from .tailwind import TailwindCSS


@click.group()
def tailwind() -> None:
    """Perform TailwindCSS operations."""
    pass


@tailwind.command()
@with_appcontext
def init() -> None:
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

    with open(dest_dir / "src/input.css", "w") as file:
        file.write(tailwind.input_css_str())

    logging.info(f"🍃 Installing dependencies in {tailwind.cwd}")
    console = tailwind.get_console_interface()
    console.npm_run("install", "tailwindcss", "@tailwindcss/cli")


def install_if_needed(ctx: click.Context, tailwind_ext: "TailwindCSS") -> None:
    if not tailwind_ext.node_destination_path().exists():
        logging.info(
            f"No {tailwind_ext.node_destination_path()} directory found. Running 'npm install'."
        )
        ctx.invoke(init)
    return None


@tailwind.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1)
@click.pass_context
@with_appcontext
def start(ctx: click.Context, args: Optional[Tuple[str]] = None) -> None:
    """Start watching CSS changes for dev."""
    tailwind_ext: "TailwindCSS" = current_app.extensions["tailwind"]
    install_if_needed(ctx, tailwind_ext)

    extra_args = args or ()
    console = tailwind_ext.get_console_interface()
    console.npx_run(
        "@tailwindcss/cli",
        "-i",
        "./src/input.css",
        "-o",
        "../" + str(tailwind_ext.get_output_path()),
        "--watch",
        *extra_args,
    )


@tailwind.command(
    context_settings=dict(ignore_unknown_options=True, allow_interspersed_args=True)
)
@click.argument("args", nargs=-1)
@click.pass_context
@with_appcontext
def npm(ctx: click.Context, args: Tuple[str]) -> None:
    tailwind_ext: "TailwindCSS" = current_app.extensions["tailwind"]
    install_if_needed(ctx, tailwind_ext)

    console = tailwind_ext.get_console_interface()
    console.npm_run(*args)


@tailwind.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("args", nargs=-1)
@click.pass_context
@with_appcontext
def npx(ctx: click.Context, args: Tuple[str]) -> None:
    tailwind_ext: "TailwindCSS" = current_app.extensions["tailwind"]
    install_if_needed(ctx, tailwind_ext)

    console = tailwind_ext.get_console_interface()
    console.npx_run(*args)
