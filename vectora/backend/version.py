"""Version management for Vectora.

Dynamically reads version from pyproject.toml via importlib.metadata.
"""

import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version


def get_vectora_version() -> str:
    """Get Vectora version from package metadata.

    Returns the version string from pyproject.toml.
    Falls back to "0.1.0" if package is not installed.

    Returns:
        Version string (e.g., "0.1.0")
    """
    try:
        return get_version("vectora")
    except PackageNotFoundError:
        return "0.1.0"


def get_build_version() -> str:
    """Versão completa com hash numérico de build (X.Y.Z.<hash>).

    O hash é calculado no build (``scons up-version``), não em runtime — o
    binário Nuitka distribuído não carrega ``.git``. O pipeline de release
    exporta ``VECTORA_BUILD_VERSION`` antes de empacotar; sem isso (dev local,
    sem build oficial), cai pra versão semver sem hash.
    """
    return os.environ.get("VECTORA_BUILD_VERSION", get_vectora_version())


__version__ = get_vectora_version()
