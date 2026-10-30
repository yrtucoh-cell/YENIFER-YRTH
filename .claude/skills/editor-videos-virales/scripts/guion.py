"""Lee un guion en Markdown (formato de canal/guiones/semana-*.md) y extrae la narración.

Uso:
  python guion.py ARCHIVO.md --dia 1 [-o guion.json]
  python guion.py ARCHIVO.txt            (texto plano: todo es narración)
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import escribir_json, error, sin_emojis  # noqa: E402

TOKEN = re.compile(r"(\*\*\[PANTALLA[^\]]*\]\*\*|\[PANTALLA[^\]]*\]|\*\*|✂️|✂)")
META = ("**[VISUAL]**", "**Hashtags:**", "**Nota:**", "**Texto en pantalla:**", "**Formato:**", "**Fuentes:**",
        "**Fuente:**")


def secciones(md):
    partes = re.split(r"^## ", md, flags=re.M)
    return [p for p in partes[1:]]


def elegir_seccion(md, dia, titulo):
    for s in secciones(md):
        cab = s.splitlines()[0]
        if dia is not None and re.match(rf"D[ií]a\s+{dia}\b", cab, flags=re.I):
            return s
        if titulo and titulo.lower() in cab.lower():
            return s
    disp = [s.splitlines()[0] for s in secciones(md)]
    error("No encontré esa sección. Secciones disponibles:\n  " + "\n  ".join(disp))


def palabras_de(lineas, item_de_linea):
    """Convierte las líneas de narración en palabras con banderas."""
    palabras, negrita, recorte, pendientes = [], False, False, []
    for linea, (item, es_cta) in zip(lineas, item_de_linea):
        primera_de_linea = True
        for parte in TOKEN.split(linea):
            if not parte:
                continue
            if "PANTALLA" in parte:
                desc = re.sub(r"[\*\[\]]", "", parte).replace("PANTALLA", "").strip(": ")
                pendientes.append(desc or "pantalla")
                continue
            if parte == "**":
                negrita = not negrita
                continue
            if parte in ("✂️", "✂"):
                recorte = not recorte
                continue
            texto = sin_emojis(parte.replace("*", ""))
            # Puntuación pegada a una negrita ("**tú**?") se une a la palabra anterior.
            m = re.match(r"^([^\w\s¿¡\"“(]+)(.*)", texto)
            if m and palabras and not parte[:1].isspace():
                palabras[-1]["texto"] += m.group(1)
                texto = m.group(2)
            for w in texto.split():
                palabras.append({
                    "texto": w, "negrita": negrita, "recortable": recorte, "cta": es_cta,
                    "item": item if primera_de_linea else None,
                    "marcadores": pendientes,
                })
                pendientes, primera_de_linea = [], False
    if pendientes and palabras:
        palabras[-1].setdefault("marcadores_despues", []).extend(pendientes)
    return palabras


def leer(ruta, dia=None, titulo=None):
    md = Path(ruta).read_text(encoding="utf-8")
    if Path(ruta).suffix.lower() == ".txt" or "## " not in md:
        lineas = [l.strip() for l in md.splitlines() if l.strip()]
        return {"titulo": Path(ruta).stem, "texto_pantalla": "", "hashtags": [],
                "palabras": palabras_de(lineas, [(None, False)] * len(lineas))}
    sec = elegir_seccion(md, dia, titulo)
    cab, *cuerpo = sec.splitlines()
    titulo_sec = re.sub(r"^D[ií]a\s+\d+\s*·\s*", "", cab).strip()
    texto_pantalla, hashtags, lineas, info = "", [], [], []
    for l in cuerpo:
        l = l.strip()
        if not l or l == "---" or l.startswith("#") or l.startswith("```"):
            continue
        if l.startswith("**Texto en pantalla:**"):
            texto_pantalla = l.split(":**", 1)[1].strip().strip('"“”')
            continue
        if l.startswith("**Hashtags:**"):
            hashtags = re.findall(r"#\w+", l)
            continue
        if l.startswith(META) or l.startswith("> "):
            continue
        es_cta = l.startswith("**CTA:**")
        l = l.replace("**CTA:**", "").replace("**[GANCHO]**", "")
        item = None
        m = re.match(r"^(\d+)\.\s+(.*)", l)
        if m:
            item, l = m.group(1), m.group(2)
        elif l.startswith("- "):
            item, l = "•", l[2:]
        lineas.append(l)
        info.append((item, es_cta))
    if not lineas:
        error("La sección no tiene narración.")
    return {"titulo": titulo_sec, "texto_pantalla": sin_emojis(texto_pantalla) or titulo_sec,
            "texto_pantalla_original": texto_pantalla, "hashtags": hashtags,
            "palabras": palabras_de(lineas, info)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--dia", type=int)
    ap.add_argument("--titulo")
    ap.add_argument("-o", "--salida", default="guion.json")
    a = ap.parse_args()
    g = leer(a.archivo, a.dia, a.titulo)
    escribir_json(a.salida, g)
    n = len(g["palabras"])
    rec = sum(p["recortable"] for p in g["palabras"])
    print(f"Guion '{g['titulo']}': {n} palabras ({rec} recortables) → {a.salida}")


if __name__ == "__main__":
    main()
