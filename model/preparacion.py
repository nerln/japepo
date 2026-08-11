# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
El pronostico de MasterChef Celebrity Paraguay 2026 cuando todavia no hay
casi nada que pronosticar.

Se jugo una gala. No hubo eliminacion. Lo unico observado es un orden parcial
en una prueba tecnica de cortes: RDN nombra primero, segundo y tercero, y
despues completa los seis destacados sin declarar el orden de los otros tres.
Eso es todo el dato que existe.

El modelo, entonces, hace una sola cosa bien: convertir ese orden parcial en
una posterior sobre la habilidad de cada persona, y decir con cuanta fuerza.
La medida que importa no es quien puntea sino el indice de ignorancia, que es
la entropia de la distribucion dividida por la entropia maxima. Arranca en 1 y
solo baja cuando pasa algo.

    habilidad     theta_i ~ Normal(0, sigma^2)
    prueba        Plackett-Luce sobre exp(alpha_prueba * theta)
    galas         se elimina con probabilidad proporcional a exp(-theta)

alpha_prueba es cuanto vale una prueba de cuchillo como prediccion de una
temporada entera. En el caso base vale 0,6: mide algo, no mide todo. El
escenario sin_gala1 lo pone en cero y devuelve el 1/18 exacto, que es la forma
de leer cuanto movio el unico dato que hay.

    python3 model/preparacion.py

