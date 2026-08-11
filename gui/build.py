# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
Construye web/index.html desde data/. Nada se escribe a mano en el HTML.

Cada texto sale de data/i18n.json en los dos idiomas y cada numero sale de un
archivo de data/. Los marcadores de la plantilla son comentarios HTML
<!--== NOMBRE ==-->, que no pueden confundirse con nada del CSS ni del guion.

    python3 gui/build.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "gui"))

from avatares import svg as cara_svg                                   # noqa: E402
from firma import firma_corrida                                        # noqa: E402
from marca import svg as marca_svg                                     # noqa: E402

TEMAS = ["sistema", "claro", "oscuro", "brasa", "kaa", "contraste"]
# El orden es el de quien mira el programa: cuando se juega, quien cocina, como
# va, que paso. El modelo va al final, que es donde lo busca quien lo quiera.
SECCIONES = [
    ("01", "proxima", "nav_proxima"),
    ("02", "plantel", "nav_plantel"),
    ("03", "como-va", "nav_como_va"),
    ("04", "galas", "nav_galas"),
    ("05", "spoilers", "nav_spoilers"),
    ("06", "social", "nav_social"),
    ("07", "ficha", "nav_ficha"),
    ("08", "metodo", "nav_metodo"),
]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_GN = ["jasyteĩ", "jasykõi", "jasyapy", "jasyrundy", "jasypo", "jasypoteĩ",
            "jasypokõi", "jasypoapy", "jasyporundy", "jasypa", "jasypateĩ", "jasypakõi"]
DIAS_GN = {"lunes": "arakõi", "martes": "araapy", "miercoles": "ararundy",
           "miércoles": "ararundy", "jueves": "arapo", "viernes": "arapoteĩ",
           "sabado": "arapokõi", "sábado": "arapokõi", "domingo": "arateĩ"}


# --------------------------------------------------------------------------
# formato
# --------------------------------------------------------------------------

def num(x: float, dec: int = 1) -> str:
    """Castellano y guarani escriben el decimal con coma."""
    return f"{x:.{dec}f}".replace(".", ",")


def pct(x: float, dec: int = 1) -> str:
    return num(x * 100, dec)


def num_corto(x: float) -> str:
    """Sin decimal cuando no hace falta: «17 semanas», no «17,0 semanas»."""
    return num(x, 0) if float(x).is_integer() else num(x, 1)


def fecha(iso: str, idioma: str) -> str:
    d = date.fromisoformat(iso)
    if idioma == "gn":
        return f"{d.day} {MESES_GN[d.month - 1]} {d.year}"
    return f"{d.day} de {MESES_ES[d.month - 1]} de {d.year}"


DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def fecha_corta(d: date, idioma: str) -> str:
    """«martes 11 de agosto» / «araapy 11 jasypoapy»: la fecha como la dice alguien."""
    if idioma == "gn":
        return (f"{DIAS_GN[DIAS_ES[d.weekday()]]} {d.day} "
                f"{MESES_GN[d.month - 1]}")
    return f"{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]}"


def dias(lista: list[str], idioma: str) -> str:
    if idioma == "gn":
        lista = [DIAS_GN.get(d, d) for d in lista]
    return " ha ".join(lista) if idioma == "gn" else " y ".join(lista)


def esc(texto: str) -> str:
    return html.escape(str(texto), quote=False)


# --------------------------------------------------------------------------
# bilingue
# --------------------------------------------------------------------------

class Texto:
    """
    Devuelve los dos idiomas juntos y deja que el CSS elija cual se ve.

    Ninguna traduccion se pide al servidor ni se arma con JavaScript: las dos
    versiones estan en el HTML, asi que la pagina funciona sin guion y un
    buscador ve las dos.
    """

    def __init__(self, i18n: dict, ctx: dict):
        self.i18n = i18n
        self.ctx = ctx

    def crudo(self, clave: str, idioma: str, **extra) -> str:
        entrada = self.i18n[clave]
        return entrada[idioma].format(**{**self.ctx[idioma], **extra})

    def __call__(self, clave: str, tag: str = "span", clase: str = "", **extra) -> str:
        atributo = f' class="{clase}"' if clase else ""
        partes = []
        for idioma in ("es", "gn"):
            cuerpo = esc(self.crudo(clave, idioma, **extra))
            partes.append(f'<{tag} data-l="{idioma}"{atributo}>{cuerpo}</{tag}>')
        return "".join(partes)

    def par(self, clave: str, clase: str = "", **extra) -> str:
        return self.__call__(clave, tag="p", clase=clase, **extra)

    def libre(self, es: str, gn: str, tag: str = "span", clase: str = "") -> str:
        atributo = f' class="{clase}"' if clase else ""
        return (f'<{tag} data-l="es"{atributo}>{esc(es)}</{tag}>'
                f'<{tag} data-l="gn"{atributo}>{esc(gn)}</{tag}>')


