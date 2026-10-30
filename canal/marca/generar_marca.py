"""Genera el kit visual del canal a partir de la marca del editor de videos.

Uso (desde la raíz del repo): python canal/marca/generar_marca.py [--marca dato-mental]
Crea: logo.png (800x800), banner-youtube.png (2560x1440) y miniaturas de ejemplo (1280x720).
Si cambias el nombre, el usuario o los colores en
.claude/skills/editor-videos-virales/marcas/<marca>.json, vuelve a ejecutarlo.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent.parent / ".claude/skills/editor-videos-virales/scripts"))
from comun import buscar_fuente, cargar_marca, hex_rgb  # noqa: E402


def degradado(w, h, c1, c2):
    img = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    return img


def brillo(img, cx, cy, r, color, fuerza=0.5):
    capa = Image.new("RGB", img.size, (0, 0, 0))
    ImageDraw.Draw(capa).ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(int(c * fuerza) for c in color))
    capa = capa.filter(ImageFilter.GaussianBlur(r * 0.45))
    return Image.blend(img, Image.composite(capa, img, capa.convert("L")), 0.9)


def puntos(img, paso, color):
    d = ImageDraw.Draw(img)
    for y in range(paso // 2, img.height, paso):
        for x in range(paso // 2, img.width, paso):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=color)


def texto_ajustado(d, texto, fuente, tam_max, ancho_max):
    tam = tam_max
    while tam > 20:
        f = ImageFont.truetype(fuente, tam)
        if d.textlength(texto, font=f) <= ancho_max:
            return f
        tam -= 4
    return ImageFont.truetype(fuente, 20)


def logo(m, fuente, tam=800):
    col = m["colores"]
    img = degradado(tam, tam, hex_rgb(col["fondo2"]), hex_rgb(col["fondo"]))
    img = brillo(img, tam * 0.5, tam * 0.45, tam * 0.45, hex_rgb(col["acento"]), 0.55)
    d = ImageDraw.Draw(img)
    r, c = tam * 0.40, tam / 2
    d.ellipse([c - r, c - r, c + r, c + r], outline=hex_rgb(col["acento"]), width=int(tam * 0.025))
    inicial = m["nombre"].strip()[0].upper()
    f = ImageFont.truetype(fuente, int(tam * 0.50))
    caja = d.textbbox((0, 0), inicial, font=f)
    w, h = caja[2] - caja[0], caja[3] - caja[1]
    x, y = c - w / 2 - caja[0] - tam * 0.04, c - h / 2 - caja[1]
    d.text((x, y), inicial, font=f, fill=hex_rgb(col["texto"]))
    pr = tam * 0.055  # el "punto" del dato
    px, py = x + caja[2] + pr * 1.4, y + caja[3] - pr
    d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=hex_rgb(col["resalte"]))
    return img


def banner(m, fuente, fuente_texto):
    col = m["colores"]
    W, H = 2560, 1440
    img = degradado(W, H, hex_rgb(col["fondo"]), hex_rgb(col["fondo2"]))
    img = brillo(img, W * 0.18, H * 0.5, 520, hex_rgb(col["acento"]), 0.5)
    img = brillo(img, W * 0.82, H * 0.5, 520, hex_rgb(m.get("pilares", {}).get("Filosofía", col["acento"])), 0.45)
    puntos(img, 64, tuple(int(c * 0.6 + 40) for c in hex_rgb(col["fondo2"])))
    d = ImageDraw.Draw(img)
    # Zona segura (visible en todos los dispositivos): 1546x423 centrada.
    sx, sy, sw, sh = (W - 1546) / 2, (H - 423) / 2, 1546, 423
    lg = logo(m, fuente, 300).resize((300, 300))
    mascara = Image.new("L", (300, 300), 0)
    ImageDraw.Draw(mascara).ellipse([0, 0, 300, 300], fill=255)
    img.paste(lg, (int(sx), int(sy + (sh - 300) / 2)), mascara)
    tx = sx + 350
    f = texto_ajustado(d, m["nombre"].upper(), fuente, 150, sw - 360)
    d.text((tx, sy + 40), m["nombre"].upper(), font=f, fill=hex_rgb(col["texto"]))
    pilares = m.get("pilares", {})
    fp = ImageFont.truetype(fuente_texto, 50)
    x = tx
    for k, (nombre, color) in enumerate(pilares.items()):
        if k:
            d.text((x, sy + 225), "·", font=fp, fill=(140, 150, 180))
            x += d.textlength("· ", font=fp)
        d.text((x, sy + 225), nombre, font=fp, fill=hex_rgb(color))
        x += d.textlength(nombre + " ", font=fp)
    fs = ImageFont.truetype(fuente_texto, 40)
    etiqueta = "NUEVO VIDEO CADA DÍA"
    ew = d.textlength(etiqueta, font=fs) + 60
    d.rounded_rectangle([tx, sy + 315, tx + ew, sy + 385], 35, fill=hex_rgb(col["resalte"]))
    d.text((tx + 30, sy + 325), etiqueta, font=fs, fill=hex_rgb(col["fondo"]))
    return img


def miniatura(m, fuente, fuente_texto, lineas, resaltada, pilar, simbolo):
    col = m["colores"]
    W, H = 1280, 720
    color_p = hex_rgb(m.get("pilares", {}).get(pilar, col["acento"]))
    img = degradado(W, H, hex_rgb(col["fondo"]), hex_rgb(col["fondo2"]))
    img = brillo(img, W * 0.80, H * 0.5, 330, color_p, 0.7)
    puntos(img, 48, tuple(int(c * 0.6 + 35) for c in hex_rgb(col["fondo2"])))
    d = ImageDraw.Draw(img)
    # Símbolo grande a la derecha (sustitúyelo por una imagen en Canva si quieres).
    fs = texto_ajustado(ImageDraw.Draw(img), simbolo, fuente, 380, 380)
    caja = d.textbbox((0, 0), simbolo, font=fs)
    sx = W * 0.81 - (caja[2] - caja[0]) / 2 - caja[0]
    sy = H * 0.5 - (caja[3] - caja[1]) / 2 - caja[1]
    d.text((sx + 10, sy + 14), simbolo, font=fs, fill=(0, 0, 0))
    d.text((sx, sy), simbolo, font=fs, fill=color_p, stroke_width=8, stroke_fill=(255, 255, 255))
    # Etiqueta del pilar.
    fe = ImageFont.truetype(fuente_texto, 38)
    etq = pilar.upper()
    ew = d.textlength(etq, font=fe) + 50
    d.rounded_rectangle([50, 50, 50 + ew, 112], 31, fill=color_p)
    d.text((75, 58), etq, font=fe, fill=(255, 255, 255) if pilar != "Datos" else hex_rgb(col["fondo"]))
    # Texto principal: máximo 3 líneas cortas, una palabra resaltada.
    y = 150
    for linea in lineas:
        f = texto_ajustado(d, linea, fuente, 150, 640)
        x = 50
        for palabra in linea.split():
            color = hex_rgb(col["resalte"]) if palabra.strip("¿?¡!.,") == resaltada else hex_rgb(col["texto"])
            d.text((x + 6, y + 8), palabra, font=f, fill=(0, 0, 0))
            d.text((x, y), palabra, font=f, fill=color, stroke_width=4, stroke_fill=(0, 0, 0))
            x += d.textlength(palabra + " ", font=f)
        y += int(f.size * 1.08)
    usuario = m.get("usuario", "")
    if usuario:
        fu = ImageFont.truetype(fuente_texto, 34)
        d.text((52, H - 70), usuario, font=fu, fill=(200, 210, 235))
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marca", default="dato-mental")
    a = ap.parse_args()
    m = cargar_marca(a.marca)
    fuente, _ = buscar_fuente(m["fuentes"]["titulos"])
    fuente_texto, _ = buscar_fuente(m["fuentes"]["subtitulos"])
    logo(m, fuente).save(AQUI / "logo.png")
    banner(m, fuente, fuente_texto).save(AQUI / "banner-youtube.png")
    ejemplos = [
        ("miniatura-video-1.png", ["10 USOS", "DE LA IA"], "IA", "IA", "AI"),
        ("miniatura-video-2.png", ["¿ES", "REAL?"], "REAL?", "Filosofía", "?"),
        ("miniatura-video-3.png", ["LA IA EN", "10 MINUTOS"], "IA", "Tecnología", "</>"),
        ("miniatura-plantilla-dato.png", ["DATO QUE", "NO SABÍAS"], "NO", "Datos", "!"),
    ]
    for nombre, lineas, resaltada, pilar, simbolo in ejemplos:
        miniatura(m, fuente, fuente_texto, lineas, resaltada, pilar, simbolo).save(AQUI / nombre)
    print("Kit de marca generado en", AQUI)


if __name__ == "__main__":
    main()
