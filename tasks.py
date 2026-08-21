# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.
"""Development task entry points, invoked via `uv run <name>`."""

from __future__ import annotations

import subprocess
import sys


def tests() -> None:
    """Run the test suite."""
    sys.exit(subprocess.run(["pytest", *sys.argv[1:]], check=False).returncode)  # noqa: S603, S607


def commit() -> None:
    """Run pre-commit checks, then create a conventional commit with commitizen."""
    if subprocess.run(["pre-commit", "run"], check=False).returncode != 0:  # noqa: S607
        print("Fix the issues above, stage your changes and try again.")  # noqa: T201
        sys.exit(1)
    sys.exit(subprocess.run(["cz", "commit", *sys.argv[1:]], check=False).returncode)  # noqa: S603, S607