# --------------------------------------------------------------------------
# contexto: todo numero que aparece en la prosa entra por aca
# --------------------------------------------------------------------------

def contexto(d: dict) -> dict:
    stats, programa, historia = d["stats"], d["programa"], d["historia"]
    base = stats["escenarios"]["base"]
    sep = stats["separacion"]
    orden = sorted(base["p_gana"], key=base["p_gana"].get, reverse=True)
    nombres = {p["id"]: p["nombre"] for p in d["plantel"]["plantel"]}
    prox = base["p_proxima"]
    c2025 = next(t for t in historia["temporadas"] if t["anho"] == 2025)
    cal = stats["calendario"]

    comun = {
        "n": programa["n_participantes"],
        "galas_jugadas": stats["galas_jugadas"],
        "eliminados": stats["eliminados"],
        "plano_pct": pct(sep["plano"]),
        "ignorancia": num(base["ignorancia"], 3),
        "sabido_pct": pct(1 - base["ignorancia"]),
        "lider": nombres[orden[0]],
        "segundo": nombres[orden[1]],
        "max_pct": pct(base["p_gana"][orden[0]]),
        "segundo_pct": pct(base["p_gana"][orden[1]]),
        "prox_min_pct": pct(min(prox.values())),
        "prox_max_pct": pct(max(prox.values())),
        "ganador_2025": c2025["ganador"],
        "n_calibracion": stats["calibracion"]["n"],
        "eliminaciones": cal["eliminaciones"],
        "emisiones": cal["emisiones_semana"],
        "semanas_rapido": num_corto(cal["semanas_rapido"]),
        "semanas_lento": num_corto(cal["semanas_lento"]),
    }
    return {
        "es": {**comun,
               "estreno": fecha(programa["estreno"], "es"),
               "final_2025": fecha(c2025["final"], "es")},
        "gn": {**comun,
               "estreno": fecha(programa["estreno"], "gn"),
               "final_2025": fecha(c2025["final"], "gn")},
    }


# --------------------------------------------------------------------------
# piezas
# --------------------------------------------------------------------------

def enlace_fuente(d: dict, fid: str, etiqueta: str = "") -> str:
    f = d["fuentes"]["fuentes"][fid]
    texto = etiqueta or f["medio"]
    return (f'<a href="{esc(f["url"])}" rel="noopener noreferrer" target="_blank" '
            f'title="{esc(f["titulo"])} · {f["fecha"]}">{esc(texto)}</a>')


def emisiones(d: dict, cuantas: int = 8) -> list[dict]:
    """
    Las proximas emisiones, en el instante exacto en que empiezan.

    La hora sale de la base de zonas horarias, no de una cuenta a mano: Paraguay
    dejo el horario de verano y va en UTC-3 todo el anho, y eso lo sabe el
    sistema, no yo.
    """
    p = d["programa"]
    tz = ZoneInfo(p["zona_horaria"])
    hora, minuto = (int(x) for x in p["hora"].split(":"))
    dia = date.fromisoformat(p["proxima_gala"])
    salida = []
    while len(salida) < cuantas:
        if dia.isoweekday() in p["dias_iso"]:
            cuando = datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=tz)
            salida.append({
                "iso": cuando.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "es": fecha_corta(dia, "es"),
                "gn": fecha_corta(dia, "gn"),
            })
        dia += timedelta(days=1)
    return salida


def cuenta_regresiva(d: dict, t: Texto) -> str:
    """
    La tarjeta de arriba de todo: cuando es la proxima gala y donde se la ve.

    Sin JavaScript se lee igual, porque la fecha y la hora estan escritas en el
    HTML; el guion solo agrega cuanto falta.
    """
    p = d["programa"]
    prox = emisiones(d)[0]
    donde = "".join(
        f'<a class="hecho" href="{esc(v["url"])}" rel="noopener noreferrer" target="_blank">'
        f'<b>{esc(v["que"])}</b> · {t.libre(v["detalle_es"], v["detalle_gn"])}</a>'
        for v in p["donde_ver"]
    )
    relojes = "".join(
        f'<span class="reloj" data-l="{idioma}" data-faltan="{esc(t.crudo("cd_faltan", idioma))}" '
        f'data-dias="{esc(t.crudo("cd_dias", idioma))}" '
        f'data-horas="{esc(t.crudo("cd_horas", idioma))}" '
        f'data-minutos="{esc(t.crudo("cd_minutos", idioma))}" '
        f'data-aire="{esc(t.crudo("cd_al_aire", idioma))}"></span>'
        for idioma in ("es", "gn")
    )
    return f"""
    <div class="proxima-tarjeta">
      <p class="proxima-rotulo">{t('cd_proxima')}</p>
      <p class="proxima-cuando">
        {t.libre(prox['es'], prox['gn'], clase='proxima-fecha')}<span
          class="proxima-hora">{p['hora']}</span>
      </p>
      <p class="proxima-reloj mono">{relojes}</p>
      <div class="hechos">{donde}</div>
    </div>"""


