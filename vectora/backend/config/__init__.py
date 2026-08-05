"""Schema declarativo de configuração — fonte única de verdade para CLI e
REST (ver ``registry.py`` para o racional completo). Importar este pacote
popula o registry global a partir de ``fields.py``.
"""

from __future__ import annotations

from backend.config import (
    fields as _fields,
)
from backend.config.registry import (
    DuplicateSettingFieldError,
    SettingField,
    all_categories,
    all_fields,
    fields_for_category,
    get_field,
    setting_field,
)

__all__ = [
    "DuplicateSettingFieldError",
    "SettingField",
    "all_categories",
    "all_fields",
    "fields_for_category",
    "get_field",
    "setting_field",
]
