# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
Lo que se publica tiene que salir de lo que esta publicado.

Es la unica prueba que corre antes de desplegar y contesta una pregunta: la
pagina que hay en web/ se puede reconstruir desde data/ tal como esta en el
repositorio? Si alguien edita un numero a mano en el HTML, o commitea data/
nuevo sin volver a construir, esto falla y la pagina no sale.

Ademas comprueba lo que haria falsa la pagina sin romper nada visible:

  * las probabilidades de cada escenario suman uno
  * cada dato publicado apunta a una fuente que existe en data/fuentes.json
  * cada texto existe en los dos idiomas, y los marcadores de cada idioma se
    rellenan sin faltar ninguno
  * ningun numero decimal escrito a mano en la prosa: si tiene fuente en
    data/, entra como marcador
  * ningun texto traducido a dos idiomas que ya no aparezca en ninguna seccion
  * la pagina no pide un solo archivo a otro servidor, asi que funciona sin
    red y no registra a nadie por abrirla
  * ninguna foto de ningun participante
  * los seis temas declaran las mismas variables, asi que ninguno se rompe a
    medias
  * el aviso de no afiliacion sigue en la pagina
  * la firma de la corrida coincide con la que sale de los datos, y la
    tarjeta de previsualizacion tambien es de esta corrida
  * el guion parsea y el <style> no tiene JavaScript adentro
  * las tres tipografias viajan adentro de la pagina, con su licencia
  * ningun signo de la pagina se quedo fuera del recorte de las fuentes

Las dos ultimas no comprueban ningun dato: comprueban que la pagina no este
rota de una forma que no cambia ningun dato y por eso no la ve nadie mas.

    python3 gui/verificar.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "gui"))

from build import SECCIONES, TEMAS, Texto, contexto, cargar   # noqa: E402
from firma import firma_corrida                               # noqa: E402

TOL = 1e-9


def falla(msg: str) -> int:
    print("  FALLA · " + msg)
    return 1


def bien(msg: str) -> int:
    print("  ok · " + msg)
    return 0


# --------------------------------------------------------------------------

