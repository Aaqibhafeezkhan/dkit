"""Allow running the CLI with ``python -m dkit``."""

from dkit.cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
