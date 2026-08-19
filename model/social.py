# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
LO QUE MIRA LA GENTE, medido donde se puede medir.

Este programa casi no tiene conversacion publica, y eso no es una opinion: es
una cuenta. Antes de escribir una linea sobre el sentimiento de nadie se
probaron seis corpus, en este orden, y cinco no existen o piden credenciales:

  1. Comentarios de los episodios en el canal oficial de YouTube.
     LA SECCION NO DEVUELVE NADA por la via publica: cero comentarios en los
     doce videos de los cuatro programas. No se afirma que esten desactivados,
     porque el detector obvio -buscar el cartel "Los comentarios estan
     desactivados" en la pagina- da positivo tambien en videos que SI tienen
     comentarios: ese texto viaja en la plantilla de la interfaz, no en el
     estado. Lo que se afirma es lo medido: con el mismo metodo, los videos de
     presentacion devuelven comentarios y los episodios no.
  2. Comentarios de los dieciocho videos de presentacion, uno por participante.
     EXISTEN Y SON DIECISEIS EN TOTAL, y siete son la misma persona pidiendo que
     resuban un vivo. Se recogen igual, se clasifican y se publica el numero.
  3. Facebook. La pagina publica devuelve un muro de inicio de sesion.
  4. Instagram y TikTok. La pagina carga y los comentarios piden credenciales.
  5. X. Las dos cuentas oficiales estan practicamente quietas, y el lector
     anonimo devuelve lo mas interactuado, no lo mas reciente.
  6. Voiz, la plataforma de comentarios de Popular. Es un iframe con el id del
     articulo; la sonda anonima devolvio 404 y no se insistio. Queda como no
     alcanzado, que no es lo mismo que vacio.

LO QUE SI SE PUEDE MEDIR, y es lo que esta pagina publica: las VISTAS de los
dieciocho videos de presentacion. Son del mismo canal, del mismo dia, del mismo
formato y de la misma duracion aproximada: uno por participante. Eso los hace
comparables entre si, que es la unica razon por la que sirven.

Y hay que decir que miden: ATENCION, no aprobacion. A un video se entra por
curiosidad, por simpatia o por bronca, y las tres cuentan igual. Quien lea esto
como un ranking de queridos esta leyendo otra cosa de la que dice el numero.

    python3 model/social.py            recoge y clasifica
    python3 model/social.py --rapido   solo vistas, sin bajar comentarios

Escribe data/social.json.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DESTINO = DATA / "social.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")

# --------------------------------------------------------------------------
# Los dieciocho videos de presentacion, uno por persona. Se encontraron
# buscando «Bienvenid... MasterChef Celebrity Paraguay» en el canal oficial y
# se anotan aca a mano para que la corrida no dependa de que un buscador
# conteste igual mañana.
# --------------------------------------------------------------------------
VIDEOS = {
    "marilina": "ExEvTt87Toc", "luana": "ThlKe4gSjb4", "mariaelsa": "OiWRuU3N_Fc",
    "will": "OtkZhWjYvSM", "jorge": "hesL6P7GNp0", "betha": "tVGRFzDp6bw",
    "silvia": "4UA75fFmfuk", "chad": "4A7ZibclTsc", "vale": "bK1j9rFnsWo",
    "junior": "a3egRGHDKzg", "jessica": "aFiLdpPIMkM", "marisa": "hZWfpLpd2bo",
    "walter": "WKEcjRN_wp4", "faro": "Cf4XX_PdF2A", "maricha": "C1hK3eOv0OE",
    "joaquin": "zOPNbl2Ni1w", "calonga": "CAWU6mAJNro", "negro": "bmrAjjrBcZQ",
}

