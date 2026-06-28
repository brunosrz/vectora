"""Launcher Vectora — entry-point do binário compilado."""

from __future__ import annotations


def main() -> int:
    from backend.main import run as cli_run

    cli_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
