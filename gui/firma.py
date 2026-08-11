# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
La firma de la corrida: un hash corto de todo lo que hay en data/.

Viaja dentro de la pagina. Si alguien edita un dato y no vuelve a construir, la
firma publicada deja de coincidir con la que sale de los datos y gui/verificar.py
lo caza. Es la diferencia entre una pagina que sale de los datos y una pagina que
alguna vez salio de los datos.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def firma_corrida(datos: Path = DATA) -> str:
    h = hashlib.sha256()
    for archivo in sorted(datos.glob("*.json")):
        h.update(archivo.name.encode())
        h.update(archivo.read_bytes())
    return h.hexdigest()[:12]


if __name__ == "__main__":
    print(firma_corrida())