def portada(d: dict, t: Texto) -> str:
    stats = d["stats"]
    base = stats["escenarios"]["base"]["p_gana"]
    probs = sorted(base.values(), reverse=True)
    vivos = sum(1 for x in d["plantel"]["plantel"] if x["estado"] == "en_competencia")
    cifras = [
        (str(vivos), t("hero_en_competencia")),
        (str(stats["eliminados"]), t("hero_eliminados")),
        (str(stats["galas_jugadas"]), t("hero_galas")),
    ]
    tarjetas = "".join(
        f'<div class="cifra"><span class="cifra-num">{n}</span>{etiqueta}</div>'
        for n, etiqueta in cifras
    )
    indice = "".join(
        f'<a href="#{ancla}"><span class="numero-seccion">{numero}</span> {t(clave)}</a>'
        for numero, ancla, clave in SECCIONES
    )
    return f"""
<header class="portada">
  <div class="envoltura">
    <div class="portada-fila">
      {marca_svg(probs, "japepo")}
      <div>
        <p class="rotulo">{t('hero_eyebrow')}</p>
        <h1>{esc(d['i18n']['titulo_sitio']['es'])}</h1>
        {t('bajada', tag='p', clase='bajada')}
        <div class="cifras">{tarjetas}</div>
      </div>
    </div>
    {cuenta_regresiva(d, t)}
  </div>
  <nav class="envoltura">
    <div class="indice">{indice}</div>
  </nav>
</header>"""


def ficha(d: dict, t: Texto) -> str:
    p, h = d["programa"], d["historia"]
    premio = p["premio_2025"]
    filas = [
        ("ficha_canal", esc(p["canal"]), esc(p["canal"])),
        ("ficha_horario",
         f'{dias(p["dias"], "es")}, {p["hora"]}',
         f'{dias(p["dias"], "gn")}, {p["hora"]}'),
        ("ficha_conduccion", esc(p["conduccion"][0]["nombre"]), esc(p["conduccion"][0]["nombre"])),
        ("ficha_jurado",
         esc(", ".join(j["nombre"] for j in p["jurado"])),
         esc(", ".join(j["nombre"] for j in p["jurado"]))),
        ("ficha_participantes", str(p["n_participantes"]), str(p["n_participantes"])),
        ("ficha_premio",
         f'{premio["monto_guaranies"]:,}'.replace(",", ".") + " ₲",
         f'{premio["monto_guaranies"]:,}'.replace(",", ".") + " ₲"),
    ]
    celdas = "".join(
        f"<div><dt>{t(clave)}</dt><dd>{t.libre(es, gn)}</dd></div>"
        for clave, es, gn in filas
    )
    return f"""
<section id="ficha">
  <div class="envoltura">
    <p class="rotulo">07</p>
    <h2>{t('ficha_h')}</h2>
    <div class="prosa">{t.par('ficha_p')}</div>
    <dl class="ficha">{celdas}</dl>
    <p class="silencio" style="font-size:.84rem;margin-top:.8rem">
      {t('ficha_premio_nota')} · {enlace_fuente(d, 'rdn_final2025')} ·
      {enlace_fuente(d, 'tvpy_estreno')}
    </p>
  </div>
</section>"""


