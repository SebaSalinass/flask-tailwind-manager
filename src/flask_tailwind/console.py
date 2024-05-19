import subprocess
import logging
from typing import Optional

DEFAULT_NPM_BIN_PATH = "npm"
DEFAULT_NPX_BIN_PATH = "npx"


class NPMError(Exception):
    pass


class NPXError(Exception):
    pass


class ConsoleInterface:
    cwd: str
    npm_bin_path: str
    npx_bin_path: str

    def __init__(
        self,
        cwd="",
        npm_bin_path: Optional[str] = None,
        npx_bin_path: Optional[str] = None,
    ):
        self.npm_bin_path = npm_bin_path or DEFAULT_NPM_BIN_PATH
        self.npx_bin_path = npx_bin_path or DEFAULT_NPX_BIN_PATH
        self.cwd = cwd

    def npm_run(self, *args: str) -> None:
        try:
            logging.debug(f"🍃 Running npm with args {' '.join(list(args))}")
            subprocess.run([self.npm_bin_path] + list(args), cwd=self.cwd)
        except OSError:
            raise NPMError(
                "It looks like node.js and/or npm is not installed or cannot be found. Visit https://nodejs.org to download and install node.js for your system."
            )

    def npx_run(self, *args: str) -> None:
        try:
            logging.debug(f"🍃 Running npx with args {' '.join(list(args))}")
            subprocess.run([self.npx_bin_path] + list(args), cwd=self.cwd)
        except OSError:
            raise NPXError(
                "It looks like node.js and/or npx is not installed or cannot be found. Visit https://nodejs.org to download and install node.js for your system."
            )
