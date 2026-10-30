"""Dibuja los fondos y tarjetas de texto (PNG 1080x1920) con la identidad de la marca."""

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from comun import ALTO, ANCHO, hex_rgb, sin_emojis


def _mezcla(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def fondo(marca, variante=0):
    col = marca["colores"]
    c1, c2 = hex_rgb(col["fondo"]), hex_rgb(col["fondo2"])
    acento = hex_rgb(col["acento"])
    img = Image.new("RGB", (ANCHO, ALTO), c1)
    d = ImageDraw.Draw(img)
    for y in range(ALTO):
        d.line([(0, y), (ANCHO, y)], fill=_mezcla(c1, c2, y / ALTO))
    # Brillo difuso del color de acento (cambia de posición en cada variante).
    brillo = Image.new("RGB", (ANCHO, ALTO), (0, 0, 0))
    bd = ImageDraw.Draw(brillo)
    cx, cy = [(ANCHO * 0.8, ALTO * 0.2), (ANCHO * 0.2, ALTO * 0.35), (ANCHO * 0.5, ALTO * 0.75)][variante % 3]
    r = 650
    bd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(int(c * 0.45) for c in acento))
    brillo = brillo.filter(ImageFilter.GaussianBlur(220))
    img = Image.blend(img, Image.composite(brillo, img, brillo.convert("L")), 0.9)
    # Patrón de puntos (estética tecnológica).
    d = ImageDraw.Draw(img)
    punto = _mezcla(c2, (255, 255, 255), 0.12)
    for y in range(40, ALTO, 60):
        for x in range(40, ANCHO, 60):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=punto)
    return img


def _fuente(ruta, tam):
    return ImageFont.truetype(ruta, tam)


def _envolver(d, texto, ruta, tam_max, ancho_max, lineas_max=4, tam_min=54):
    tam = tam_max
    while tam >= tam_min:
        f = _fuente(ruta, tam)
        palabras, lineas, actual = texto.split(), [], ""
        for w in palabras:
            prueba = (actual + " " + w).strip()
            if d.textlength(prueba, font=f) <= ancho_max:
                actual = prueba
            else:
                if actual:
                    lineas.append(actual)
                actual = w
        if actual:
            lineas.append(actual)
        if len(lineas) <= lineas_max and all(d.textlength(l, font=f) <= ancho_max for l in lineas):
            return f, lineas, tam
        tam -= 6
    return _fuente(ruta, tam_min), lineas, tam_min


def _texto_centrado(d, lineas, f, tam, y_centro, color, sombra=(0, 0, 0)):
    alto_linea = int(tam * 1.15)
    y = y_centro - alto_linea * len(lineas) / 2
    for l in lineas:
        w = d.textlength(l, font=f)
        x = (ANCHO - w) / 2
        d.text((x + 5, y + 6), l, font=f, fill=sombra)
        d.text((x, y), l, font=f, fill=color, stroke_width=3, stroke_fill=sombra)
        y += alto_linea
    return y


def tarjeta(marca, fuente_titulos, variante, texto, numero=None, fondo_var=0):
    img = fondo(marca, fondo_var)
    d = ImageDraw.Draw(img)
    col = marca["colores"]
    blanco, acento, resalte = hex_rgb(col["texto"]), hex_rgb(col["acento"]), hex_rgb(col.get("resalte", col["acento"]))
    texto = sin_emojis(texto or "")
    if marca.get("titulos_mayusculas", True):
        texto = texto.upper()
    y_centro = int(ALTO * 0.36)
    if variante == "gancho":
        f, lineas, tam = _envolver(d, texto, fuente_titulos, 132, 860, 5)
        fin = _texto_centrado(d, lineas, f, tam, y_centro, blanco)
        d.rounded_rectangle([ANCHO / 2 - 160, fin + 30, ANCHO / 2 + 160, fin + 46], 8, fill=acento)
    elif variante == "lista":
        if numero:
            r = 120
            cy = y_centro - 210
            d.ellipse([ANCHO / 2 - r, cy - r, ANCHO / 2 + r, cy + r], fill=acento)
            fn = _fuente(fuente_titulos, 150)
            w = d.textlength(str(numero), font=fn)
            d.text((ANCHO / 2 - w / 2, cy - 95), str(numero), font=fn, fill=(255, 255, 255))
        f, lineas, tam = _envolver(d, texto, fuente_titulos, 112, 860, 3)
        _texto_centrado(d, lineas, f, tam, y_centro + (60 if numero else 0), blanco)
    elif variante == "cta":
        handle = marca.get("usuario", "")
        f, lineas, tam = _envolver(d, texto, fuente_titulos, 150, 760, 2)
        bw = max(d.textlength(l, font=f) for l in lineas) + 120
        bh = int(tam * 1.15) * len(lineas) + 70
        d.rounded_rectangle([(ANCHO - bw) / 2, y_centro - bh / 2, (ANCHO + bw) / 2, y_centro + bh / 2], 50, fill=acento)
        _texto_centrado(d, lineas, f, tam, y_centro, (255, 255, 255), sombra=_mezcla(acento, (0, 0, 0), 0.5))
        if handle:
            fh = _fuente(fuente_titulos, 76)
            w = d.textlength(handle, font=fh)
            d.text(((ANCHO - w) / 2, y_centro + bh / 2 + 50), handle, font=fh, fill=resalte, stroke_width=3, stroke_fill=(0, 0, 0))
    else:  # concepto
        f, lineas, tam = _envolver(d, texto, fuente_titulos, 118, 760, 3)
        alto = int(tam * 1.15) * len(lineas) + 110
        ancho = max(d.textlength(l, font=f) for l in lineas) + 140
        caja = [(ANCHO - ancho) / 2, y_centro - alto / 2, (ANCHO + ancho) / 2, y_centro + alto / 2]
        d.rounded_rectangle(caja, 44, fill=_mezcla(hex_rgb(col["fondo"]), (0, 0, 0), 0.3), outline=acento, width=10)
        _texto_centrado(d, lineas, f, tam, y_centro, resalte)
    return img


def fondo_palabra(marca, fuente_titulos, palabra, variante=0):
    """Fondo con una palabra clave enorme (tipografía cinética) sobre la zona de subtítulos."""
    img = fondo(marca, variante)
    if not palabra:
        return img
    d = ImageDraw.Draw(img)
    col = marca["colores"]
    palabra = sin_emojis(palabra).upper()
    f, lineas, tam = _envolver(d, palabra, fuente_titulos, 180, 840, 2, 70)
    color = [hex_rgb(col["texto"]), hex_rgb(col.get("resalte", col["acento"])), hex_rgb(col["acento"])][variante % 3]
    _texto_centrado(d, lineas, f, tam, int(ALTO * 0.38), color)
    return img


def portada(marca, fuente_titulos, texto):
    """Miniatura/portada 1080x1920 para Reels, TikTok y Shorts."""
    img = tarjeta(marca, fuente_titulos, "gancho", texto, fondo_var=1)
    d = ImageDraw.Draw(img)
    handle = marca.get("usuario", "")
    if handle:
        fh = _fuente(fuente_titulos, 60)
        w = d.textlength(handle, font=fh)
        d.text(((ANCHO - w) / 2, ALTO * 0.62), handle, font=fh, fill=hex_rgb(marca["colores"]["acento"]))
    return img
