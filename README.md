# Flask-Tailwind-Manager

Use Tailwind CSS v4 with Flask. Flask-Tailwind-Manager owns Tailwind stylesheets,
build/watch commands, and the `tailwind_css()` template helper. **Flask-Node owns
all Node/npm infrastructure**, including the shared environment, dependency
installation, package resolution, and command execution.

Requires Python 3.10+ and Flask 2.2–3.x. Install Node.js with npm/npx to execute
commands. Importing or initializing the Flask extension needs no Node executable,
creates no files, and runs no commands.

## Installation

```bash
pip install flask-tailwind-manager
```

Flask-Node is a required Python dependency; users do not need to install it
separately. This integration targets the local Flask-Node 0.1.0 API. Until that
release is available from your package index, develop with both repositories:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ../flask-node -e .
.venv/bin/python -m pip install pytest
```

## Application setup

```python
from flask import Flask
from flask_tailwind import TailwindCSS

tailwind = TailwindCSS()


def create_app():
    app = Flask(__name__)
    tailwind.init_app(app)
    return app
```

`TailwindCSS(app)` also works. Tailwind initializes Flask-Node automatically when
needed and reuses an existing `app.extensions["node"]` manager. Each Flask app
has its own settings and manager, even with a shared `TailwindCSS()` instance.

For explicit Node configuration or a custom runner, initialize Node first:

```python
from flask_node import Node

node = Node()
node.init_app(app)
tailwind.init_app(app)
```

Other Flask-Node consumers can declare dependencies on the same manager. There
is only one Node environment. Do not call `Node.init_app()` again after Tailwind
has initialized it; access it through `Node().get_manager(app)` instead.

## Configuration

Configure before initializing the extensions.

| Tailwind setting | Default | Meaning |
| --- | --- | --- |
| `TAILWIND_INPUT_PATH` | `tailwind/input.css` | Relative to the shared Node directory, or absolute |
| `TAILWIND_OUTPUT_PATH` | `css/style.css` | Relative to `app.static_folder` |
| `TAILWIND_TEMPLATE_FOLDER` | `templates` | Relative to `app.root_path`, or absolute; used when generating input CSS |

| Flask-Node setting | Default | Meaning |
| --- | --- | --- |
| `NODE_DIR` | `.node` | Relative to `app.root_path`, or absolute |
| `NODE_BIN` | `node` | Node executable |
| `NODE_NPM_BIN` | `npm` | npm executable |
| `NODE_NPX_BIN` | `npx` | npx executable |

Flask requires a static folder for this extension. A relative `NODE_DIR` is
anchored to the application's root, **not the shell working directory**. For
`.node` beside an application package, set an absolute project path:

```python
from pathlib import Path

app.config["NODE_DIR"] = Path(app.root_path).parent / ".node"
```

With that setting, a project can look like:

```text
project/
├── .node/
│   ├── package.json
│   ├── package-lock.json
│   ├── node_modules/       # Tailwind and all other consumers' packages
│   └── tailwind/input.css
└── app/
    ├── static/css/style.css
    └── templates/
```

## Initialize, watch, and build

```bash
flask --app your_app tailwind init
flask --app your_app tailwind start
flask --app your_app tailwind build
```

`init` declares/installs `tailwindcss` and `@tailwindcss/cli` with version range
`^4` through Flask-Node and creates missing input CSS. Existing input CSS is
preserved. It also installs declarations from other consumers sharing the
manager, preserving unrelated manifest entries.

`start` watches changes; `build` produces minified CSS. Both pass absolute input
and output paths to Flask-Node's npx runner and stream command output. Missing
packages or input CSS trigger first-use initialization. An existing environment
with both packages and input CSS does not trigger another install.

Pass extra Tailwind CLI arguments after `--`:

```bash
flask --app your_app tailwind start -- --poll
```

The generated stylesheet imports Tailwind's `index.css` using a relative path
resolved through Flask-Node, so custom input locations can still use the same
installed package. It includes a source path calculated from the actual template
directory. Edit the input CSS to add custom styles and additional sources,
including blueprint templates. Changing template configuration does not rewrite
an existing stylesheet. This is Tailwind v4 CSS configuration; no
`tailwind.config.js` is generated.

Node failures produce a nonzero CLI exit with Tailwind context and the underlying
Node error. Python operations expose Flask-Node's `NodeError` subclasses directly.

## Other npm packages and reproducible builds

Use Flask-Node's commands for generic operations:

```bash
flask --app your_app node install preline
flask --app your_app node npm -- run custom-script
flask --app your_app node npx -- some-tool --help
flask --app your_app node status
```

Tailwind records requirements during Flask initialization without writing a
manifest. `flask node install` or `flask tailwind init` merges those requirements
and installs them. `flask node init` alone creates/validates the manifest; it does
not persist declarations or install packages. Requirement conflicts between
consumers fail explicitly; Flask-Node compares version strings exactly.

Commit the shared `package.json` and `package-lock.json`. For subsequent clean
installs, use `flask node ci`, then `flask tailwind build`. Build environments
must retain the Tailwind input file and install the required packages.

Recommended project `.gitignore` entry (adjust for your configured directory):

```gitignore
.node/node_modules/
```

Keep customized `.node/tailwind/input.css` in version control too.

## Load compiled CSS

```html
<head>
  {{ tailwind_css() }}
</head>
```

The helper uses Flask's static URL and `TAILWIND_OUTPUT_PATH`.

## Upgrade from the previous Node environment

Python 3.9 and Flask 2.0–2.1 are no longer supported because Flask-Node requires
Python 3.10+ and Flask 2.2+.

1. Set `NODE_DIR` before initialization, paying attention to its application-root
   path semantics.
2. Run `flask node init` followed by `flask tailwind init`. The first command is
   optional because Tailwind's installation initializes the environment.
3. Manually copy custom styles from your old input stylesheet into the new one.
   Preserve the generated import/source paths or adjust your old paths for the
   new location. Reinstall additional packages using `flask node install` and
   transfer custom npm scripts manually.
4. Run `flask tailwind build` and verify the output.
5. Update version control and ignore rules. Remove the old environment yourself
   only after verification. No upgrade operation moves or deletes user files.

Deprecated settings remain aliases for this transition release:

| Old setting | Replacement |
| --- | --- |
| `TAILWIND_CWD` | `NODE_DIR` |
| `TAILWIND_NPM_BIN_PATH` | `NODE_NPM_BIN` |
| `TAILWIND_NPX_BIN_PATH` | `NODE_NPX_BIN` |

Aliases emit `FutureWarning`. Explicit legacy relative directory values retain
working-directory semantics and select the one shared environment; they do not
create another Node manager. Conflicting old/new settings, including conflicts
with an already initialized manager, fail with guidance rather than silently
changing that manager.

`flask tailwind npm` and `flask tailwind npx` emit deprecation guidance and forward
to the shared manager. They no longer initialize Tailwind automatically; use
`flask node init` or `flask tailwind init` first. These aliases and settings are
scheduled for removal in a future breaking release.

The old `ConsoleInterface`, `NPMError`, `NPXError`, `get_console_interface()`,
`package_json_str()`, `node_config_starter_path()`, and `node_destination_path()`
infrastructure APIs are removed. Use Flask-Node's manager and errors instead.
`get_output_path()` retains its historical relative result under an app context;
`get_absolute_output_path()` provides the execution path. Access to extension
settings now requires the current app context for factory isolation.

## Tests

With local Flask-Node installed and pytest available:

```bash
python -m pytest
```

Tests use real Flask-Node managers with a fake command runner. They require no
Node executables or npm network access.
