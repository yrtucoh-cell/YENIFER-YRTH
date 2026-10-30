"""Genera 6 propuestas de logo para Dato Mental.

Uso (desde la raíz del repo): python canal/marca/logos/generar_logos.py
Crea, por cada propuesta: <n>-<nombre>-icono.png (1024x1024, foto de perfil) y
<n>-<nombre>-horizontal.png (2000x600, icono + nombre), más comparativa.png con todas.
Se dibuja a 4x y se reduce para que los bordes queden suaves.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).resolve().parent
FUENTES = Path("/usr/share/fonts/opentype/inter")
NEGRA = str(FUENTES / "Inter-Black.otf")
EXTRA = str(FUENTES / "Inter-ExtraBold.otf")
SEMI = str(FUENTES / "Inter-SemiBold.otf")

FONDO, FONDO2 = (11, 16, 32), (20, 30, 66)
AZUL, AZUL_CLARO = (59, 130, 246), (96, 165, 250)
AMARILLO = (250, 204, 21)
VIOLETA, CIAN = (168, 85, 247), (6, 182, 212)
BLANCO = (255, 255, 255)

S = 4096  # lienzo de trabajo (se reduce a 1024)


def f(ruta, tam):
    return ImageFont.truetype(ruta, int(tam))


def lienzo(c1=FONDO2, c2=FONDO, brillo=AZUL, fuerza=0.55):
    img = Image.new("RGB", (S, S), c1)
    d = ImageDraw.Draw(img)
    for y in range(0, S, 4):
        t = y / S
        d.rectangle([0, y, S, y + 4], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    if brillo:
        capa = Image.new("RGB", (S, S), (0, 0, 0))
        r = S * 0.42
        ImageDraw.Draw(capa).ellipse([S / 2 - r, S * 0.46 - r, S / 2 + r, S * 0.46 + r],
                                     fill=tuple(int(c * fuerza) for c in brillo))
        capa = capa.resize((256, 256)).filter(ImageFilter.GaussianBlur(40)).resize((S, S))
        img = Image.blend(img, Image.composite(capa, img, capa.convert("L")), 0.9)
    return img


def centrar_texto(d, texto, fuente, cx, cy, color, **kw):
    caja = d.textbbox((0, 0), texto, font=fuente)
    x = cx - (caja[2] - caja[0]) / 2 - caja[0]
    y = cy - (caja[3] - caja[1]) / 2 - caja[1]
    d.text((x, y), texto, font=fuente, fill=color, **kw)
    return x + caja[0], y + caja[1], x + caja[2], y + caja[3]


def circulo(d, cx, cy, r, **kw):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], **kw)


# ---------------------------------------------------------------- propuestas

def p1_monograma():
    """D. — la D de Dato y el punto amarillo: 'un dato' en un vistazo."""
    img = lienzo()
    d = ImageDraw.Draw(img)
    circulo(d, S / 2, S / 2, S * 0.41, outline=AZUL, width=int(S * 0.028))
    x0, y0, x1, y1 = centrar_texto(d, "D", f(NEGRA, S * 0.50), S * 0.47, S * 0.50, BLANCO)
    r = S * 0.058
    circulo(d, x1 + r * 1.35, y1 - r, r, fill=AMARILLO)
    return img


def p2_lupa():
    """Lupa que descubre un dato (punto amarillo): curiosidad e investigación."""
    img = lienzo(brillo=AZUL, fuerza=0.45)
    d = ImageDraw.Draw(img)
    cx, cy, r = S * 0.44, S * 0.43, S * 0.24
    grosor = int(S * 0.055)
    ang = math.radians(45)
    hx0, hy0 = cx + (r + grosor * 0.2) * math.cos(ang), cy + (r + grosor * 0.2) * math.sin(ang)
    hx1, hy1 = cx + r * 2.05 * math.cos(ang), cy + r * 2.05 * math.sin(ang)
    d.line([hx0, hy0, hx1, hy1], fill=BLANCO, width=int(grosor * 1.5))
    circulo(d, hx1, hy1, grosor * 0.75, fill=BLANCO)
    circulo(d, cx, cy, r * 0.93, fill=(25, 45, 100))
    circulo(d, cx, cy, r, outline=BLANCO, width=grosor)
    # Órbita azul y el "dato" amarillo dentro de la lente.
    d.arc([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], 200, 520, fill=AZUL_CLARO, width=int(S * 0.012))
    circulo(d, cx, cy, r * 0.24, fill=AMARILLO)
    circulo(d, cx + r * 0.62 * math.cos(math.radians(200)), cy + r * 0.62 * math.sin(math.radians(200)),
            r * 0.09, fill=AZUL_CLARO)
    return img


def p3_burbuja():
    """Burbuja de diálogo con '?': preguntas, conversación, comentarios."""
    img = lienzo(brillo=VIOLETA, fuerza=0.45)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = S * 0.22, S * 0.24, S * 0.78, S * 0.68
    d.rounded_rectangle([x0, y0, x1, y1], radius=S * 0.12, fill=AZUL)
    d.polygon([(S * 0.33, y1 - 10), (S * 0.30, S * 0.80), (S * 0.47, y1 - 10)], fill=AZUL)
    # Brillo interior.
    d.rounded_rectangle([x0 + S * 0.03, y0 + S * 0.03, x1 - S * 0.03, y0 + S * 0.12], radius=S * 0.05,
                        fill=(79, 145, 248))
    centrar_texto(d, "?", f(NEGRA, S * 0.36), S * 0.50, S * 0.465, BLANCO)
    circulo(d, S * 0.74, S * 0.26, S * 0.07, fill=AMARILLO, outline=FONDO, width=int(S * 0.015))
    return img


def p4_red_neuronal():
    """Una D formada por nodos conectados: mente + tecnología."""
    img = lienzo(brillo=CIAN, fuerza=0.35)
    d = ImageDraw.Draw(img)
    R = S * 0.27
    cx, cy = S * 0.5 - 0.125 * R, S * 0.5
    izq = [(cx - R * 0.45, cy + R * k) for k in (-1, -0.33, 0.33, 1)]
    arco = [(cx - R * 0.45 + R * 1.15 * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a)))
            for a in (-90, -45, 0, 45, 90)]
    centro = (cx + R * 0.15, cy)
    lineas = list(zip(izq, izq[1:])) + list(zip(arco, arco[1:])) + [(izq[0], arco[0]), (izq[-1], arco[-1])]
    lineas += [(centro, p) for p in (izq[1], izq[2], arco[1], arco[2], arco[3])]
    for a, b in lineas:
        d.line([a, b], fill=(120, 170, 255), width=int(S * 0.016))
    for p in izq + arco:
        circulo(d, *p, S * 0.045, fill=BLANCO)
    circulo(d, *centro, S * 0.07, fill=AMARILLO)
    return img


def p5_bombilla():
    """Bombilla: la idea, el '¡ajá!' de aprender algo nuevo."""
    img = lienzo(brillo=AMARILLO, fuerza=0.35)
    d = ImageDraw.Draw(img)
    cx, cy, r = S * 0.5, S * 0.40, S * 0.24
    g = int(S * 0.04)
    circulo(d, cx, cy, r, fill=(30, 50, 105), outline=BLANCO, width=g)
    cuello_y = cy + r * 0.88
    d.polygon([(cx - r * 0.55, cuello_y - g), (cx + r * 0.55, cuello_y - g), (cx + r * 0.40, cy + r * 1.42),
               (cx - r * 0.40, cy + r * 1.42)], fill=(30, 50, 105))
    d.line([(cx - r * 0.55, cuello_y - g * 0.5), (cx - r * 0.40, cy + r * 1.42)], fill=BLANCO, width=g)
    d.line([(cx + r * 0.55, cuello_y - g * 0.5), (cx + r * 0.40, cy + r * 1.42)], fill=BLANCO, width=g)
    for k in range(3):
        y = cy + r * 1.55 + k * g * 1.45
        ancho = r * (0.42 - k * 0.07)
        d.rounded_rectangle([cx - ancho, y, cx + ancho, y + g], radius=g / 2, fill=AZUL_CLARO)
    # Filamento en forma de D con el punto amarillo.
    x0, y0, x1, y1 = centrar_texto(d, "D", f(NEGRA, S * 0.26), cx - S * 0.02, cy + S * 0.01, AMARILLO)
    circulo(d, x1 + S * 0.035, y1 - S * 0.03, S * 0.03, fill=BLANCO)
    return img


def p6_dm():
    """Monograma DM en caja degradada azul→violeta: moderno, tipo app."""
    img = lienzo(c1=FONDO, c2=FONDO, brillo=None)
    peq = Image.new("RGB", (64, 64))
    for y in range(64):
        for x in range(64):
            t = (x + y) / 126
            peq.putpixel((x, y), tuple(int(a + (b - a) * t) for a, b in zip(AZUL, VIOLETA)))
    caja = peq.resize((S, S), Image.BICUBIC)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle([S * 0.15, S * 0.15, S * 0.85, S * 0.85], radius=S * 0.17, fill=255)
    img.paste(caja, (0, 0), m)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = centrar_texto(d, "DM", f(NEGRA, S * 0.30), S * 0.48, S * 0.50, BLANCO)
    circulo(d, x1 + S * 0.05, y1 - S * 0.035, S * 0.035, fill=AMARILLO)
    return img


PROPUESTAS = [
    ("1-monograma", "Monograma D.", p1_monograma),
    ("2-lupa", "Lupa del dato", p2_lupa),
    ("3-burbuja", "Burbuja de pregunta", p3_burbuja),
    ("4-red-neuronal", "Red neuronal", p4_red_neuronal),
    ("5-bombilla", "Bombilla de idea", p5_bombilla),
    ("6-dm", "DM tipo app", p6_dm),
]


def horizontal(icono):
    W, H = 2000, 600
    img = Image.new("RGB", (W, H), FONDO)
    m = Image.new("L", (440, 440), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 440, 440], fill=255)
    img.paste(icono.resize((440, 440), Image.LANCZOS), (80, 80), m)
    d = ImageDraw.Draw(img)
    d.text((590, 95), "DATO", font=f(NEGRA, 190), fill=BLANCO)
    d.text((590, 280), "MENTAL", font=f(NEGRA, 190), fill=AZUL)
    ancho = d.textlength("MENTAL", font=f(NEGRA, 190))
    circulo(d, 590 + ancho + 40, 280 + 170, 26, fill=AMARILLO)
    return img


def comparativa(iconos):
    cw, ch = 760, 900
    W, H = cw * 3 + 80, ch * 2 + 200
    img = Image.new("RGB", (W, H), (240, 242, 247))
    d = ImageDraw.Draw(img)
    d.text((40, 40), "Dato Mental · propuestas de logo", font=f(EXTRA, 64), fill=FONDO)
    d.text((40, 120), "Grande, en círculo (perfil) y en tamaño real de comentario", font=f(SEMI, 34), fill=(90, 100, 120))
    for k, ((clave, nombre, _), ic) in enumerate(zip(PROPUESTAS, iconos)):
        x, y = 40 + (k % 3) * cw, 190 + (k // 3) * ch
        d.rounded_rectangle([x, y, x + cw - 30, y + ch - 30], radius=36, fill=BLANCO)
        img.paste(ic.resize((520, 520), Image.LANCZOS), (x + 105, y + 40))
        for tam, dx in ((150, 110), (64, 300), (32, 400)):
            m = Image.new("L", (tam, tam), 0)
            ImageDraw.Draw(m).ellipse([0, 0, tam, tam], fill=255)
            img.paste(ic.resize((tam, tam), Image.LANCZOS), (x + dx, y + 600 + (150 - tam) // 2), m)
        d.text((x + 40, y + ch - 120), f"{k + 1}. {nombre}", font=f(EXTRA, 46), fill=FONDO)
    return img


def main():
    iconos = []
    for clave, _, fn in PROPUESTAS:
        ic = fn().resize((1024, 1024), Image.LANCZOS)
        ic.save(AQUI / f"{clave}-icono.png")
        horizontal(ic).save(AQUI / f"{clave}-horizontal.png")
        iconos.append(ic)
    comparativa(iconos).save(AQUI / "comparativa.png")
    print("Logos generados en", AQUI)


if __name__ == "__main__":
    main()