def seccion_proxima(d: dict, t: Texto) -> str:
    """Lo primero que quiere saber quien mira: que pasa esta noche."""
    por_id = {p["id"]: p for p in d["plantel"]["plantel"]}
    g1 = d["galas"]["galas"][0]
    proxima = next((g for g in d["galas"]["galas"] if g.get("estado") == "anunciada"), None)

    capitanes = g1["destacados"]["ordenados"] + g1["destacados"]["sin_orden"]
    fichas = "".join(
        f'<span class="capitan">{cara_svg(por_id[x]["nombre"], x, True)}'
        f'{esc(por_id[x]["corto"])}</span>' for x in capitanes
    )

    desafio = ""
    if proxima:
        desafio = f"""
      <h3>{t('desafio_h')}</h3>
      <div class="prosa">{t.libre(proxima['prueba_detalle_es'],
                                  proxima['prueba_detalle_gn'], tag='p')}</div>
      <h3>{t('en_juego_h')}</h3>
      <div class="prosa">{t.libre(proxima['en_juego_es'], proxima['en_juego_gn'], tag='p')}
        <p class="silencio" style="font-size:.84rem">{t('fuente_label')}:
          {enlace_fuente(d, proxima['en_juego_fuente'])}</p>
      </div>"""

    hora = d["programa"]["hora"]
    filas = "".join(
        f'<li>{t.libre(e["es"], e["gn"])}<span class="mono">{hora}</span></li>'
        for e in emisiones(d, 6)[1:]
    )
    return f"""
<section id="proxima">
  <div class="envoltura">
    <p class="rotulo">01</p>
    <h2>{t('proxima_h')}</h2>
    {desafio}
    <h3>{t('capitanes_h')}</h3>
    <div class="prosa">{t.par('capitanes_p')}</div>
    <div class="capitanes">{fichas}</div>
    <h3>{t('calendario_h')}</h3>
    <div class="prosa">{t.par('calendario_p', clase='silencio')}</div>
    <ul class="calendario">{filas}</ul>
  </div>
</section>"""


def medidor_ignorancia(valor: float) -> str:
    """Un arco: cuanto del total que se puede saber sigue sin saberse."""
    r, circ = 54.0, 2 * 3.141592653589793 * 54.0
    largo = circ * valor
    return (
        '<svg viewBox="0 0 128 128" role="img" aria-hidden="true">'
        f'<circle cx="64" cy="64" r="{r}" fill="none" stroke="var(--fondo-3)" stroke-width="12"/>'
        f'<circle cx="64" cy="64" r="{r}" fill="none" stroke="var(--acento)" stroke-width="12" '
        f'stroke-dasharray="{largo:.2f} {circ - largo:.2f}" stroke-linecap="butt" '
        f'transform="rotate(-90 64 64)"/></svg>'
    )


def barras(d: dict, t: Texto) -> str:
    base = d["stats"]["escenarios"]["base"]
    plano = d["stats"]["separacion"]["plano"]
    nombres = {p["id"]: p["nombre"] for p in d["plantel"]["plantel"]}
    orden = sorted(base["p_gana"], key=base["p_gana"].get, reverse=True)
    tope = max(base["p_gana"].values()) + 3 * max(base["p_gana_ee"].values())

    filas = []
    for pid in orden:
        p = base["p_gana"][pid]
        ee = base["p_gana_ee"][pid]
        izq = max(0.0, p - 2 * ee) / tope * 100
        der = min(1.0, p + 2 * ee) / tope * 100
        filas.append(f"""
      <div class="barra-fila">
        <span class="barra-nombre">{esc(nombres[pid])}</span>
        <span class="pista">
          <span class="valor" style="width:{p / tope * 100:.2f}%"></span>
          <span class="banda" style="left:{izq:.2f}%;width:{der - izq:.2f}%"></span>
          <span class="plano" style="left:{plano / tope * 100:.2f}%"></span>
        </span>
        <span class="barra-num">{pct(p)} %</span>
      </div>""")

    leyenda = (
        f'<span><i style="background:var(--barra)"></i>{t("col_gana")}</span>'
        f'<span><i style="background:var(--banda)"></i>'
        f'{t.libre("margen de simulación", "simulación margen")}</span>'
        f'<span><i style="background:var(--plano)"></i>'
        f'{t.libre("reparto plano", "ñemboja\'o joja")}</span>'
    )
    return f"""
    <div class="barras">{''.join(filas)}</div>
    <div class="leyenda">{leyenda}</div>
    <details class="spoiler" style="margin-top:1.5rem">
      <summary>{t('como_va_leer')}</summary>
      <div class="prosa">{t.par('barras_p')}{t.par('barras_trio')}
        {t.par('ignorancia_p')}{t.par('ignorancia_lectura', clase='silencio')}</div>
    </details>"""


