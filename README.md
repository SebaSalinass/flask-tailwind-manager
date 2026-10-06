# Flask-Tailwind-Manager

Tailwind CSS v4 integration for Flask, with optional Preline, Flowbite, and daisyUI
adapters. Flask-Tailwind-Manager owns stylesheets, Tailwind configuration helpers,
and build/watch commands. **Flask-Node owns the shared Node environment**, npm
requirements, execution, package resolution, and browser asset publication.

The distribution remains `flask-tailwind-manager`, the Python import remains
`flask_tailwind`, and the CLI namespace remains `flask tailwind`.

## Installation

Requires Python 3.10+, Flask 2.2–3.x, and Flask-Node 0.2.0 or newer within the 0.2
series. Flask-Node is installed automatically as a required Python dependency.
Install Node.js with npm/npx separately for synchronization, builds, watches, and
plugin-entry resolution.

```bash
pip install flask-tailwind-manager
# Optional explicit installation spelling:
pip install 'flask-tailwind-manager[preline]'
pip install 'flask-tailwind-manager[flowbite]'
pip install 'flask-tailwind-manager[daisyui]'
pip install 'flask-tailwind-manager[preline,flowbite]'
```

The built-in integrations have no additional Python dependencies. These extras
are intentionally empty: all definitions are available with the base package.
An extra does not enable an integration, install npm packages, or create files.
Enable integrations explicitly in each Flask application's configuration.

## Application setup

```python
from flask import Flask
from flask_tailwind import TailwindCSS

tailwind = TailwindCSS()


def create_app():
    app = Flask(__name__)
    app.config["TAILWIND_INTEGRATIONS"] = ["preline"]
    tailwind.init_app(app)
    return app
```

`TailwindCSS(app)` also works. Tailwind initializes Flask-Node if necessary and
reuses an existing `app.extensions['node']` manager. Other consumers may share
that manager. For explicit Node setup, call `Node().init_app(app)` before Tailwind
initialization. Do not initialize Node again afterward; use
`Node().get_manager(app)` to retrieve the manager.

Application initialization only registers state, requirements, and browser asset
declarations. It creates no directories, executes no processes, copies no assets,
and accesses no network. Settings and enabled integrations are application-local,
including when one `TailwindCSS()` instance serves several application factories.
Unknown integration names fail with a list of available integrations.

## Application-owned stylesheet and configuration

Configure paths before extension initialization.

| Setting | Default | Meaning |
| --- | --- | --- |
| `TAILWIND_INPUT_PATH` | `src/input.css` | Relative to `app.static_folder`, or absolute |
| `TAILWIND_OUTPUT_PATH` | `css/style.css` | Relative to `app.static_folder` |
| `TAILWIND_TEMPLATE_FOLDER` | `app.template_folder` | Relative to `app.root_path`, or absolute; overrides the initial template source path |
| `TAILWIND_INTEGRATIONS` | `[]` | Enabled names: `preline`, `flowbite`, `daisyui` |

Flask must have a static folder. If no template folder is configured, initial CSS
omits the template source clause. Additional template directories, including
blueprint templates, can be added manually to the stylesheet.

Flask-Node configuration is delegated unchanged:

| Setting | Default | Meaning |
| --- | --- | --- |
| `NODE_DIR` | `.node` | Relative to `app.root_path`, or absolute |
| `NODE_PYPROJECT` | `pyproject.toml` | Application npm declarations; relative to `app.root_path`, or absolute |
| `NODE_BIN` | `node` | Node executable |
| `NODE_NPM_BIN` | `npm` | npm executable |
| `NODE_NPX_BIN` | `npx` | npx executable |

For `.node` beside an application package, configure an absolute project path:

```python
from pathlib import Path

app.config["NODE_DIR"] = Path(app.root_path).parent / ".node"
```

That layout becomes:

```text
project/
├── .node/
│   ├── package.json
│   ├── package-lock.json
│   └── node_modules/
└── app/
    ├── templates/
    └── static/
        ├── src/input.css        # Application source: commit this file
        ├── css/style.css        # Compiled CSS
        └── vendor/preline/preline.js
```

`input.css` belongs to the developer. Tailwind init creates it once, using
exclusive file creation. It never overwrites an existing file. The initial CSS
contains a calculated import to the shared environment's Tailwind stylesheet and
a calculated source path to Flask's template folder. No path assumes `app/static`
or the shell working directory.

Integrations do not automatically add directives to existing or new stylesheets.
Configuration helpers print the required directives for the developer to apply.
There is no `--apply`, template modification, or automatic script injection.

## Fresh-project Preline workflow

After enabling Preline as shown above:

```bash
flask --app your_app node sync
flask --app your_app tailwind init
flask --app your_app node publish
flask --app your_app tailwind integration preline
```

`node sync` realizes all application and extension requirements in the shared
Node environment. `tailwind init` creates missing application-owned input CSS;
when Tailwind packages are already installed, it does not repeat installation.
`node publish` copies registered browser assets using Flask-Node.

The integration command reports the input file, npm requirements, calculated
CSS directives, and browser asset destinations. Add its CSS directives after the
initial Tailwind import. Keep CSS imports before source/plugin directives. Include
the published browser script manually in the application template:

```html
<script src="{{ url_for('static', filename='vendor/preline/preline.js') }}"></script>
```

Then build or watch:

```bash
flask --app your_app tailwind build
flask --app your_app tailwind start
flask --app your_app tailwind start -- --poll
```