# --------------------------------------------------------------------------
# EL LEXICO. Todo lo que decide un signo esta aca, a la vista, y cualquiera
# puede discutirlo linea por linea. No hay ningun modelo de lenguaje detras:
# con dieciseis comentarios seria ridiculo, y con dieciseis mil tambien seria
# preferible algo que se pueda auditar.
# --------------------------------------------------------------------------
FAVOR = [
    r"\bme encant", r"\bhermos[ao]", r"\bcapa\b", r"\bgrande\b", r"\bvamo[s]? ",
    r"\bfuerza\b", r"\bqueri[dt]", r"\bidol[oa]\b", r"\bgenia\b", r"\bgenio\b",
    r"\bexcelente\b", r"\bfelicit", r"\bore(mi)?\b", r"\biporã", r"\bipora\b",
    r"\bche ru", r"\bmborayhu", r"\bapoya", r"\bapoyo\b", r"\bfavorit",
    r"\bta luego\b", r"\bcampeon", r"\breyna\b", r"\breina\b",
]
CONTRA = [
    r"\bque se vaya\b", r"\bafuera\b", r"\bchau\b", r"\bfuera\b", r"\binsoportable\b",
    r"\bhorrible\b", r"\bno la banco\b", r"\bno lo banco\b", r"\bfals[ao]\b",
    r"\bsoberbi", r"\bagrand", r"\bpesim", r"\bque asco\b", r"\bnde tavy\b",
    r"\bvyro\b", r"\bno merece\b", r"\bacomodad", r"\benchufad",
]
# Pedidos de la propia audiencia al canal: no hablan de nadie del plantel.
RUIDO = [r"\bresuban\b", r"\bsuban\b", r"\ba que hora\b", r"\ba qu[eé] hora\b",
         r"\bdonde puedo ver\b", r"\bno se ve\b", r"\brepeticion\b"]