def escenarios(d: dict, t: Texto) -> str:
    stats = d["stats"]
    nombres = {p["id"]: p["nombre"] for p in d["plantel"]["plantel"]}
    filas = []
    for clave, esc_datos in stats["escenarios"].items():
        lider = max(esc_datos["p_gana"], key=esc_datos["p_gana"].get)
        filas.append(f"""
        <tr>
          <td>{t(f'esc_{clave}_n')}</td>
          <td>{t(f'esc_{clave}_d')}</td>
          <td class="entero">{esc(nombres[lider])} · <span class="mono">{pct(esc_datos['p_gana'][lider])} %</span></td>
          <td class="num">{num(esc_datos['ignorancia'], 3)}</td>
        </tr>""")
    return f"""
    <h3>{t('escenarios_h')}</h3>
    <div class="prosa">{t.par('escenarios_p')}</div>
    <div class="tabla-envoltura"><table>
      <thead><tr>
        <th>{t('col_escenario')}</th><th>{t('col_supuesto')}</th>
        <th>{t('col_lider')}</th><th>{t('col_ignorancia')}</th>
      </tr></thead>
      <tbody>{''.join(filas)}</tbody>
    </table></div>"""


def calibracion(d: dict, t: Texto) -> str:
    cal = d["stats"]["calibracion"]
    filas = "".join(
        f'<tr><td class="num">{num(v["nominal"] * 100, 0)} %</td>'
        f'<td class="num">{num(v["observado"] * 100, 1)} %</td>'
        f'<td class="num">{num(v["tamano_medio"], 1)}</td></tr>'
        for v in cal["niveles"].values()
    )
    return f"""
    <h3>{t('calibracion_h')}</h3>
    <div class="prosa">{t.par('calibracion_p')}</div>
    <div class="tabla-envoltura"><table>
      <thead><tr><th>{t('col_nominal')}</th><th>{t('col_observado')}</th>
      <th>{t('col_tamano')}</th></tr></thead>
      <tbody>{filas}</tbody>
    </table></div>"""


def proxima_caida(d: dict, t: Texto) -> str:
    base = d["stats"]["escenarios"]["base"]
    nombres = {p["id"]: p["nombre"] for p in d["plantel"]["plantel"]}
    orden = sorted(base["p_proxima"], key=base["p_proxima"].get, reverse=True)[:6]
    filas = "".join(
        f'<tr><td>{esc(nombres[pid])}</td>'
        f'<td class="num">{pct(base["p_proxima"][pid])} %</td>'
        f'<td class="num">± {pct(2 * base["p_proxima_ee"][pid], 2)}</td></tr>'
        for pid in orden
    )
    return f"""
    <h3>{t('proxima_h')}</h3>
    <div class="prosa">{t.par('proxima_p')}</div>
    <div class="tabla-envoltura"><table>
      <thead><tr><th>{t('col_persona')}</th><th>{t('col_proxima')}</th>
      <th>{t.libre('margen', 'margen')}</th></tr></thead>
      <tbody>{filas}</tbody>
    </table></div>"""


def seccion_como_va(d: dict, t: Texto) -> str:
    """
    Las barras primero y la teoria despues.

    Quien entra quiere ver como va su favorito. El indice de ignorancia es la
    letra chica de esa misma barra, asi que va abajo y en una linea, no arriba
    y en cuerpo cuarenta.
    """
    return f"""
<section id="como-va">
  <div class="envoltura">
    <p class="rotulo">03</p>
    <h2>{t('como_va_h')}</h2>
    <div class="prosa">{t.par('como_va_p')}{t.par('como_va_empate')}</div>
    {barras(d, t)}
    {proxima_caida(d, t)}
  </div>
</section>"""


def plantel(d: dict, t: Texto) -> str:
    base = d["stats"]["escenarios"]["base"]
    g1 = d["galas"]["galas"][0]["destacados"]
    campos = d["plantel"]["campos"]
    por_id = {p["id"]: p for p in d["plantel"]["plantel"]}
    orden = sorted(base["p_gana"], key=base["p_gana"].get, reverse=True)

    tarjetas = []
    for pid in orden:
        p = por_id[pid]
        destacado = pid in g1["ordenados"] or pid in g1["sin_orden"]
        etiquetas = []
        if p["campo"]:
            c = campos[p["campo"]]
            etiquetas.append(f'<span class="etiqueta">{t.libre(c["es"], c["gn"])}</span>')
        else:
            etiquetas.append(f'<span class="etiqueta">{t("sin_confirmar")}</span>')
        if pid in g1["ordenados"]:
            puesto = g1["ordenados"].index(pid) + 1
            etiquetas.append(f'<span class="etiqueta viva">{t("puesto_declarado", puesto=puesto)}</span>')
        elif pid in g1["sin_orden"]:
            etiquetas.append(f'<span class="etiqueta viva">{t("puesto_sin_orden")}</span>')

        nota = t.libre(p["nota_es"], p["nota_gn"], tag="p", clase="persona-nota")
        fuente = enlace_fuente(d, p["nota_fuente"])
        tarjetas.append(f"""
      <article class="persona">
        <div class="persona-cab">
          {cara_svg(p['nombre'], p['id'], destacado)}
          <div>
            <div class="persona-nombre">{esc(p['nombre'])}</div>
            <div class="persona-p">{pct(base['p_gana'][pid])} % {t('chance_ganar')}</div>
          </div>
        </div>
        <div>{''.join(etiquetas)}</div>
        {nota}
        <p class="persona-nota">{t('fuente_label')}: {fuente}</p>
      </article>""")

    return f"""
<section id="plantel">
  <div class="envoltura">
    <p class="rotulo">02</p>
    <h2>{t('plantel_h')}</h2>
    <div class="prosa">{t.par('plantel_p')}{t.par('plantel_orden', clase='silencio')}</div>
    <div class="rejilla">{''.join(tarjetas)}</div>
  </div>
</section>"""


