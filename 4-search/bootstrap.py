"""Подключение модулей ЛР3: объединённая система берёт рекомендательное ядро из ../3-likesdislikes."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LR3_DIR = HERE.parent / "3-likesdislikes"


def connect_lr3() -> Path:
    """Добавляет каталог ЛР3 в sys.path (один раз) и возвращает его путь."""
    if str(LR3_DIR) not in sys.path:
        sys.path.insert(0, str(LR3_DIR))
    return LR3_DIR


connect_lr3()