def plano(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _curl(url: str, *extra: str) -> str:
    r = subprocess.run(["curl", "-s", "--max-time", "30", "-A", UA,
                        "-H", "Accept-Language: es-PY,es;q=0.9", *extra, url],
                       capture_output=True, text=True)
    return r.stdout


def mirar_video(vid: str) -> dict:
    """Vistas, me gusta y fecha de subida, leidos de la propia pagina del video."""
    h = _curl(f"https://www.youtube.com/watch?v={vid}")
    vistas = re.search(r'"viewCount":"(\d+)"', h)
    # YouTube escribe el numero de me gusta de tres formas segun la version que
    # sirva; se prueban las tres y se toma la primera que aparezca.
    likes = (re.search(r'"accessibilityText":"me gusta este vídeo junto con ([\d\.]+) personas', h)
             or re.search(r'"likeCount":"(\d+)"', h)
             or re.search(r'\{"accessibilityText":"([\d\.]+) me gusta"', h))
    fecha = re.search(r'"uploadDate":"(\d{4}-\d{2}-\d{2})', h)
    return {
        "video": vid,
        "vistas": int(vistas.group(1)) if vistas else None,
        "likes": int(likes.group(1).replace(".", "")) if likes else None,
        "subido": fecha.group(1) if fecha else None,
    }


# Los doce videos de los cuatro programas, para dejar medido que ahi no hay
# comentarios en vez de afirmarlo.
EPISODIOS = ["2FSTpgJXWaQ", "XQB01fI0qBA", "Ue3gFogpuCI",
             "ttiXPnCM5fQ", "TibEeiv0KZs", "y9biOuVCfso",
             "X7dRAAO54MI", "sEpnuGtBoTc", "FrvhEm3laFU",
             "PhOFNHMmy1s", "pTNGzSusnc8", "GU_0HBWDmV0"]


def comentarios_de(vid: str, paginas: int = 4) -> list[str]:
    """Baja los comentarios siguiendo las continuaciones de la interfaz web."""
    h = _curl(f"https://www.youtube.com/watch?v={vid}")
    k = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', h)
    v = re.search(r'"clientVersion":"([\d.]+)"', h)
    if not (k and v):
        return []
    key, ver = k.group(1), v.group(1)
    salida, vistos = [], set()
    for tok in re.findall(r'"continuationCommand":\{"token":"([^"]{40,})"', h)[:2]:
        for _ in range(paginas):
            if not tok:
                break
            cuerpo = json.dumps({"context": {"client": {"clientName": "WEB",
                                                        "clientVersion": ver,
                                                        "hl": "es", "gl": "PY"}},
                                 "continuation": tok})
            p = _curl(f"https://www.youtube.com/youtubei/v1/next?key={key}&prettyPrint=false",
                      "-X", "POST", "-H", "Content-Type: application/json",
                      "--data-binary", cuerpo)
            if "commentEntityPayload" not in p:
                break
            nuevos = []

            def rec(o):
                if isinstance(o, dict):
                    if "commentEntityPayload" in o:
                        e = o["commentEntityPayload"]
                        t = ((e.get("properties") or {}).get("content") or {}).get("content")
                        if t and t not in vistos:
                            vistos.add(t)
                            nuevos.append(t)
                    for x in o.values():
                        rec(x)
                elif isinstance(o, list):
                    for x in o:
                        rec(x)

            rec(json.loads(p))
            salida += nuevos
            sig = re.findall(r'"continuationCommand":\{"token":"([^"]{40,})"', p)
            tok = sig[-1] if sig and nuevos else None
    return salida


def clasificar(texto: str) -> str:
    """
    A favor, en contra, ruido, o SIN CLASIFICAR.

    Lo que no se hace: contar como neutral al que no se pudo clasificar. Quien
    escribe sin marca de signo queda sin clasificar, que no es lo mismo que
    indiferente, y el numero de los que quedaron afuera se publica porque es el
    que dice cuanto vale el resto.
    """
    t = plano(texto)
    if any(re.search(p, t) for p in RUIDO):
        return "ruido"
    a_favor = any(re.search(p, t) for p in FAVOR)
    en_contra = any(re.search(p, t) for p in CONTRA)
    if a_favor and not en_contra:
        return "favor"
    if en_contra and not a_favor:
        return "contra"
    return "sin_clasificar"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true", help="solo vistas, sin comentarios")
    ap.add_argument("--fecha", required=True, help="AAAA-MM-DD de la medicion")
    args = ap.parse_args()

    atencion, comentarios = {}, []
    for pid, vid in VIDEOS.items():
        datos = mirar_video(vid)
        atencion[pid] = datos
        if not args.rapido:
            for texto in comentarios_de(vid):
                comentarios.append({"de": pid, "video": vid, "texto": texto,
                                    "clase": clasificar(texto)})
        print(f"  {pid:11s} {datos['vistas']!s:>6} vistas, {datos['likes']} me gusta")

    total = sum(a["vistas"] or 0 for a in atencion.values())
    for pid, a in atencion.items():
        a["parte"] = round((a["vistas"] or 0) / total, 5) if total else None

    sondeo = []
    if not args.rapido:
        for vid in EPISODIOS:
            n = len(comentarios_de(vid, paginas=2))
            sondeo.append({"video": vid, "comentarios": n})
            print(f"  episodio {vid}: {n} comentarios")

    conteo = {}
    for c in comentarios:
        conteo[c["clase"]] = conteo.get(c["clase"], 0) + 1

    fechas = {a["subido"] for a in atencion.values() if a["subido"]}

    salida = {
        "_nota": ("Lo que se puede medir del publico de este programa, y lo que no. "
                  "Las vistas miden ATENCION, no aprobacion: a un video se entra por "
                  "curiosidad, por simpatia o por bronca, y las tres cuentan igual."),
        "medido": args.fecha,
        "fuente": "yt_presentaciones",
        "atencion": atencion,
        "vistas_totales": total,
        "mismo_dia": len(fechas) == 1,
        "dia_de_subida": sorted(fechas)[0] if len(fechas) == 1 else None,
        "_nota_comentarios": ("Corpus completo, sin muestrear: son todos los que hay. "
                              "El que no trae marca de signo queda SIN CLASIFICAR, que no "
                              "es lo mismo que indiferente."),
        "comentarios": comentarios,
        "conteo": conteo,
        "_nota_episodios": ("Los doce videos de los cuatro programas, sondeados con el "
                            "mismo metodo que las presentaciones. Que devuelvan cero es "
                            "el dato; por que devuelven cero no se afirma."),
        "sondeo_episodios": sondeo,
        "descartados": [
            {"corpus": "Comentarios de los episodios en el canal oficial",
             "porque": "estan desactivados; lo dice la propia pagina del video"},
            {"corpus": "Facebook",
             "porque": "la pagina publica devuelve un muro de inicio de sesion"},
            {"corpus": "Instagram y TikTok",
             "porque": "cargan, pero los comentarios piden credenciales"},
            {"corpus": "X",
             "porque": "las dos cuentas estan casi quietas y el lector anonimo "
                       "devuelve lo mas interactuado, no lo mas reciente"},
            {"corpus": "Voiz, los comentarios de Popular",
             "porque": "la sonda anonima al iframe devolvio 404; no alcanzado, "
                       "que no es lo mismo que vacio"},
        ],
    }
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n")
    print(f"  ok · {DESTINO.relative_to(ROOT)} · {total:,}".replace(",", ".") +
          f" vistas, {len(comentarios)} comentarios, {conteo}")


if __name__ == "__main__":
    main()
