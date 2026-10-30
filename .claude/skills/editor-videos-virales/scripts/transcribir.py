"""Obtiene el tiempo de cada palabra de la narración.

Modo 1 (preciso): faster-whisper con marcas de tiempo por palabra. Si hay guion, se alinean las
palabras del guion con lo que dijo Whisper, para conservar ortografía, negritas, cortes ✂️ y
marcas [PANTALLA].
Modo 2 (estimado, sin internet ni Whisper): detecta los tramos con voz y reparte las palabras del
guion según sus sílabas. Requiere guion.

Uso: python transcribir.py voz.wav [--guion guion.json] [-o palabras.json] [--modelo small] [--estimar]
"""
import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import duracion, error, escribir_json, leer_json, normalizar  # noqa: E402


def whisper(audio, modelo, texto_guion):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    try:
        m = WhisperModel(modelo, device="auto", compute_type="int8")
    except Exception as e:  # sin red para descargar el modelo, etc.
        print(f"Aviso: no se pudo cargar Whisper ({type(e).__name__}). Uso el modo estimado.")
        return None
    segs, _ = m.transcribe(str(audio), language="es", word_timestamps=True, vad_filter=True,
                           initial_prompt=(texto_guion or "")[:800] or None)
    out = []
    for s in segs:
        for w in s.words or []:
            t = w.word.strip()
            if t:
                out.append({"texto": t, "ini": round(w.start, 3), "fin": round(w.end, 3)})
    return out


def alinear_con_guion(guion_pal, oidas):
    """Copia los tiempos de Whisper sobre las palabras del guion (difflib + interpolación)."""
    a = [normalizar(p["texto"]) for p in guion_pal]
    b = [normalizar(p["texto"]) for p in oidas]
    tiempos = [None] * len(a)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            o = oidas[blk.b + k]
            tiempos[blk.a + k] = (o["ini"], o["fin"])
    cubiertas = sum(t is not None for t in tiempos)
    if cubiertas < 0.5 * len(a):
        print(f"Aviso: el audio coincide poco con el guion ({cubiertas}/{len(a)} palabras). "
              "Uso el texto que dijo Whisper.")
        return None
    # Interpolar los huecos (palabras dichas distinto o no reconocidas).
    i = 0
    fin_audio = oidas[-1]["fin"]
    while i < len(a):
        if tiempos[i] is not None:
            i += 1
            continue
        j = i
        while j < len(a) and tiempos[j] is None:
            j += 1
        t0 = tiempos[i - 1][1] if i > 0 else 0.0
        t1 = tiempos[j][0] if j < len(a) else fin_audio
        paso = max(t1 - t0, 0.05) / (j - i)
        for k in range(i, j):
            tiempos[k] = (t0 + paso * (k - i), t0 + paso * (k - i + 1))
        i = j
    res = []
    for p, (ini, fin) in zip(guion_pal, tiempos):
        q = dict(p)
        q["ini"], q["fin"] = round(ini, 3), round(fin, 3)
        res.append(q)
    return res


def tramos_de_voz(audio, umbral="-35dB", min_silencio=0.12):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(audio), "-af",
                        f"silencedetect=noise={umbral}:d={min_silencio}", "-f", "null", "-"],
                       capture_output=True, text=True)
    total = duracion(audio)
    ini_s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    fin_s = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    tramos, cursor = [], 0.0
    for s, e in zip(ini_s, fin_s + [total] * (len(ini_s) - len(fin_s))):
        if s - cursor > 0.05:
            tramos.append((cursor, s))
        cursor = e
    if total - cursor > 0.05:
        tramos.append((cursor, total))
    return tramos or [(0.0, total)]


def silabas(palabra):
    p = normalizar(palabra)
    digitos = sum(c.isdigit() for c in p)
    voc = len(re.findall(r"[aeiouáéíóúü]+", p))
    extra = 2 if "%" in palabra or "$" in palabra else 0
    return max(1, voc + int(digitos * 1.6) + extra)


def estimar(audio, guion_pal):
    tramos = tramos_de_voz(audio)
    total_voz = sum(e - s for s, e in tramos)
    pesos = [silabas(p["texto"]) for p in guion_pal]
    suma = float(sum(pesos))

    def a_real(tv):  # tiempo dentro de la voz concatenada → tiempo real
        for s, e in tramos:
            if tv <= e - s:
                return s + tv
            tv -= e - s
        return tramos[-1][1]

    res, acum = [], 0.0
    for p, w in zip(guion_pal, pesos):
        t0 = acum / suma * total_voz
        acum += w
        t1 = acum / suma * total_voz
        q = dict(p)
        q["ini"], q["fin"] = round(a_real(t0 + 0.001), 3), round(a_real(t1 - 0.001), 3)
        res.append(q)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--guion", help="guion.json generado por guion.py")
    ap.add_argument("-o", "--salida", default="palabras.json")
    ap.add_argument("--modelo", default="small", help="Modelo Whisper: tiny, base, small, medium, large-v3")
    ap.add_argument("--estimar", action="store_true", help="Forzar el modo estimado (sin Whisper)")
    a = ap.parse_args()

    guion = leer_json(a.guion) if a.guion else None
    gpal = guion["palabras"] if guion else None
    texto = " ".join(p["texto"] for p in gpal) if gpal else ""

    oidas = None if a.estimar else whisper(a.audio, a.modelo, texto)
    if oidas:
        pal = alinear_con_guion(gpal, oidas) if gpal else None
        fuente = "whisper+guion" if pal else "whisper"
        if not pal:
            pal = [dict(o, negrita=False, recortable=False, cta=False, item=None, marcadores=[]) for o in oidas]
    elif gpal:
        pal, fuente = estimar(a.audio, gpal), "estimado"
    else:
        error("Sin Whisper hace falta el guion (--guion) para calcular los tiempos. "
              "Instala Whisper con: pip install faster-whisper")
    escribir_json(a.salida, {"fuente": fuente, "duracion": duracion(a.audio), "palabras": pal})
    print(f"Tiempos ({fuente}): {len(pal)} palabras → {a.salida}")
    if fuente == "estimado":
        print("Aviso: tiempos aproximados. Para subtítulos exactos instala faster-whisper.")


if __name__ == "__main__":
    main()