def reconstruible() -> int:
    # El PNG queda fuera de la comparacion byte a byte a proposito: la compresion
    # y el dibujado de las letras cambian con la version de zlib y de FreeType, y
    # la del servidor de integracion no es la de la maquina donde se construyo.
    # Que la tarjeta sea de esta corrida lo comprueba tarjeta_al_dia().
    antes = {p.name: p.read_bytes() for p in WEB.glob("*")
             if p.suffix in (".html", ".json", ".svg")}
    if not antes:
        return falla("web/ esta vacio: correr gui/build.py")
    for guion in ("build.py", "tarjeta.py"):
        r = subprocess.run([sys.executable, str(ROOT / "gui" / guion)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            ultima = (r.stderr.strip().splitlines() or ["sin mensaje"])[-1]
            return falla(f"gui/{guion} no llega a construir lo suyo: " + ultima)
    malos = [n for n, b in antes.items() if (WEB / n).read_bytes() != b]
    if malos:
        return falla("web/ no coincide con lo que produce gui/build.py: "
                     + ", ".join(sorted(malos)) + ". Correr gui/build.py y commitear.")
    return bien(f"web/ reconstruible ({len(antes)} archivos)")


def tarjeta_al_dia(firma_publicada: str | None) -> int:
    """La tarjeta que se comparte tiene que ser la de los datos de hoy."""
    esperada = firma_corrida()
    if firma_publicada is None:
        return falla("web/og.png no lleva firma de corrida: correr gui/tarjeta.py")
    if firma_publicada != esperada:
        return falla(f"la tarjeta publicada es de la corrida {firma_publicada} y los datos "
                     f"son de la {esperada}. Correr gui/tarjeta.py y commitear.")
    return bien(f"la tarjeta de previsualizacion es de esta corrida ({esperada})")


def leer_firma_tarjeta() -> str | None:
    """Se lee ANTES de reconstruir nada, o se estaria mirando la recien hecha."""
    try:
        from PIL import Image                                  # noqa: PLC0415
        with Image.open(WEB / "og.png") as im:
            return im.info.get("japepo:firma")
    except Exception:
        return None


def probabilidades(d: dict) -> int:
    err = 0
    for nombre, e in d["stats"]["escenarios"].items():
        for campo in ("p_gana", "p_proxima"):
            s = sum(e[campo].values())
            if abs(s - 1) > 1e-3:
                err += falla(f"{campo} del escenario {nombre} suma {s!r}")
    if err:
        return err
    return bien(f"{len(d['stats']['escenarios'])} escenarios suman uno")


def fuentes(d: dict) -> int:
    conocidas = set(d["fuentes"]["fuentes"])
    usadas: set[str] = set()

    def mirar(nodo):
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                if clave in ("fuente", "campo_fuente", "nota_fuente") and isinstance(valor, str):
                    usadas.add(valor)
                elif clave == "fuentes" and isinstance(valor, list):
                    usadas.update(x for x in valor if isinstance(x, str))
                else:
                    mirar(valor)
        elif isinstance(nodo, list):
            for x in nodo:
                mirar(x)

    for nombre in ("programa", "plantel", "galas", "historia", "spoilers", "tuits"):
        mirar(d[nombre])

    huerfanas = sorted(usadas - conocidas)
    if huerfanas:
        return falla("fuentes citadas que no existen en data/fuentes.json: " + ", ".join(huerfanas))
    sueltas = sorted(conocidas - usadas)
    print(f"  ok · {len(usadas)} fuentes citadas, todas registradas"
          + (f" ({len(sueltas)} registradas sin usar)" if sueltas else ""))
    return 0


def idiomas(d: dict) -> int:
    i18n = d["i18n"]
    t = Texto(i18n, contexto(d))
    err = 0
    claves = [k for k in i18n if not k.startswith("_")]
    for clave in claves:
        entrada = i18n[clave]
        if not isinstance(entrada, dict) or set(entrada) - {"es", "gn"}:
            err += falla(f"la clave {clave} no tiene la forma es/gn")
            continue
        faltan = {"es", "gn"} - set(entrada)
        if faltan:
            err += falla(f"la clave {clave} no esta en {', '.join(sorted(faltan))}")
            continue
        if entrada["es"].strip() == "" or entrada["gn"].strip() == "":
            err += falla(f"la clave {clave} esta vacia en un idioma")
        marcadores_es = set(re.findall(r"\{(\w+)\}", entrada["es"]))
        marcadores_gn = set(re.findall(r"\{(\w+)\}", entrada["gn"]))
        if marcadores_es != marcadores_gn:
            err += falla(f"la clave {clave} usa marcadores distintos en cada idioma: "
                         f"{sorted(marcadores_es)} contra {sorted(marcadores_gn)}")
        for idioma in ("es", "gn"):
            try:
                t.crudo(clave, idioma, puesto=1, minutos=1)
            except KeyError as exc:
                err += falla(f"la clave {clave} en {idioma} pide un marcador que no existe: {exc}")
    if err:
        return err
    return bien(f"{len(claves)} textos en los dos idiomas")


def textos_huerfanos(d: dict) -> int:
    """
    Ningun texto traducido dos veces para no aparecer en ninguna parte.

    Cuando una seccion cambia de forma, las claves viejas se quedan en
    data/i18n.json y nadie las borra: son dos idiomas de trabajo tirados, y de
    paso hacen creer que la pagina dice algo que ya no dice.
    """
    fuente = ((ROOT / "gui" / "build.py").read_text()
              + (ROOT / "gui" / "plantilla.html").read_text())
    claves = [k for k in d["i18n"] if not k.startswith("_")]
    sueltas = [k for k in claves
               if f"'{k}'" not in fuente and f'"{k}"' not in fuente
               and f"esc_{k}" not in fuente]
    # los escenarios y los temas se arman con el nombre adentro de un f-string
    dinamicas = {f"esc_{n}_{s}" for n in d["stats"]["escenarios"] for s in ("n", "d")}
    dinamicas |= {f"tema_{n}" for n in TEMAS}
    sueltas = [k for k in sueltas if k not in dinamicas]
    if sueltas:
        return falla("textos traducidos que ya no usa ninguna seccion: " + ", ".join(sueltas)
                     + ". Borrarlos de data/i18n.json o volver a usarlos.")
    return bien(f"los {len(claves)} textos se usan en la pagina")


def numeros_a_mano(d: dict) -> int:
    """
    Un decimal escrito en la prosa envejece en silencio.

    Los enteros pasan: un anho, una version de licencia, una hora. Lo que no
    pasa es un decimal o un porcentaje, porque esos salen del modelo y cambian
    en cada corrida.
    """
    # nombres de licencia: llevan numero y no salen de ninguna corrida
    literales = ("Apache-2.0", "CC BY 4.0", "Open Font License 1.1")
    sospechosos = []
    for clave, entrada in d["i18n"].items():
        if clave.startswith("_"):
            continue
        for idioma, texto in entrada.items():
            limpio = re.sub(r"\{\w+\}", "", texto)
            for literal in literales:
                limpio = limpio.replace(literal, "")
            if re.search(r"\d+[.,]\d", limpio) or re.search(r"\d+\s*(%|por ciento|porciento)", limpio):
                sospechosos.append(f"{clave}/{idioma}")
    if sospechosos:
        return falla("numeros escritos a mano en la prosa: " + ", ".join(sospechosos))
    return bien("ningun numero del modelo escrito a mano")


def sin_red(html: str) -> int:
    """La pagina no pide nada a ningun otro servidor."""
    err = 0
    if re.search(r"<img\b", html, re.I):
        err += falla("hay una etiqueta <img>: las figuras se generan, no se traen")
    for etiqueta, atributo in (("script", "src"), ("link", "href"), ("iframe", "src"),
                               ("source", "src"), ("video", "src"), ("audio", "src")):
        for m in re.finditer(rf"<{etiqueta}\b[^>]*?{atributo}=[\"']([^\"']+)[\"']", html, re.I):
            destino = m.group(1)
            if etiqueta == "link":
                # canonical y alternate son metadatos: no descargan nada
                if re.search(r'rel=["\'](canonical|alternate)', m.group(0), re.I):
                    continue
                # lo que si descarga, solo desde la propia carpeta
                if not re.match(r"[a-z]+:|//", destino, re.I):
                    continue
            err += falla(f"<{etiqueta}> pide {destino} a otro servidor")
    if re.search(r"url\(\s*[\"']?https?:", html, re.I):
        err += falla("el CSS pide un archivo remoto")
    if err:
        return err
    return bien("la pagina no pide nada a otro servidor")


def sin_fotos(html: str) -> int:
    """
    La unica imagen de mapa de bits permitida es la tarjeta de previsualizacion,
    que la dibuja gui/tarjeta.py desde los datos y no lleva la cara de nadie.
    """
    sospechosas = [m.group(0) for m in re.finditer(r"[\w./-]+\.(jpg|jpeg|png|webp|avif|gif)\b",
                                                   html, re.I)
                   if not m.group(0).endswith("og.png")]
    if sospechosas:
        return falla("hay imagenes de mapa de bits ajenas a la tarjeta: "
                     + ", ".join(sorted(set(sospechosas))[:4]))
    if "og.png" not in html:
        return falla("falta la tarjeta de previsualizacion en los metadatos")
    return bien("ninguna foto de nadie; la unica imagen es la tarjeta generada")


def temas(html: str) -> int:
    bloques = dict(re.findall(r':root\[data-tema="(\w+)"\]\s*\{([^}]*)\}', html))
    base = re.search(r":root\s*\{([^}]*)\}", html)
    if not base:
        return falla("no se encontro el bloque :root")
    esperadas = {m for m in re.findall(r"(--[\w-]+):", base.group(1))}
    # el tema claro es el :root, y sistema hereda salvo en modo oscuro
    color = {v for v in esperadas if not v.startswith(("--tipo", "--radio", "--sombra"))}
    err = 0
    declarados = set(bloques) | {"claro", "sistema"}
    faltan_temas = set(TEMAS) - declarados
    if faltan_temas:
        err += falla("temas sin bloque de color: " + ", ".join(sorted(faltan_temas)))
    for nombre, cuerpo in bloques.items():
        tiene = {m for m in re.findall(r"(--[\w-]+):", cuerpo)}
        faltan = color - tiene
        if faltan:
            err += falla(f"el tema {nombre} no define " + ", ".join(sorted(faltan)))
    if err:
        return err
    return bien(f"{len(TEMAS)} temas completos ({len(color)} variables cada uno)")


def anclas(html: str) -> int:
    err = 0
    for _numero, ancla, _clave in SECCIONES:
        if f'id="{ancla}"' not in html:
            err += falla(f"el indice apunta a #{ancla} y esa seccion no existe")
    if err:
        return err
    return bien(f"{len(SECCIONES)} secciones enlazadas desde el indice")


def aviso(html: str, d: dict) -> int:
    trozo = d["i18n"]["pie_aviso"]["es"][:60]
    if trozo not in html:
        return falla("el aviso de no afiliacion no esta en la pagina")
    if "no-afiliacion" not in html:
        return falla("falta el meta de no afiliacion")
    return bien("aviso de no afiliacion en el pie y en un meta")


def firma(html: str) -> int:
    esperada = firma_corrida()
    hallada = re.search(r'name="japepo:firma" content="(\w+)"', html)
    if not hallada:
        return falla("la pagina no lleva firma de corrida")
    if hallada.group(1) != esperada:
        return falla(f"la firma publicada ({hallada.group(1)}) no es la de los datos ({esperada}). "
                     "Alguien toco data/ sin volver a construir.")
    return bien(f"firma de corrida {esperada}")


def guion(html: str) -> int:
    cuerpos = re.findall(r"<script>(.*?)</script>", html, re.S)
    if not cuerpos:
        return falla("no se encontro el guion de la pagina")
    if not shutil.which("node"):
        print("  aviso · sin node, no se comprueba que el guion parsee")
        return 0
    for i, cuerpo in enumerate(cuerpos):
        tmp = WEB / f".guion{i}.js"
        tmp.write_text(cuerpo)
        r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
        tmp.unlink()
        if r.returncode != 0:
            return falla("el guion no parsea: " + r.stderr.strip().splitlines()[0])
    return bien(f"{len(cuerpos)} guion parsea")


def estilo_limpio(html: str) -> int:
    """El fallo de placa: JavaScript adentro del <style> y el navegador callado."""
    for cuerpo in re.findall(r"<style>(.*?)</style>", html, re.S):
        # las fuentes viajan en base64, y ahi adentro puede aparecer cualquier
        # cadena de letras por puro azar: se saca antes de mirar
        limpio = re.sub(r"url\(data:[^)]*\)", "", cuerpo)
        if re.search(r"\b(function|addEventListener|localStorage|var |const |=>)", limpio):
            return falla("hay JavaScript adentro del <style>")
    return bien("el <style> no tiene JavaScript adentro")


def fuentes_incrustadas(html: str) -> int:
    """Las tres familias tienen que viajar adentro, no pedirse a nadie."""
    caras = re.findall(r"@font-face\{([^}]*)\}", html)
    if not caras:
        return falla("la pagina no lleva ninguna tipografia incrustada: correr gui/fuentes.py")
    externas = [c for c in caras if "url(data:font/woff2;base64," not in c]
    if externas:
        return falla(f"{len(externas)} @font-face piden un archivo en vez de llevarlo adentro")
    familias = {re.search(r'font-family:"([^"]+)"', c).group(1) for c in caras}
    esperadas = {"Be Vietnam Pro", "Japepo Serif", "Japepo Mono"}
    if familias != esperadas:
        return falla(f"las familias incrustadas son {sorted(familias)} y se esperaban "
                     f"{sorted(esperadas)}")
    if "SIL Open Font License" not in html:
        return falla("falta el aviso de licencia de las tipografias adentro de la pagina")
    return bien(f"{len(caras)} caras incrustadas, {len(familias)} familias, con su licencia")


def signos_cubiertos(html: str) -> int:
    """
    Ningun signo de la pagina puede quedar fuera del recorte de las fuentes.

    Un nombre nuevo en data/ con una letra que el recorte no trae no rompe
    nada visible: el navegador la dibuja con otra tipografia y queda un renglon
    con dos letras de otro color de tinta. Esto lo caza antes.
    """
    sys.path.insert(0, str(ROOT / "gui"))
    from fuentes import CHARSET                                   # noqa: PLC0415

    visible = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    visible = re.sub(r"<[^>]+>", " ", visible)
    visible = (visible.replace("&nbsp;", " ").replace("&amp;", "&")
               .replace("&lt;", "<").replace("&gt;", ">").replace("&#039;", "'"))
    faltan = sorted({c for c in visible if c not in CHARSET and c not in "\n\t\r"})
    if faltan:
        return falla("la pagina usa signos que el recorte de las fuentes no trae: "
                     + " ".join(f"{c!r} (U+{ord(c):04X})" for c in faltan)
                     + ". Agregarlos a CHARSET en gui/fuentes.py y correrlo.")
    return bien(f"todos los signos de la pagina estan en el recorte ({len(CHARSET)} declarados)")


def coherencia(d: dict) -> int:
    err = 0
    n = d["programa"]["n_participantes"]
    ids = [p["id"] for p in d["plantel"]["plantel"]]
    if len(ids) != n:
        err += falla(f"programa dice {n} participantes y plantel trae {len(ids)}")
    if len(set(ids)) != len(ids):
        err += falla("hay ids repetidos en el plantel")
    if d["stats"]["orden"] != ids:
        err += falla("estadisticas.json se corrio con otro plantel: correr model/preparacion.py")
    for g in d["galas"]["galas"]:
        if not g.get("destacados"):
            continue
        marcados = g["destacados"]["ordenados"] + g["destacados"]["sin_orden"]
        desconocidos = [x for x in marcados if x not in ids]
        if desconocidos:
            err += falla(f"la gala {g['n']} destaca a alguien que no esta en el plantel: {desconocidos}")
        if len(set(marcados)) != len(marcados):
            err += falla(f"la gala {g['n']} destaca dos veces a la misma persona")
    ultima = d["historial"]["entradas"][-1]
    base = d["stats"]["escenarios"]["base"]
    if abs(ultima["ignorancia"] - base["ignorancia"]) > TOL:
        err += falla("la ultima entrada del registro no es de esta corrida: correr model/registrar.py")
    if err:
        return err
    return bien(f"{n} personas, {len(d['galas']['galas'])} galas y el registro al dia")


def main() -> int:
    print("japepo · verificacion")
    d = cargar()
    firma_publicada = leer_firma_tarjeta()
    err = reconstruible()
    err += tarjeta_al_dia(firma_publicada)
    html = (WEB / "index.html").read_text()
    err += probabilidades(d)
    err += fuentes(d)
    err += idiomas(d)
    err += textos_huerfanos(d)
    err += numeros_a_mano(d)
    err += coherencia(d)
    err += sin_red(html)
    err += sin_fotos(html)
    err += temas(html)
    err += anclas(html)
    err += aviso(html, d)
    err += firma(html)
    err += guion(html)
    err += estilo_limpio(html)
    err += fuentes_incrustadas(html)
    err += signos_cubiertos(html)
    print("  todo en orden" if err == 0 else f"  {err} fallas")
    return 1 if err else 0


if __name__ == "__main__":
    raise SystemExit(main())
