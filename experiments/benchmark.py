"""Repository-local benchmark entry point.

Prefer ``quasar2 benchmark`` after editable installation. This wrapper keeps the
experiment script discoverable from the project layout proposed for the POC.
"""

import sys

from quasar2.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["benchmark", *sys.argv[1:]]))
