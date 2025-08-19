# src/reqsync/__init__.py

from .core import sync

__all__ = ["sync"]

try:
    from importlib.metadata import PackageNotFoundError, version
except Exception:  # py<3.8 backport if installed
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

try:
    __version__ = version("reqsync")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
