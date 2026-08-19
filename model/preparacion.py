# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
El pronostico de MasterChef Celebrity Paraguay 2026 cuando todavia no hay
casi nada que pronosticar.

Van cuatro galas y una eliminacion. Lo observado, en orden:

  * gala 1, prueba individual de cortes: RDN nombra primero, segundo y tercero,
    y completa los seis destacados sin decir el orden de los otros tres;
  * gala 2, prueba por equipos: tres trios subieron al balcon y tres cayeron a
    la zona de riesgo, sin orden adentro de cada grupo;
  * gala 3, zona de riesgo: de los nueve sentenciados, cuatro se salvaron y
    cinco quedaron abajo. Es un orden parcial entre esos nueve y nadie mas;
  * gala 4: la primera eliminacion. Cayo Jessica Santa Cruz de entre cinco.

El modelo convierte esos ordenes parciales en una posterior sobre la
habilidad de cada persona, y dice con cuanta fuerza. La medida que importa no es
quien puntea sino el indice de ignorancia, que es la entropia de la distribucion
dividida por la entropia maxima. Arranca en 1 y solo baja cuando pasa algo.

    habilidad     theta_i ~ Normal(0, sigma^2)
    prueba        Plackett-Luce sobre exp(alpha_prueba * theta)
    equipos       Plackett-Luce sobre exp(alpha_equipo * promedio del trio)
    riesgo        Plackett-Luce entre los sentenciados, y solo entre ellos
    eliminacion   cae con probabilidad proporcional a exp(-alpha_gala * theta)
                  entre los que estaban en riesgo esa noche

alpha_prueba es cuanto vale una prueba de cuchillo como prediccion de una
temporada entera; alpha_equipo es lo mismo para un resultado repartido entre
tres, y es mas chico por eso. Los escenarios sin_gala1, sin_equipos y sin_nada
apagan cada observacion por separado, que es la forma de leer cuanto movio cada
una.

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
    "alpha_equipo": 0.35,       # cuanto informa un resultado repartido entre tres
    "alpha_gala": 1.00,         # cuanto pesa la habilidad en cada eliminacion
    "orden_completo": False,    # tratar a los tres destacados sin orden como ordenados
}