Escribe data/estadisticas.json. No toca ningun otro archivo.
"""

from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SEMILLA = 20260810              # la fecha del estreno, para que la corrida sea repetible
N_PARTICULAS = 200_000          # muestras de la prior antes de pesar
N_POSTERIOR = 1_600             # draws de habilidad que sobreviven al remuestreo
N_TEMPORADAS = 300              # temporadas simuladas por draw
N_LOTES = 8                     # el remuestreo se parte en lotes: de ahi sale el error
N_CALIBRACION = 200             # temporadas sinteticas para la prueba de coherencia

BASE = {
    "sigma": 0.90,              # dispersion de habilidad a priori
    "alpha_prueba": 0.60,       # cuanto informa la prueba de cortes
    "alpha_gala": 1.00,         # cuanto pesa la habilidad en cada eliminacion
    "orden_completo": False,    # tratar a los tres destacados sin orden como ordenados
}

ESCENARIOS = [
    ("base", {}),
    ("sin_gala1", {"alpha_prueba": 0.0}),
    ("corte_manda", {"alpha_prueba": 1.6}),
    ("orden_completo", {"orden_completo": True}),
    ("loteria", {"sigma": 0.0}),
    ("plantel_parejo", {"sigma": 0.45}),
    ("plantel_disparejo", {"sigma": 1.60}),
]


# --------------------------------------------------------------------------
# verosimilitud
# --------------------------------------------------------------------------

def log_pl_secuencia(logw: np.ndarray, orden: list[int], vivos: np.ndarray) -> np.ndarray:
    """
    log P de que 'orden' salga en ese orden, arriba de todos los 'vivos'.

    Plackett-Luce: cada posicion se gana contra los que todavia no salieron.
    logw es (N, n); devuelve (N,).
    """
    restan = vivos.copy()
    total = np.zeros(logw.shape[0])
    w = np.exp(logw)
    denom = (w * restan).sum(axis=1)
    for i in orden:
        total += logw[:, i] - np.log(denom)
        denom -= w[:, i]
        restan[i] = False
    return total


def log_verosimilitud(logw: np.ndarray, ordenados: list[int], sin_orden: list[int],
                      n: int, orden_completo: bool) -> np.ndarray:
    """
    El dato de la gala 1: tres puestos declarados y tres destacados sin orden.

    Los tres primeros entran como secuencia. Los otros tres entran como
    conjunto: se suman las seis permutaciones, que es exactamente lo que
    significa 'la lista se completo con estos tres' sin decir en que orden.
    Con orden_completo=True se toma el orden en que los nombro la nota, para
    ver cuanto cambia leer la fuente de la forma mas cargada.
    """
    vivos = np.ones(n, dtype=bool)
    base = log_pl_secuencia(logw, ordenados, vivos)

    vivos_2 = np.ones(n, dtype=bool)
    for i in ordenados:
        vivos_2[i] = False

    if orden_completo:
        return base + log_pl_secuencia(logw, sin_orden, vivos_2)

    ramas = [base + log_pl_secuencia(logw, list(p), vivos_2)
             for p in permutations(sin_orden)]
    apilado = np.stack(ramas)
    m = apilado.max(axis=0)
    return m + np.log(np.exp(apilado - m).sum(axis=0))


def posterior(rng, n, ordenados, sin_orden, par) -> np.ndarray:
    """Muestrea la prior, la pesa con la gala 1 y remuestrea. Devuelve (N_POSTERIOR, n)."""
    theta = rng.normal(0.0, par["sigma"], size=(N_PARTICULAS, n))
    if par["alpha_prueba"] <= 0.0 or par["sigma"] <= 0.0:
        idx = rng.choice(N_PARTICULAS, size=N_POSTERIOR, replace=False)
        return theta[idx]
    logw = par["alpha_prueba"] * theta
    ll = log_verosimilitud(logw, ordenados, sin_orden, n, par["orden_completo"])
    ll -= ll.max()
    p = np.exp(ll)
    p /= p.sum()
    idx = rng.choice(N_PARTICULAS, size=N_POSTERIOR, replace=True, p=p)
    return theta[idx]


def n_efectivo(rng, n, ordenados, sin_orden, par) -> float:
    """Tamano efectivo de muestra del remuestreo: cuantas particulas sobreviven de verdad."""
    theta = rng.normal(0.0, par["sigma"], size=(N_PARTICULAS, n))
    logw = par["alpha_prueba"] * theta
    ll = log_verosimilitud(logw, ordenados, sin_orden, n, par["orden_completo"])
    ll -= ll.max()
    p = np.exp(ll)
    p /= p.sum()
    return float(1.0 / (p ** 2).sum())


# --------------------------------------------------------------------------
# la temporada
# --------------------------------------------------------------------------

def simular(rng, theta_draws: np.ndarray, reps: int, alpha_gala: float):
    """
    Corre la temporada hasta que queda uno.

    En cada ronda sale alguien con probabilidad proporcional a exp(-alpha*theta):
    quien cocina peor cae mas seguido, pero nadie esta a salvo. Devuelve la
    posicion final de cada persona (1 = gana) por simulacion.
    """
    draws, n = theta_draws.shape
    theta = np.repeat(theta_draws, reps, axis=0)
    s = theta.shape[0]
    riesgo = np.exp(-alpha_gala * theta)
    vivo = np.ones((s, n), dtype=bool)
    puesto = np.zeros((s, n), dtype=np.int16)
    filas = np.arange(s)

    for ronda in range(n - 1):
        p = np.where(vivo, riesgo, 0.0)
        p /= p.sum(axis=1, keepdims=True)
        u = rng.random(s)
        elegido = (p.cumsum(axis=1) < u[:, None]).sum(axis=1)
        elegido = np.minimum(elegido, n - 1)
        puesto[filas, elegido] = n - ronda
        vivo[filas, elegido] = False

    ganador = vivo.argmax(axis=1)
    puesto[filas, ganador] = 1
    return puesto


def resumen(puesto: np.ndarray, n: int) -> dict:
    return {
        "p_gana": (puesto == 1).mean(axis=0),
        "p_final3": (puesto <= 3).mean(axis=0),
        "p_mitad": (puesto <= n // 2).mean(axis=0),
        "p_proxima": (puesto == n).mean(axis=0),
    }


def por_lotes(rng, theta: np.ndarray, n: int, alpha_gala: float) -> dict:
    """
    Corre la simulacion en lotes y devuelve media y error estandar por persona.

    Los lotes no son un detalle de implementacion para no llenar la memoria:
    son de donde sale el error. Cada lote es una estimacion independiente de la
    misma cantidad, y la dispersion entre lotes mide junto lo que aporta la
    posterior y lo que aporta el Monte Carlo. Sin ese numero, el orden entre
    los primeros puestos se lee como si significara algo.
    """
    trozos = np.array_split(theta, N_LOTES)
    claves = ("p_gana", "p_final3", "p_mitad", "p_proxima")
    acumulado = {k: [] for k in claves}
    for trozo in trozos:
        r = resumen(simular(rng, trozo, N_TEMPORADAS, alpha_gala), n)
        for k in claves:
            acumulado[k].append(r[k])
    salida = {}
    for k in claves:
        m = np.stack(acumulado[k])
        salida[k] = m.mean(axis=0)
        salida[k + "_ee"] = m.std(axis=0, ddof=1) / np.sqrt(N_LOTES)
    return salida


def ignorancia(p: np.ndarray) -> float:
    """Entropia sobre entropia maxima. 1 = no sabemos nada, 0 = certeza."""
    q = np.clip(p, 1e-12, None)
    return float(-(q * np.log(q)).sum() / np.log(len(p)))


# --------------------------------------------------------------------------
# coherencia interna
# --------------------------------------------------------------------------

def calibracion(rng, n, par) -> dict:
    """
    Si el mundo fuera exactamente como el modelo lo describe, el modelo acertaria
    lo que dice acertar?

    Se generan temporadas sinteticas con la misma maquina: habilidad de la prior,
    una gala 1 con su orden parcial, y una temporada completa. Despues se corre la
    inferencia y se mira si el ganador verdadero cae dentro del conjunto de mayor
    probabilidad al nivel nominal.

    Esto NO valida el modelo contra la realidad. Comprueba que la maquinaria no se
    contradiga a si misma, que es lo unico comprobable antes de la primera
    eliminacion. La validacion de verdad empieza cuando haya eliminados y esta en
    data/historial_pronostico.json.
    """
    niveles = [0.5, 0.8, 0.9]
    aciertos = {f"{int(x * 100)}": 0 for x in niveles}
    tamanos = {f"{int(x * 100)}": [] for x in niveles}

    for _ in range(N_CALIBRACION):
        theta_real = rng.normal(0.0, par["sigma"], size=n)

        w = np.exp(par["alpha_prueba"] * theta_real)
        gumbel = rng.gumbel(size=n)
        orden_prueba = np.argsort(-(np.log(w) + gumbel))
        ordenados = [int(i) for i in orden_prueba[:3]]
        sin_orden = sorted(int(i) for i in orden_prueba[3:6])

        th = posterior(rng, n, ordenados, sin_orden, {**par, "_": None})
        p = resumen(simular(rng, th, 40, par["alpha_gala"]), n)["p_gana"]

        riesgo = np.exp(-par["alpha_gala"] * theta_real)
        vivo = np.ones(n, dtype=bool)
        for _ronda in range(n - 1):
            q = np.where(vivo, riesgo, 0.0)
            q = q / q.sum()
            vivo[rng.choice(n, p=q)] = False
        ganador = int(np.argmax(vivo))

        orden = np.argsort(-p)
        acumulado = np.cumsum(p[orden])
        for x in niveles:
            k = int(np.searchsorted(acumulado, x) + 1)
            clave = f"{int(x * 100)}"
            tamanos[clave].append(k)
            if ganador in orden[:k]:
                aciertos[clave] += 1

    return {
        "n": N_CALIBRACION,
        "niveles": {
            clave: {
                "nominal": int(clave) / 100,
                "observado": round(aciertos[clave] / N_CALIBRACION, 3),
                "tamano_medio": round(float(np.mean(tamanos[clave])), 2),
            }
            for clave in aciertos
        },
    }


# --------------------------------------------------------------------------

def calendario(programa, historia, n):
    """
    Cuando termina esto.

    Dos cotas, dos supuestos escritos. Si cae una persona por emision, con dos
    emisiones por semana la final llega en unas nueve semanas. Si cae una por
    semana, tarda diecisiete. La edicion 2025 cerro el 17 de septiembre, que
    queda entre las dos.
    """
    emisiones = len(programa["dias"])
    n_elim = n - 1
    rapido_semanas = n_elim / emisiones
    lento_semanas = float(n_elim)
    final2025 = next(t["final"] for t in historia["temporadas"]
                     if t["tipo"] == "celebrity" and t["anho"] == 2025)
    return {
        "eliminaciones": n_elim,
        "emisiones_semana": emisiones,
        "semanas_rapido": round(rapido_semanas, 1),
        "semanas_lento": round(lento_semanas, 1),
        "supuesto_rapido_es": "Una eliminación por emisión.",
        "supuesto_rapido_gn": "Peteĩ ñemosẽ peteĩteĩ emisión-pe.",
        "supuesto_lento_es": "Una eliminación por semana.",
        "supuesto_lento_gn": "Peteĩ ñemosẽ peteĩteĩ semana-pe.",
        "final_2025": final2025,
    }


def main():
    rng = np.random.default_rng(SEMILLA)
    plantel = json.loads((DATA / "plantel.json").read_text())["plantel"]
    galas = json.loads((DATA / "galas.json").read_text())["galas"]
    programa = json.loads((DATA / "programa.json").read_text())
    historia = json.loads((DATA / "historia.json").read_text())

    ids = [p["id"] for p in plantel]
    n = len(ids)
    pos = {pid: i for i, pid in enumerate(ids)}

    g1 = galas[0]
    ordenados = [pos[x] for x in g1["destacados"]["ordenados"]]
    sin_orden = [pos[x] for x in g1["destacados"]["sin_orden"]]

    salida = {
        "semilla": SEMILLA,
        "n_particulas": N_PARTICULAS,
        "n_posterior": N_POSTERIOR,
        "n_temporadas_por_draw": N_TEMPORADAS,
        "parametros_base": BASE,
        "orden": ids,
        "galas_jugadas": sum(1 for g in galas if g.get("estado") != "anunciada"),
        "eliminados": 0,
        "escenarios": {},
    }

    for nombre, cambios in ESCENARIOS:
        par = {**BASE, **cambios}
        theta = posterior(rng, n, ordenados, sin_orden, par)
        r = por_lotes(rng, theta, n, par["alpha_gala"])
        salida["escenarios"][nombre] = {
            "parametros": par,
            "ignorancia": round(ignorancia(r["p_gana"]), 4),
            "p_gana": {pid: round(float(v), 5) for pid, v in zip(ids, r["p_gana"])},
            "p_gana_ee": {pid: round(float(v), 5) for pid, v in zip(ids, r["p_gana_ee"])},
            "p_final3": {pid: round(float(v), 4) for pid, v in zip(ids, r["p_final3"])},
            "p_mitad": {pid: round(float(v), 4) for pid, v in zip(ids, r["p_mitad"])},
            "p_proxima": {pid: round(float(v), 4) for pid, v in zip(ids, r["p_proxima"])},
            "p_proxima_ee": {pid: round(float(v), 5) for pid, v in zip(ids, r["p_proxima_ee"])},
        }

    # el numero que resume todo: cuanto separo la unica gala jugada
    esc = salida["escenarios"]["base"]
    base, ee = esc["p_gana"], esc["p_gana_ee"]
    plano = 1.0 / n
    lider = max(base, key=base.get)
    orden_p = sorted(base, key=base.get, reverse=True)
    # dos personas se distinguen si sus intervalos de +-2 errores no se tocan
    sep_12 = (base[orden_p[0]] - 2 * ee[orden_p[0]]) > (base[orden_p[1]] + 2 * ee[orden_p[1]])
    salida["separacion"] = {
        "lider": lider,
        "max": round(base[lider], 5),
        "max_ee": round(ee[lider], 5),
        "min": round(min(base.values()), 5),
        "plano": round(plano, 5),
        "razon_max_plano": round(base[lider] / plano, 3),
        "primero_distinguible_del_segundo": bool(sep_12),
        "lider_distinguible_del_plano": bool(base[lider] - 2 * ee[lider] > plano),
        "empatados_arriba": [pid for pid in orden_p
                             if base[pid] + 2 * ee[pid] >= base[lider] - 2 * ee[lider]],
        "n_efectivo": round(n_efectivo(rng, n, ordenados, sin_orden, BASE), 1),
        "n_particulas": N_PARTICULAS,
    }
    salida["calibracion"] = calibracion(rng, n, BASE)
    salida["calendario"] = calendario(programa, historia, n)

    destino = DATA / "estadisticas.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n")
    s = salida["separacion"]
    print(f"  ok · {destino.relative_to(ROOT)}")
    print(f"  ignorancia base · {salida['escenarios']['base']['ignorancia']}")
    print(f"  maximo · {s['max']:.4f} +- {s['max_ee']:.4f} "
          f"({s['razon_max_plano']}x el 1/{n})")
    print(f"  arriba sin distinguirse · {len(s['empatados_arriba'])} personas")
    print(f"  n efectivo · {s['n_efectivo']:.0f} de {N_PARTICULAS}")


if __name__ == "__main__":
    main()