Build produces minified CSS. Start watches changes. Commands delegate to
Flask-Node's npx runner with absolute input/output paths and streamed output.
First-use build/watch can install missing core Tailwind packages and create
missing source CSS. Use explicit `node sync` and `node publish` to realize enabled
integrations. CLI failures retain useful Flask-Node diagnostics and exit nonzero.

Load compiled CSS using the existing helper:

```html
{{ tailwind_css() }}
```

## Available integrations

| Name | npm requirements | Tailwind configuration | Browser publication |
| --- | --- | --- | --- |
| `preline` | `preline` `^3`, `@tailwindcss/forms` `^0.5` | Source glob, variants import, forms plugin | `dist/preline.js` → `vendor/preline/preline.js` |
| `flowbite` | `flowbite` `^3` | Source glob, Flowbite plugin | `dist/flowbite.min.js` → `vendor/flowbite/flowbite.min.js` |
| `daisyui` | `daisyui` `^5` | daisyUI plugin | None |

These definitions target Tailwind v4. Package files were verified against Preline
3.2.3, Flowbite 3.1.2, daisyUI 5.0.0, and forms 0.5.10. Library configuration follows
the [Preline installation guide](https://www.preline.co/docs/),
[Flowbite configuration](https://flowbite.com/docs/customize/configuration/), and
[daisyUI installation guide](https://daisyui.com/docs/install/).

Each definition is immutable data: requirements, sources, imports, plugins, and
optional browser assets. Core processes these declarations without library-specific
conditionals or lifecycle hooks. The registry is fixed; there is no plugin discovery
framework. Full Flask extensions such as Flask-Leaflet remain separate consumers
of Flask-Node.

Flask-Node compares requirement strings exactly. An application declaration of a
package already required by an integration must agree with its version and section.
Keep additional npm declarations in the application's Flask-Node configuration;
`node sync` rebuilds the managed manifest from declarations and does not preserve
hand-edited npm scripts or undeclared manifest dependencies.

## Path, directive, and diagnostic helpers

```bash
flask --app your_app tailwind paths
flask --app your_app tailwind path preline 'dist/*.js'
flask --app your_app tailwind source preline 'dist/*.js'
flask --app your_app tailwind import preline variants.css
flask --app your_app tailwind plugin daisyui
flask --app your_app tailwind plugin flowbite plugin
flask --app your_app tailwind integrations
flask --app your_app tailwind integration preline
```

`paths` displays configured input, output, template, static, and Node directories.
Use `flask node status` for executable/environment diagnostics. `integrations`
distinguishes available definitions from enabled ones. Integration output labels
assets as registered; registration is not proof that publication has happened.

Python equivalents, inside the appropriate application context:

```python
with app.app_context():
    tailwind.input_path
    tailwind.node_path("preline", "dist/*.js")
    tailwind.source("preline", "dist/*.js")
    tailwind.import_package("preline", "variants.css")
    tailwind.plugin("daisyui")
    tailwind.plugin("flowbite", "plugin")
    tailwind.integration_config("preline")
    tailwind.paths()
    tailwind.integrations  # Enabled immutable definitions
```

Paths are relative to `input_path.parent`, normalized to `/`, and CSS strings are
escaped. Package locations come from Flask-Node. Glob helpers resolve their fixed
prefix through Flask-Node and retain the wildcard suffix; they do not expand globs.
Plugin helpers use Flask-Node's `resolve_entry()` with its CommonJS require-resolution
conditions, without evaluating package code. Plugin inspection requires Node;
ordinary explicit-file/source helpers do not launch commands. Different Windows
drives cannot be expressed as relative CSS paths and produce a useful error.

Helpers never install packages. Enable the desired integration and run
`flask node sync` first. An available-but-disabled integration can be inspected
if its packages are installed, but inspection does not enable it or register assets.

## Version control and compatibility

Commit application source CSS and the application's npm declarations. For the
shared Node environment, follow Flask-Node's lockfile/reproducibility workflow;
use `flask node ci` when its manifest and lockfile agree with current declarations.
Ignore installed modules (adjust the path for your configured Node directory):

```gitignore
.node/node_modules/
```

Relative `TAILWIND_INPUT_PATH` now resolves against the Flask static folder rather
than the Node directory. The default source location has also changed. This task
provides no automatic migration from any earlier input location: existing apps
should keep an explicit absolute input path until they are migrated separately.
No user files are moved or deleted.

The existing `TailwindCSS` initialization API, `tailwind_css()`, init/start/build,
and output setting remain. Extension settings and helper methods require an
application context. `get_output_path()` retains its historical relative result;
`get_absolute_output_path()` provides the execution path.

Legacy Node settings remain deprecated aliases for this transition release:

| Old setting | Replacement |
| --- | --- |
| `TAILWIND_CWD` | `NODE_DIR` |
| `TAILWIND_NPM_BIN_PATH` | `NODE_NPM_BIN` |
| `TAILWIND_NPX_BIN_PATH` | `NODE_NPX_BIN` |

Aliases warn, preserve explicitly configured legacy directory semantics, and fail
on conflicts with new configuration or an existing manager. `flask tailwind npm`
and `flask tailwind npx` remain warning aliases; prefer `flask node npm` and
`flask node npx`. They require an initialized Node environment. Old standalone
ConsoleInterface and package-manifest-generation helpers remain removed.

## Development and tests

```bash
uv sync --upgrade
uv run pytest
```

For unreleased local Flask-Node changes, install its sibling checkout editably
into your development environment. Production metadata uses the released dependency.

Tests use actual Flask-Node managers and temporary package structures, mocking
command execution. An additional offline test uses real Node when available to
prove plugin entry resolution without evaluating package code. Tests download
no npm packages and require no network access.