def galas(d: dict, t: Texto) -> str:
    por_id = {p["id"]: p for p in d["plantel"]["plantel"]}
    bloques = []
    for g in d["galas"]["galas"]:
        futura = g.get("estado") == "anunciada"
        meta = [t.libre(fecha(g["fecha"], "es"), fecha(g["fecha"], "gn"))]
        if g.get("minutos"):
            meta.append(t("gala_minutos", minutos=g["minutos"]))
        if g.get("sin_eliminacion"):
            meta.append(t("gala_sin_eliminacion"))
        if futura:
            meta.append(t("gala_anunciada"))
        meta.append(enlace_fuente(d, g["fuente"]))

        podio = ""
        if g.get("destacados"):
            fichas = [
                f'<span class="orden">{i + 1}. {esc(por_id[x]["nombre"])}</span>'
                for i, x in enumerate(g["destacados"]["ordenados"])
            ] + [
                f'<span>{esc(por_id[x]["nombre"])}</span>'
                for x in g["destacados"]["sin_orden"]
            ]
            podio = (f'<p class="silencio" style="margin:.9rem 0 0;font-size:.84rem">'
                     f'{t("gala_destacados")}</p><div class="podio">{"".join(fichas)}</div>')

        consecuencia = ""
        if g.get("consecuencia_es"):
            consecuencia = t.libre(g["consecuencia_es"], g["consecuencia_gn"],
                                   tag="p", clase="persona-nota")

        momentos = ""
        if g.get("momentos"):
            puntos = "".join(f"<li>{t.libre(m['es'], m['gn'])}</li>" for m in g["momentos"])
            momentos = (f'<h4 class="momentos-h">{t("momentos_h")}</h4>'
                        f'<ol class="momentos">{puntos}</ol>')

        bloques.append(f"""
      <div class="gala{' futura' if futura else ''}">
        <h3>{t.libre(f'Gala {g["n"]} · {g["titulo_es"]}', f'Gala {g["n"]} · {g["titulo_gn"]}')}</h3>
        <div class="gala-meta">{' · '.join(meta)}</div>
        <div class="prosa">{t.libre(g['prueba_detalle_es'], g['prueba_detalle_gn'], tag='p')}</div>
        {podio}{consecuencia}{momentos}
      </div>""")

    return f"""
<section id="galas">
  <div class="envoltura">
    <p class="rotulo">04</p>
    <h2>{t('galas_h')}</h2>
    <div class="prosa">{t.par('galas_p')}</div>
    <div style="margin-top:1.5rem">{''.join(bloques)}</div>
  </div>
</section>"""


def spoilers(d: dict, t: Texto) -> str:
    s = d["spoilers"]

    def lista(items):
        return "".join(
            f'<li>{t.libre(i["es"], i["gn"], tag="div")}'
            f'<div class="persona-nota">{t("fuente_label")}: {enlace_fuente(d, i["fuente"])}</div></li>'
            for i in items
        )

    rumores = (f'<ul class="lista-limpia">{lista(s["rumores"])}</ul>' if s["rumores"]
               else t.par("spoilers_rumores_vacio", clase="silencio"))

    return f"""
<section id="spoilers">
  <div class="envoltura">
    <p class="rotulo">05</p>
    <h2>{t('spoilers_h')}</h2>
    <div class="prosa aviso">{t('spoilers_aviso')}</div>
    <details class="spoiler" id="spoilers-abre">
      <summary>{t('spoilers_abrir')}</summary>
      <h3>{t('spoilers_anunciado_h')}</h3>
      <ul class="lista-limpia">{lista(s['anunciado'])}</ul>
      <h3>{t('spoilers_deducido_h')}</h3>
      <div class="prosa">{t.par('spoilers_deducido_p')}</div>
      <h3>{t('spoilers_rumores_h')}</h3>
      <div class="prosa">{rumores}</div>
      <h3>{t('spoilers_falta_h')}</h3>
      <ul class="lista-limpia">{lista(s['no_confirmado'])}</ul>
    </details>
  </div>
</section>"""


