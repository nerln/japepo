# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
El registro: lo que la pagina prometia cada dia, congelado antes de saber.

Un pronostico que se puede reescribir despues de conocer el resultado no es un
pronostico. Este archivo es append-only y guarda tres series distintas, que se
puntuan por separado porque son afirmaciones de dificultad muy distinta:

  corridas            La foto de cada dia: cuantas galas iban, quien punteaba,
                      cuanta ignorancia quedaba, y la probabilidad de ganar de
                      cada persona. Sirve para dibujar como se movio todo.

  predicciones_gala   La promesa. Antes de cada gala, la distribucion de quien
                      cae. Esta es la que se puntua, y es la unica que importa
                      para saber si el modelo sirve o no.

  puntajes            Lo que escribe model/puntaje.py cuando la gala se
                      resuelve, con la regla que EVALUACION.md fijo antes.

Una entrada escrita no se toca nunca mas. Correrlo dos veces el mismo dia pisa
la entrada de ese dia y no agrega otra; correrlo con una fecha nueva agrega.

    python3 model/registrar.py --fecha 2026-08-18
    python3 model/registrar.py --fecha 2026-08-18 --gala 5

--gala dice a que numero de gala apunta la prediccion de eliminacion. Sin eso
se guarda la corrida pero no la promesa, porque una promesa sin destinatario no
se puede puntuar.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DESTINO = DATA / "historial_pronostico.json"

VACIO = {
    "_nota": ("Append-only. Una entrada por corrida publicada, escrita antes de saber "
              "el resultado. No se edita hacia atras: si una entrada envejece mal, "
              "envejece mal a la vista."),
    "corridas": [],
    "_nota_predicciones": ("Append-only, y a proposito: es la promesa que despues hay que "
                           "puntuar. Cada entrada es la distribucion de quien cae que la "
                           "pagina publicaba ANTES de esa gala. No se reescribe ninguna "
                           "aunque la corrida siguiente diga otra cosa."),
    "predicciones_gala": [],
    "_nota_puntajes": ("Lo escribe model/puntaje.py cuando una gala se resuelve, con la "
                       "regla escrita en EVALUACION.md antes de conocer el resultado."),
    "puntajes": [],
}


def cargar() -> dict:
    if not DESTINO.exists():
        return json.loads(json.dumps(VACIO))
    h = json.loads(DESTINO.read_text())
    # el archivo viejo tenia una sola serie llamada «entradas»
    if "entradas" in h and "corridas" not in h:
        h = {**VACIO, "corridas": h["entradas"]}
    for clave in ("corridas", "predicciones_gala", "puntajes"):
        h.setdefault(clave, [])
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", required=True, help="AAAA-MM-DD, la fecha de la corrida")
    ap.add_argument("--gala", type=int, default=None,
                    help="numero de la gala que viene, si la prediccion de eliminacion apunta a una")
    args = ap.parse_args()

    stats = json.loads((DATA / "estadisticas.json").read_text())
    plantel = json.loads((DATA / "plantel.json").read_text())["plantel"]
    base = stats["escenarios"]["base"]
    vivos = [p["id"] for p in plantel if p["estado"] == "en_competencia"]
    lider = max(base["p_gana"], key=base["p_gana"].get)

    h = cargar()

    corrida = {
        "fecha": args.fecha,
        "galas": stats["galas_jugadas"],
        "eliminados": stats["eliminados"],
        "en_competencia": len(vivos),
        "lider": lider,
        "p_lider": base["p_gana"][lider],
        "p_lider_ee": base["p_gana_ee"][lider],
        "ignorancia": base["ignorancia"],
        "semilla": stats["semilla"],
        "p_gana": {k: v for k, v in base["p_gana"].items() if k in vivos},
    }
    h["corridas"] = sorted([c for c in h["corridas"] if c["fecha"] != args.fecha] + [corrida],
                           key=lambda c: c["fecha"])

    # Sellar la corrida anterior con el commit desde el que salio publicada. En
    # este momento HEAD es exactamente esa publicacion, asi que el dato se toma
    # una sola vez y queda escrito en data/: la pagina no le pregunta nada a git
    # al construirse, que es lo que la mantiene reconstruible en cualquier lado.
    anteriores = [c for c in h["corridas"] if c["fecha"] != args.fecha and not c.get("commit")]
    if anteriores:
        cabeza = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True)
        if cabeza.returncode == 0:
            anteriores[-1]["commit"] = cabeza.stdout.strip()
            print(f"  la corrida del {anteriores[-1]['fecha']} queda sellada con "
                  f"{anteriores[-1]['commit'][:7]}")

    if args.gala is not None:
        ya = any(p["gala"] == args.gala for p in h["predicciones_gala"])
        if ya:
            print(f"  la promesa para la gala {args.gala} ya estaba escrita: no se toca")
        else:
            h["predicciones_gala"].append({
                "gala": args.gala,
                "corrida": args.fecha,
                "en_riesgo": vivos,
                "p_cae": {k: round(v, 6) for k, v in base["p_proxima"].items() if k in vivos},
                "regla": "EVALUACION.md",
            })
            print(f"  promesa escrita para la gala {args.gala}, sobre {len(vivos)} personas")

    DESTINO.write_text(json.dumps(h, ensure_ascii=False, indent=2) + "\n")
    print(f"  ok · {DESTINO.relative_to(ROOT)} · {len(h['corridas'])} corridas, "
          f"{len(h['predicciones_gala'])} promesas, {len(h['puntajes'])} puntajes")


if __name__ == "__main__":
    main()
