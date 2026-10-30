"""Utilidades compartidas: ffmpeg, rutas, marca, fuentes y colores."""
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ANCHO, ALTO, FPS = 1080, 1920, 30
EXT_VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}

FUENTES_RESPALDO = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def error(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def requiere_ffmpeg():
    for b in ("ffmpeg", "ffprobe"):
        if not shutil.which(b):
            error(f"No se encontró {b}. Instálalo (https://ffmpeg.org) y vuelve a intentarlo.")


def ffmpeg(args, silencioso=True):
    cmd = ["ffmpeg", "-hide_banner", "-y"] + (["-loglevel", "error"] if silencioso else []) + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        error("ffmpeg falló:\n" + " ".join(cmd) + "\n" + r.stderr[-3000:])
    return r


def duracion(ruta):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta)],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        error(f"No se pudo leer la duración de {ruta}")


def dimensiones(ruta):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation", "-of", "json", str(ruta)],
        capture_output=True, text=True)
    s = json.loads(r.stdout or "{}").get("streams", [{}])[0]
    w, h = s.get("width", ANCHO), s.get("height", ALTO)
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        rot = abs(int(sd.get("rotation", 0) or 0))
    return (h, w) if rot in (90, 270) else (w, h)


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir_json(ruta, datos):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def cargar_marca(nombre_o_ruta):
    p = Path(nombre_o_ruta)
    if not p.exists():
        p = RAIZ / "marcas" / f"{nombre_o_ruta}.json"
    if not p.exists():
        disponibles = ", ".join(x.stem for x in (RAIZ / "marcas").glob("*.json"))
        error(f"Marca '{nombre_o_ruta}' no encontrada. Disponibles: {disponibles}")
    return leer_json(p)


def buscar_fuente(nombres):
    """Devuelve (ruta_ttf, nombre_familia). Busca en fuentes/ de la skill y luego en el sistema."""
    locales = list((RAIZ / "fuentes").glob("*.[ot]tf"))
    for n in nombres:
        clave = n.lower().replace(" ", "")
        for f in locales:
            if clave in f.stem.lower().replace("-", "").replace(" ", ""):
                return str(f), familia_de(f)
        if shutil.which("fc-match"):
            r = subprocess.run(["fc-match", "-f", "%{file}|%{family}", n], capture_output=True, text=True)
            ruta, _, fam = r.stdout.partition("|")
            if ruta and n.split(":")[0].lower().replace(" ", "") in fam.lower().replace(" ", ""):
                return ruta, fam.split(",")[0]
    for f in FUENTES_RESPALDO:
        if os.path.exists(f):
            return f, familia_de(f)
    error("No hay ninguna fuente TTF disponible. Copia una en la carpeta fuentes/ de la skill.")


def familia_de(ruta):
    try:
        from PIL import ImageFont
        return ImageFont.truetype(str(ruta), 20).getname()[0]
    except Exception:
        return Path(ruta).stem.split("-")[0]


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hex_ass(h, alfa=0):
    r, g, b = hex_rgb(h)
    return f"&H{alfa:02X}{b:02X}{g:02X}{r:02X}"


def normalizar(palabra):
    s = unicodedata.normalize("NFD", palabra.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ%$]", "", s)


EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D\u2B00-\u2BFF]+")


def sin_emojis(texto):
    return re.sub(r"\s{2,}", " ", EMOJI.sub("", texto)).strip()


def slug(texto):
    s = unicodedata.normalize("NFD", texto.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "video"