def seccion_social(d: dict, t: Texto) -> str:
    """A quien seguir y con que etiqueta se comenta cada gala."""
    cuentas = "".join(
        f'<a class="cuenta" href="{esc(r["url"])}" rel="noopener noreferrer" target="_blank">'
        f'<b>{esc(r["nombre"])}</b><span class="mono">{esc(r["cuenta"])}</span></a>'
        for r in d["programa"]["redes"]
    )
    etiquetas = "".join(
        f'<span class="etiqueta-grande">#{esc(h)}</span>' for h in d["tuits"]["hashtags"]
    )
    lect = d["tuits"]["lectura"]
    return f"""
<section id="social">
  <div class="envoltura">
    <p class="rotulo">06</p>
    <h2>{t('social_h')}</h2>
    <div class="prosa">{t.par('social_p')}</div>
    <h3>{t('seguir_h')}</h3>
    <div class="cuentas">{cuentas}</div>
    <h3>{t('hashtags_h')}</h3>
    <div class="etiquetas-grandes">{etiquetas}</div>
    {tuits(d, t)}
    <h3>{t('tuits_lectura_h')}</h3>
    <div class="prosa">{t.libre(lect['es'], lect['gn'], tag='p')}
      <p class="persona-nota">{t('fuente_label')}: {enlace_fuente(d, lect['fuente'])}</p>
    </div>
  </div>
</section>"""


def tuits(d: dict, t: Texto) -> str:
    tarjetas = []
    for tu in d["tuits"]["tuits"]:
        url = d["fuentes"]["fuentes"][tu["fuente"]]["url"]
        tarjetas.append(f"""
      <article class="tuit">
        <div class="tuit-cab">
          <span class="tuit-handle">@{esc(tu['handle'])}</span>
          <span class="silencio mono">{tu['fecha'][:10]}</span>
        </div>
        <p class="tuit-texto">{esc(tu['texto'])}</p>
        <div class="tuit-pie">
          <a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{t('tuits_cargar')}</a>
          <span class="mono">♥ {tu['me_gusta']}</span>
        </div>
      </article>""")
    return f"""
    <h3>{t('tuits_h')}</h3>
    <div class="prosa">{t.par('tuits_aviso', clase='silencio')}</div>
    <div class="tuits">{''.join(tarjetas)}</div>"""


def metodo(d: dict, t: Texto, firma: str) -> str:
    return f"""
<section id="metodo">
  <div class="envoltura">
    <p class="rotulo">08</p>
    <h2>{t('metodo_h')}</h2>
    <div class="prosa">{t.par('metodo_p')}</div>
    <h3>{t('metodo_modelo_h')}</h3>
    <ul class="lista-limpia prosa">
      <li>{t('metodo_l1')}</li>
      <li>{t('metodo_l2')}</li>
      <li>{t('metodo_l3')}</li>
    </ul>
    <h3>{t('metodo_limites_h')}</h3>
    <ul class="lista-limpia prosa">
      <li>{t('metodo_lim1')}</li>
      <li>{t('metodo_lim2')}</li>
      <li>{t('metodo_lim3')}</li>
    </ul>
    <details class="spoiler">
      <summary>{t('detalle_abrir')}</summary>
      {escenarios(d, t)}
      {calibracion(d, t)}
      {registro(d, t)}
    </details>
    <p class="silencio" style="margin-top:1.2rem">
      {t('metodo_repo')}: <a href="https://github.com/nerln/japepo">nerln/japepo</a> ·
      {t('metodo_firma')}: <span class="mono">{firma}</span>
    </p>
  </div>
</section>"""


def registro(d: dict, t: Texto) -> str:
    entradas = d["historial"]["entradas"]
    nombres = {p["id"]: p["nombre"] for p in d["plantel"]["plantel"]}
    filas = "".join(
        f'<tr><td class="num">{e["fecha"]}</td><td class="num">{e["galas"]}</td>'
        f'<td>{esc(nombres.get(e["lider"], e["lider"]))}</td>'
        f'<td class="num">{pct(e["p_lider"])} %</td>'
        f'<td class="num">{num(e["ignorancia"], 3)}</td></tr>'
        for e in entradas
    )
    vacio = t.par("registro_vacio", clase="silencio") if len(entradas) < 2 else ""
    return f"""
    <h3>{t('registro_h')}</h3>
    <div class="prosa">{t.par('registro_p')}{vacio}</div>
    <div class="tabla-envoltura"><table>
      <thead><tr><th>{t('col_fecha')}</th><th>{t('col_galas')}</th>
      <th>{t('col_lider')}</th><th>{t('col_gana')}</th>
      <th>{t('col_ignorancia')}</th></tr></thead>
      <tbody>{filas}</tbody>
    </table></div>"""


