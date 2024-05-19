# Flask-Tailwind-Manager

Flask-Tailwind-Manager provides a simple interface to use TailwindCSS with your Flask project. It will let you hide it in a folder called .tailwind so you dont have to see any node_modules or any other javascript. Even tho you DO need npm and npx to be available on your machine.

```{warning}
🚧 This package is under heavy development..
```

## Installation

Install the extension with pip:

```bash
pip install flask-tailwind-manager
```

## Configuration

This are some of the settings available. All of the configurations are optional, and in most cases it should work without any configuration.

| Config                                   | Description                             | Type | Default         |
| ---------------------------------------- | --------------------------------------- | ---- | --------------- |
| TAILWIND_CWD                             | CWD for node_modules.                   | str  | `.tailwind`     |
| TAILWIND_OUTPUT_PATH                     | CSS file output path inside app static. | str  | `css/style.css` |
| TAILWIND_NPM_BIN_PATH                    | Npm binary path.                        | str  | `npm`           |
| TAILWIND_NPX_BIN_PATH                    | Npx binary path.                        | str  | `npx`           |
| TAILWIND_TEMPLATE_FOLDER                 | Name of the templates folder.           | str  | `templates`     |

## Usage

Once installed Flask-TailwindCSS is easy to use. Let's walk through setting up a basic application. Also please note that this is a very basic guide: we will be taking shortcuts here that you should never take in a real application.

To begin we'll set up a Flask app:

```python
from flask import Flask
from flask_tailwind import TailwindCSS

app = Flask(__name__)

tailwind = TailwindCSS()
tailwind.init_app(app)
```

## Using the CLI tool.

Once you completed the extension configuration, you can access the Flask-TailwindCSS CLI tool. There is 4 useful commands you will use. 
    
1. Installing Node and TailwindCSS basic configuration. By default this extension will generate a `tailwind.config.js` generic file, ready to use. If you need to futher customize you will need to edit this file accordingly.  
```bash
    flask tailwind init 
```   
2. Once installed all modules will be found on `.tailwind` folder (or CWD you define). The default configuration will look for changes at `{APP_NAME}/**/{TEMPLATES_FOLDER}/*{.html,.jinja,.j2}`. You can always modify `tailwind.config.js` file in order to customize it.

3. To start watching files and changes. use the `start` command as follows.
```bash
    flask tailwind start
```
4. Almost every time you are using you will install plugins like Preline, Flowbite, daysiUI, etc... For this cases you can use the `npx` or `npm` commands. In the following example we will install the PrelineUI plugin as follows.
```bash
    flask tailwind npm i preline
```
5. After the installation you will have to configure it manually.

This will ensure the plugins are installed in the correct CWD.
 

## Load resources

Once the extension is set up, this will make available the `tailwind_css` function into the templates context so you could load the generated css like this.

```html
<head>
  {{ tailwind_css() }} 
</head>
```
