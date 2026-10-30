"""Compatibility entry point for the centralized version generator."""

if __package__:
    from .sync_versions import main
else:
    from sync_versions import main


if __name__ == "__main__":
    raise SystemExit(main())