# --------------------------------------------------------------------------

def cargar() -> dict:
    def j(nombre):
        return json.loads((DATA / nombre).read_text())
    return {
        "programa": j("programa.json"),
        "plantel": j("plantel.json"),
        "galas": j("galas.json"),
        "historia": j("historia.json"),
        "stats": j("estadisticas.json"),
        "spoilers": j("spoilers.json"),
        "tuits": j("tuits.json"),
        "fuentes": j("fuentes.json"),
        "i18n": j("i18n.json"),
        "historial": j("historial_pronostico.json"),
    }


def main():
    d = cargar()
    t = Texto(d["i18n"], contexto(d))
    firma = firma_corrida()

    cuerpo = "\n".join([
        portada(d, t), seccion_proxima(d, t), plantel(d, t), seccion_como_va(d, t),
        galas(d, t), spoilers(d, t), seccion_social(d, t), ficha(d, t),
        metodo(d, t, firma),
    ])

    opciones = {
        idioma: "".join(
            f'<option value="{clave}">{esc(d["i18n"][f"tema_{clave}"][idioma])}</option>'
            for clave in TEMAS
        )
        for idioma in ("es", "gn")
    }
    plantilla = (ROOT / "gui" / "plantilla.html").read_text()
    fuentes = (ROOT / "gui" / "fuentes.css")
    if not fuentes.exists():
        raise SystemExit("falta gui/fuentes.css: correr python3 gui/fuentes.py")
    reemplazos = {
        "FUENTES": fuentes.read_text(),
        "ROTULO_IDIOMA_LLANO": esc(d["i18n"]["idioma"]["es"]),
        "IDIOMA_ES": t("idioma_es"),
        "IDIOMA_GN": t("idioma_gn"),
        "ROTULO_TEMA_ES": esc(d["i18n"]["tema"]["es"]),
        "ROTULO_TEMA_GN": esc(d["i18n"]["tema"]["gn"]),
        "CUERPO": cuerpo,
        "OPCIONES_TEMA_ES": opciones["es"],
        "OPCIONES_TEMA_GN": opciones["gn"],
        "LISTA_TEMAS": json.dumps(TEMAS),
        "EMISIONES": json.dumps(emisiones(d, 12), ensure_ascii=False),
        "FIRMA": firma,
        "PIE_AVISO_ES": d["i18n"]["pie_aviso"]["es"],
        "PIE_AVISO_GN": d["i18n"]["pie_aviso"]["gn"],
        "PIE_GUARANI_ES": d["i18n"]["pie_guarani"]["es"],
        "PIE_GUARANI_GN": d["i18n"]["pie_guarani"]["gn"],
        "PIE_TIPOS_ES": d["i18n"]["pie_tipografia"]["es"],
        "PIE_TIPOS_GN": d["i18n"]["pie_tipografia"]["gn"],
        "PIE_FIRMA": f'nerln · {d["i18n"]["pie_licencia"]["es"]} · {firma}',
    }
    for clave, valor in reemplazos.items():
        marcador = f"<!--== {clave} ==-->"
        if marcador not in plantilla:
            raise SystemExit(f"la plantilla no tiene el marcador {marcador}")
        plantilla = plantilla.replace(marcador, valor)

    sobrantes = re.findall(r"<!--==\s*(\w+)\s*==-->", plantilla)
    if sobrantes:
        raise SystemExit(f"quedaron marcadores sin llenar: {sobrantes}")

    WEB.mkdir(exist_ok=True)
    (WEB / "index.html").write_text(plantilla)
    (WEB / "datos.json").write_text(json.dumps({
        "firma": firma,
        "programa": d["programa"],
        "plantel": d["plantel"]["plantel"],
        "galas": d["galas"]["galas"],
        "estadisticas": d["stats"],
        "fuentes": d["fuentes"]["fuentes"],
    }, ensure_ascii=False, indent=2) + "\n")
    (WEB / ".nojekyll").write_text("")

    print(f"  ok · web/index.html ({len(plantilla):,} bytes)")
    print(f"  ok · web/datos.json")
    print(f"  firma · {firma}")


if __name__ == "__main__":
    main()
