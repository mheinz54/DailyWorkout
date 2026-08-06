#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def run_module(module, args):
    command = [sys.executable, "-m", module] + args
    print("Running:", " ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    run_module("black", ["."])
    run_module("isort", ["."])
    run_module("ruff", ["check", "."])


if __name__ == "__main__":
    main()
