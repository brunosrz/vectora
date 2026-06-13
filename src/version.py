"""Version management for Vectora.

Dynamically reads version from pyproject.toml via importlib.metadata.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version


def get_vectora_version() -> str:
    """Get Vectora version from package metadata.

    Returns the version string from pyproject.toml.
<<<<<<< HEAD:vectora/version.py
    Falls back to "0.1.0rc4" if package is not installed.

    Returns:
        Version string (e.g., "0.1.0rc4")
=======
    Falls back to "0.1.0" if package is not installed.

    Returns:
        Version string (e.g., "0.1.0")
>>>>>>> dev:src/version.py
    """
    try:
        return get_version("vectora")
    except PackageNotFoundError:
<<<<<<< HEAD:vectora/version.py
        return "0.1.0rc4"
=======
        return "0.1.0"
>>>>>>> dev:src/version.py


__version__ = get_vectora_version()