ESCENARIOS = [
    ("base", {}),
    ("sin_nada", {"alpha_prueba": 0.0, "alpha_equipo": 0.0}),
    ("sin_gala1", {"alpha_prueba": 0.0}),
    ("sin_equipos", {"alpha_equipo": 0.0}),
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


def log_orden_parcial(logw: np.ndarray, bloques: list[list[int]], n: int,
                      universo: list[int] | None = None) -> np.ndarray:
    """
    log P de un orden parcial: una lista de bloques, de mejor a peor.

    Cada bloque es un conjunto de items que la fuente puso en ese escalon sin
    decir en que orden entre ellos. Un bloque de uno es un puesto declarado. Lo
    que no aparece en ningun bloque queda debajo de todos, que es exactamente lo
    que dice una nota cuando nombra a los seis mejores y calla el resto.

    Se suman las permutaciones dentro de cada bloque, que es lo que significa
    «no dijo el orden»: no es lo mismo que inventarle uno.

    universo acota contra quienes se compite. La gala 1 se corrio entre las
    dieciocho; la gala 3, solo entre los nueve que estaban en riesgo, y meter a
    los otros nueve en el denominador seria decir que compitieron y perdieron.
    """
    ramas = None
    for bloque in bloques:
        nuevas = []
        for orden in permutations(bloque):
            nuevas.append(list(orden))
        if ramas is None:
            ramas = nuevas
        else:
            ramas = [previa + extra for previa in ramas for extra in nuevas]

    vivos = np.zeros(n, dtype=bool)
    vivos[universo if universo is not None else range(n)] = True
    apilado = np.stack([log_pl_secuencia(logw, rama, vivos.copy()) for rama in ramas])
    m = apilado.max(axis=0)
    return m + np.log(np.exp(apilado - m).sum(axis=0))


def log_verosimilitud(theta: np.ndarray, obs: dict, par: dict) -> np.ndarray:
    """
    Todo lo que se observo, junto.

    Gala 1, prueba individual: un orden parcial sobre las dieciocho personas.
    Los tres primeros con puesto declarado, los otros tres destacados como
    conjunto. Con orden_completo=True se lee la nota de la forma mas cargada,
    tratando a esos tres como si tuvieran orden.

    Gala 2, prueba por equipos: un orden parcial sobre los seis TRIOS. Tres
    subieron al balcon y tres cayeron a la zona de riesgo, y adentro de cada
    grupo la nota no ordena. La fuerza de un trio es el promedio de sus tres
    habilidades: el plato sale de los tres. Por eso alpha_equipo es mas chico
    que alpha_prueba, porque un resultado repartido entre tres dice menos de
    cada uno que una prueba individual.
    """
    n = theta.shape[1]
    total = np.zeros(theta.shape[0])

    if par["alpha_prueba"] > 0 and obs.get("gala1"):
        g1 = obs["gala1"]
        bloques = [[i] for i in g1["ordenados"]]
        bloques += ([[i] for i in g1["sin_orden"]] if par["orden_completo"]
                    else [list(g1["sin_orden"])])
        total = total + log_orden_parcial(par["alpha_prueba"] * theta, bloques, n)

    # La zona de riesgo: un orden parcial entre los que estaban ahi y nadie mas.
    if par["alpha_prueba"] > 0 and obs.get("riesgo"):
        for r in obs["riesgo"]:
            total = total + log_orden_parcial(
                par["alpha_prueba"] * theta,
                [list(r["arriba"])], n, universo=r["universo"])

    # Las eliminaciones. Es lo que faltaba: hasta la gala 4 no habia ninguna, y
    # el modelo lo decia. Cae quien cocina peor, con probabilidad proporcional a
    # exp(-alpha_gala * theta) entre los que estaban en riesgo esa noche, que es
    # exactamente la misma regla con la que despues se simula la temporada.
    if par["alpha_gala"] > 0 and obs.get("eliminaciones"):
        for e in obs["eliminaciones"]:
            uni = e["universo"]
            w = np.exp(-par["alpha_gala"] * theta[:, uni])
            total = total + (-par["alpha_gala"] * theta[:, e["quien"]]
                             - np.log(w.sum(axis=1)))

    if par["alpha_equipo"] > 0 and obs.get("equipos"):
        eq = obs["equipos"]
        fuerza = np.stack([theta[:, miembros].mean(axis=1) for miembros in eq["miembros"]], axis=1)
        arriba = list(range(len(eq["balcon"])))
        total = total + log_orden_parcial(par["alpha_equipo"] * fuerza, [arriba], len(eq["miembros"]))

    return total


def pesos(rng, n, obs, par):
    """Muestrea la prior y la pesa con todo lo observado. Devuelve (theta, p)."""
    theta = rng.normal(0.0, par["sigma"], size=(N_PARTICULAS, n))
    if par["sigma"] <= 0.0 or (par["alpha_prueba"] <= 0.0 and par["alpha_equipo"] <= 0.0):
        return theta, None
    ll = log_verosimilitud(theta, obs, par)
    ll -= ll.max()
    p = np.exp(ll)
    p /= p.sum()
    return theta, p


def posterior(rng, n, obs, par) -> np.ndarray:
    """Remuestrea segun esos pesos. Devuelve (N_POSTERIOR, n)."""
    theta, p = pesos(rng, n, obs, par)
    if p is None:
        idx = rng.choice(N_PARTICULAS, size=N_POSTERIOR, replace=False)
        return theta[idx]
    idx = rng.choice(N_PARTICULAS, size=N_POSTERIOR, replace=True, p=p)
    return theta[idx]


def n_efectivo(rng, n, obs, par) -> float:
    """Cuantas particulas sobreviven de verdad al remuestreo."""
    _theta, p = pesos(rng, n, obs, par)
    if p is None:
        return float(N_PARTICULAS)
    return float(1.0 / (p ** 2).sum())


# --------------------------------------------------------------------------
# la temporada
# --------------------------------------------------------------------------

def simular(rng, theta_draws: np.ndarray, reps: int, alpha_gala: float,
            fuera: list[int] | None = None):
    """
    Corre la temporada hasta que queda uno.

    En cada ronda sale alguien con probabilidad proporcional a exp(-alpha*theta):
    quien cocina peor cae mas seguido, pero nadie esta a salvo.

    `fuera` son los que ya se fueron. No arrancan la simulacion y su puesto
    final es el que tuvieron de verdad, no uno sorteado: quien ya salio no puede
    ganar, y dejarlo adentro seria repartirle probabilidad a alguien que no esta.
    """
    draws, n = theta_draws.shape
    theta = np.repeat(theta_draws, reps, axis=0)
    s = theta.shape[0]
    riesgo = np.exp(-alpha_gala * theta)
    vivo = np.ones((s, n), dtype=bool)
    puesto = np.zeros((s, n), dtype=np.int16)
    filas = np.arange(s)

    fuera = fuera or []
    for i in fuera:
        vivo[:, i] = False
        puesto[:, i] = n            # todos los que salieron comparten el ultimo escalon
    quedan = n - len(fuera)

    for ronda in range(quedan - 1):
        p = np.where(vivo, riesgo, 0.0)
        p /= p.sum(axis=1, keepdims=True)
        u = rng.random(s)
        elegido = (p.cumsum(axis=1) < u[:, None]).sum(axis=1)
        elegido = np.minimum(elegido, n - 1)
        puesto[filas, elegido] = quedan - ronda
        vivo[filas, elegido] = False

    ganador = vivo.argmax(axis=1)
    puesto[filas, ganador] = 1
    return puesto


def resumen(puesto: np.ndarray, n: int, quedan: int | None = None) -> dict:
    quedan = quedan or n
    return {
        "p_gana": (puesto == 1).mean(axis=0),
        "p_final3": (puesto <= 3).mean(axis=0),
        "p_mitad": (puesto <= quedan // 2).mean(axis=0),
        "p_proxima": (puesto == quedan).mean(axis=0),
    }


def por_lotes(rng, theta: np.ndarray, n: int, alpha_gala: float,
              fuera: list[int] | None = None) -> dict:
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
        r = resumen(simular(rng, trozo, N_TEMPORADAS, alpha_gala, fuera), n,
                    n - len(fuera or []))
        for k in claves:
            acumulado[k].append(r[k])
    salida = {}
    for k in claves:
        m = np.stack(acumulado[k])
        salida[k] = m.mean(axis=0)
        salida[k + "_ee"] = m.std(axis=0, ddof=1) / np.sqrt(N_LOTES)
    return salida


def ignorancia(p: np.ndarray) -> float:
    """
    Entropia sobre entropia maxima. 1 = no sabemos nada, 0 = certeza.

    Se normaliza contra los que SIGUEN, no contra los dieciocho del principio.
    Si se dividiera siempre por log(18), el indice bajaria solo porque queda
    menos gente, y estaria midiendo el paso del tiempo en vez de lo que se sabe.
    Con esta normalizacion, que baje significa que se aprendio algo sobre los
    que quedan.
    """
    vivos = p[p > 0]
    if len(vivos) < 2:
        return 0.0
    q = np.clip(vivos, 1e-12, None)
    return float(-(q * np.log(q)).sum() / np.log(len(vivos)))


# --------------------------------------------------------------------------
# coherencia interna
# --------------------------------------------------------------------------

def calibracion(rng, n, obs, par) -> dict:
    """
    Si el mundo fuera exactamente como el modelo lo describe, el modelo acertaria
    lo que dice acertar?

    Se generan temporadas sinteticas con la misma maquina: habilidad de la prior,
    una gala 1 con su orden parcial, una prueba por equipos con los mismos trios,
    y una temporada completa. Despues se corre la inferencia y se mira si el
    ganador verdadero cae dentro del conjunto de mayor probabilidad al nivel
    nominal.

    Las observaciones sinteticas son las mismas que el modelo usa de verdad: si
    se probara solo con la gala 1 mientras el modelo real usa dos cosas, la
    prueba estaria hablando de otro modelo.

    Esto NO valida el modelo contra la realidad. Comprueba que la maquinaria no
    se contradiga a si misma, que es lo unico comprobable antes de la primera
    eliminacion. La validacion de verdad esta en data/historial_pronostico.json
    y la regla, en EVALUACION.md.
    """
    niveles = [0.5, 0.8, 0.9]
    aciertos = {f"{int(x * 100)}": 0 for x in niveles}
    tamanos = {f"{int(x * 100)}": [] for x in niveles}

    for _ in range(N_CALIBRACION):
        theta_real = rng.normal(0.0, par["sigma"], size=n)
        sintetico = {}

        if obs.get("gala1"):
            orden_prueba = np.argsort(-(par["alpha_prueba"] * theta_real
                                        + rng.gumbel(size=n)))
            sintetico["gala1"] = {"ordenados": [int(i) for i in orden_prueba[:3]],
                                  "sin_orden": sorted(int(i) for i in orden_prueba[3:6])}
        if obs.get("equipos"):
            miembros = obs["equipos"]["miembros"]
            fuerza = np.array([theta_real[m].mean() for m in miembros])
            orden_eq = np.argsort(-(par["alpha_equipo"] * fuerza + rng.gumbel(size=len(miembros))))
            arriba = sorted(int(i) for i in orden_eq[:len(obs["equipos"]["balcon"])])
            reordenado = [miembros[i] for i in arriba] + \
                         [miembros[i] for i in range(len(miembros)) if i not in arriba]
            sintetico["equipos"] = {"balcon": obs["equipos"]["balcon"],
                                    "riesgo": obs["equipos"]["riesgo"],
                                    "miembros": reordenado}

        th = posterior(rng, n, sintetico, par)
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
    fuera = [pos[p["id"]] for p in plantel if p["estado"] != "en_competencia"]

    g1 = galas[0]
    obs = {"gala1": {"ordenados": [pos[x] for x in g1["destacados"]["ordenados"]],
                     "sin_orden": [pos[x] for x in g1["destacados"]["sin_orden"]]}}

    # La prueba por equipos: los seis trios, con los del balcon primero. El
    # orden adentro de cada grupo no se declaro y no se inventa.
    # La zona de riesgo de la gala 3 y las eliminaciones, si las hay.
    obs["riesgo"] = [
        {"arriba": [pos[x] for x in g["balcon"]],
         "universo": [pos[x] for x in g["balcon"] + g["riesgo"]]}
        for g in galas
        if g.get("balcon") and g.get("riesgo") and g.get("prueba") != "equipos"
    ]
    obs["eliminaciones"] = [
        {"quien": pos[g["eliminado"]],
         "universo": [pos[x] for x in (g.get("en_riesgo") or ids)]}
        for g in galas if g.get("eliminado")
    ]

    g2 = next((g for g in galas if g.get("prueba") == "equipos" and g.get("balcon")), None)
    if g2 and g1.get("equipos"):
        por_capitan = {e["capitan"]: [e["capitan"]] + e["companeros"] for e in g1["equipos"]}
        balcon = [c for c in g2["balcon"] if c in por_capitan]
        riesgo = [c for c in g2["riesgo"] if c in por_capitan]
        if len(balcon) + len(riesgo) == len(por_capitan):
            obs["equipos"] = {
                "balcon": balcon,
                "riesgo": riesgo,
                "miembros": [[pos[m] for m in por_capitan[c]] for c in balcon + riesgo],
            }

    salida = {
        "semilla": SEMILLA,
        "observaciones": {
            "gala1": bool(obs.get("gala1")),
            "equipos": bool(obs.get("equipos")),
            "riesgo": len(obs.get("riesgo") or []),
            "eliminaciones": len(obs.get("eliminaciones") or []),
        },
        "n_particulas": N_PARTICULAS,
        "n_posterior": N_POSTERIOR,
        "n_temporadas_por_draw": N_TEMPORADAS,
        "parametros_base": BASE,
        "orden": ids,
        "galas_jugadas": sum(1 for g in galas if g.get("estado") != "anunciada"),
        "eliminados": len(fuera),
        "escenarios": {},
    }

    for nombre, cambios in ESCENARIOS:
        par = {**BASE, **cambios}
        theta = posterior(rng, n, obs, par)
        r = por_lotes(rng, theta, n, par["alpha_gala"], fuera)
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
    # el reparto plano es entre los que quedan, no entre los que empezaron
    plano = 1.0 / (n - len(fuera))
    lider = max(base, key=base.get)
    orden_p = [k for k in sorted(base, key=base.get, reverse=True) if base[k] > 0]
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
        "n_efectivo": round(n_efectivo(rng, n, obs, BASE), 1),
        "n_particulas": N_PARTICULAS,
    }
    salida["calibracion"] = calibracion(rng, n, obs, BASE)
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
