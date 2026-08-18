# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
EL PUNTAJE: cuanto se acerco cada promesa, con la regla escrita de antes.

EVALUACION.md fija como se puntua «quien cae en esta gala»: Brier multiclase
sobre las personas en competencia, contra la baseline uniforme. Esto lo aplica
sobre lo que quedo congelado en data/historial_pronostico.json ANTES de la
gala, que es la unica forma de que el puntaje signifique algo.

Se reporta ademas el puesto en que la promesa dejo al que efectivamente salio,
que es lo que se entiende sin saber que es un Brier: si el modelo lo tenia
tercero de dieciocho, algo vio; si lo tenia decimoquinto, no vio nada.

    python3 model/puntaje.py --gala 3 --eliminado calonga
    python3 model/puntaje.py --gala 3            (lo lee de data/galas.json)

Escribe la serie «puntajes» de data/historial_pronostico.json, append-only: una
entrada por gala, y no se reescribe.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DESTINO = DATA / "historial_pronostico.json"


def brier(p: dict, quien: str, universo: list[str]) -> float:
    """Brier multiclase: la suma de los cuadrados del error sobre todo el universo."""
    return sum((p.get(n, 0.0) - (1.0 if n == quien else 0.0)) ** 2 for n in universo)


def puntuar(dist: dict, quien: str, universo: list[str]) -> dict:
    n = len(universo)
    orden = sorted(universo, key=lambda x: dist.get(x, 0.0), reverse=True)
    p = dist.get(quien, 0.0)
    plano = {x: 1.0 / n for x in universo}
    return {
        "p_del_eliminado": round(p, 6),
        "puesto": orden.index(quien) + 1,
        "de": n,
        "brier": round(brier(dist, quien, universo), 6),
        "brier_uniforme": round(brier(plano, quien, universo), 6),
        "log_loss": round(-math.log(max(p, 1e-12)), 4),
        "log_loss_uniforme": round(-math.log(1.0 / n), 4),
        "gana_a_la_uniforme": brier(dist, quien, universo) < brier(plano, quien, universo),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gala", type=int, required=True)
    ap.add_argument("--eliminado", default=None, help="id; si falta se lee de data/galas.json")
    args = ap.parse_args()

    h = json.loads(DESTINO.read_text())
    galas = json.loads((DATA / "galas.json").read_text())["galas"]
    nombres = {p["id"]: p["nombre"]
               for p in json.loads((DATA / "plantel.json").read_text())["plantel"]}

    gala = next((g for g in galas if g["n"] == args.gala), None)
    if gala is None:
        raise SystemExit(f"la gala {args.gala} no esta en data/galas.json")
    quien = args.eliminado or gala.get("eliminado")
    if not quien:
        raise SystemExit(f"la gala {args.gala} no tiene eliminado cargado: "
                         "pasarlo con --eliminado o cargarlo en data/galas.json")
    if quien not in nombres:
        raise SystemExit(f"«{quien}» no es un id del plantel")

    promesa = next((p for p in h["predicciones_gala"] if p["gala"] == args.gala), None)
    if promesa is None:
        raise SystemExit(
            f"no hay ninguna promesa escrita para la gala {args.gala}. Puntuar una gala "
            "sin haber publicado antes la prediccion seria escribirla despues de saber, "
            "y eso no es un puntaje. Se deja sin puntuar y se dice.")
    if any(p["gala"] == args.gala for p in h["puntajes"]):
        print(f"  la gala {args.gala} ya estaba puntuada: no se toca")
        return

    universo = promesa["en_riesgo"]
    if quien not in universo:
        raise SystemExit(f"{quien} no estaba en competencia cuando se escribio la promesa")

    entrada = {
        "gala": args.gala,
        "fecha": gala["fecha"],
        "eliminado": quien,
        "en_riesgo": len(universo),
        "regla": "EVALUACION.md, escrita antes de conocer el resultado",
        "corrida_de_la_promesa": promesa["corrida"],
        "modelo": puntuar(promesa["p_cae"], quien, universo),
    }
    h["puntajes"] = sorted(h["puntajes"] + [entrada], key=lambda x: x["gala"])
    DESTINO.write_text(json.dumps(h, ensure_ascii=False, indent=2) + "\n")

    m = entrada["modelo"]
    print(f"  gala {args.gala}: salio {nombres[quien]}")
    print(f"  el modelo lo tenia {m['puesto']}º de {m['de']}, con {m['p_del_eliminado'] * 100:.1f} %")
    print(f"  Brier {m['brier']:.4f} contra {m['brier_uniforme']:.4f} de la uniforme · "
          f"{'gana' if m['gana_a_la_uniforme'] else 'pierde'}")


if __name__ == "__main__":
    main()
