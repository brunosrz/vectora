"""Version management for Vectora.

Dynamically reads version from pyproject.toml via importlib.metadata.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version


def get_vectora_version() -> str:
    """Get Vectora version from package metadata.

    Returns the version string from pyproject.toml.
    Falls back to "0.1.0dev6" if package is not installed.

    Returns:
        Version string (e.g., "0.1.0dev6")
    """
    try:
        return get_version("vectora")
    except PackageNotFoundError:
        return "0.1.0dev6"


__version__ = get_vectora_version()
