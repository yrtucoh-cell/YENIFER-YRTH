"""Renderiza el video final a partir de plan.json.

Uso: python render.py plan.json [-o video.mp4] [--borrador]
Genera también: subtitulos.srt, portada.png y publicacion.md junto al video.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (ALTO, ANCHO, EXT_IMAGEN, FPS, RAIZ, buscar_fuente, cargar_marca, dimensiones,  # noqa: E402
                   duracion, error, ffmpeg, hex_ass, leer_json, requiere_ffmpeg, sin_emojis)
import tarjetas  # noqa: E402

SFX_SINTETICOS = {
    "whoosh": "anoisesrc=d=0.45:c=pink:a=0.6,highpass=f=300,lowpass=f=5000,"
              "afade=t=in:d=0.2:curve=exp,afade=t=out:st=0.2:d=0.25,volume=0.35",
    "pop": "aevalsrc='0.7*sin(2*PI*(300+2500*t)*t)*exp(-28*t)':d=0.15:s=48000,volume=0.6",
    "ding": "aevalsrc='0.5*sin(2*PI*1320*t)*exp(-7*t)+0.25*sin(2*PI*1980*t)*exp(-9*t)':d=0.7:s=48000,volume=0.35",
}


def sfx_archivo(tipo, tmp):
    propio = next((p for p in (RAIZ / "sfx").glob(f"{tipo}.*")), None) if (RAIZ / "sfx").exists() else None
    if propio:
        return str(propio)
    dst = Path(tmp) / f"sfx_{tipo}.wav"
    if not dst.exists():
        ffmpeg(["-f", "lavfi", "-i", SFX_SINTETICOS[tipo], "-ac", "1", "-ar", "48000", str(dst)])
    return str(dst)


def filtro_zoom(zoom, dur, foco=(0.5, 0.5), fuerza=0.08):
    fx, fy = foco
    crop = f"crop={ANCHO}:{ALTO}:x='(iw-{ANCHO})*{fx}':y='(ih-{ALTO})*{fy}'"
    if zoom == "in":
        return f"scale=w='trunc({ANCHO}*(1+{fuerza}*t/{dur:.3f})/2)*2':h=-2:eval=frame,{crop}"
    if zoom == "out":
        return f"scale=w='trunc({ANCHO}*(1+{fuerza}*(1-t/{dur:.3f}))/2)*2':h=-2:eval=frame,{crop}"
    if zoom == "punch":
        return f"scale=w={int(ANCHO * 1.12) // 2 * 2}:h=-2,{crop}"
    return "null"


def escena(e, k, tmp, marca, fuente_t, borrador):
    n = max(1, round(e["fin"] * FPS) - round(e["ini"] * FPS))
    dur = n / FPS
    salida = Path(tmp) / f"esc_{k:03d}.mp4"
    cod = ["-an", "-frames:v", str(n), "-r", str(FPS), "-c:v", "libx264", "-preset",
           "ultrafast" if borrador else "veryfast", "-crf", "26" if borrador else "18",
           "-pix_fmt", "yuv420p", "-video_track_timescale", "15360", str(salida)]
    foco = tuple(e.get("foco", (0.5, 0.5)))
    tipo = e["tipo"]
    src = e.get("src")
    if tipo == "clip" and src and Path(src).suffix.lower() in EXT_IMAGEN:
        tipo = "imagen"
    if tipo == "clip":
        if not Path(src).exists():
            error(f"No existe el clip {src}")
        w, h = dimensiones(src)
        z = filtro_zoom(e.get("zoom", "none"), dur, foco, 0.05)
        cubrir = f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},setsar=1"
        if w / h > 0.75:  # horizontal (p. ej. pantalla de PC): centrado sobre fondo desenfocado
            fc = (f"[0:v]fps={FPS},split[a][b];[a]{cubrir},gblur=sigma=40,eq=brightness=-0.18[bg];"
                  f"[b]scale={ANCHO - 40}:-2,setsar=1[fg];[bg][fg]overlay=(W-w)/2:H*0.40-h/2,{z}[v]")
        else:
            fc = f"[0:v]fps={FPS},{cubrir},{z}[v]"
        ffmpeg(["-ss", f"{e.get('desde', 0):.3f}", "-stream_loop", "-1", "-i", src,
                "-filter_complex", fc, "-map", "[v]"] + cod)
        return salida
    png = Path(tmp) / f"esc_{k:03d}.png"
    if tipo == "imagen":
        w, h = dimensiones(src)
        tarjetas.fondo(marca, k).save(png)
        fc = (f"[1:v]scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},setsar=1,"
              f"{filtro_zoom(e.get('zoom', 'in'), dur, foco)}[v]")
        ffmpeg(["-loop", "1", "-framerate", str(FPS), "-i", str(png), "-loop", "1", "-framerate", str(FPS),
                "-i", src, "-filter_complex", fc, "-map", "[v]"] + cod)
        return salida
    if tipo == "fondo":
        img = tarjetas.fondo_palabra(marca, fuente_t, e.get("texto"), int(e.get("variante", 0)))
    elif tipo == "cta":
        img = tarjetas.tarjeta(marca, fuente_t, "cta", e.get("texto", "SÍGUEME"), fondo_var=2)
    else:
        img = tarjetas.tarjeta(marca, fuente_t, e.get("variante", "concepto"), e.get("texto", ""),
                               e.get("numero"), fondo_var=k)
    img.save(png)
    ffmpeg(["-loop", "1", "-framerate", str(FPS), "-i", str(png), "-vf",
            f"{filtro_zoom(e.get('zoom', 'in'), dur, foco)},setsar=1"] + cod)
    return salida


def t_ass(s):
    s = max(0, s)
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def limpio(t):
    return t.replace("{", "(").replace("}", ")").replace("\\", "/")


def escribir_ass(plan, marca, familia_sub, familia_tit, ruta):
    col = marca["colores"]
    sub = marca.get("subtitulos", {})
    tam = sub.get("tamano", 88)
    y = int(ALTO * sub.get("altura", 0.66))
    blanco, negro = hex_ass(col["texto"]), "&H00000000"
    actual = hex_ass(col.get("resalte", col["acento"]))
    resalte = hex_ass(col.get("palabra_clave", col["acento"]))
    mayus = sub.get("mayusculas", True)
    lineas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {ANCHO}", f"PlayResY: {ALTO}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Sub,{familia_sub},{tam},{blanco},{blanco},{negro},&H80000000,-1,0,0,0,100,100,1,0,1,7,4,5,110,110,0,1",
        f"Style: Gancho,{familia_tit},84,&H00101010,&H00101010,&H00FFFFFF,&H64000000,-1,0,0,0,100,100,0,0,3,22,0,8,90,90,250,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    g = plan.get("gancho") or {}
    if g.get("mostrar") and g.get("texto"):
        txt = limpio(sin_emojis(g["texto"]))
        lineas.append(f"Dialogue: 2,{t_ass(g['ini'])},{t_ass(g['fin'])},Gancho,,0,0,0,,"
                      f"{{\\fad(0,150)\\fscx70\\fscy70\\t(0,140,\\fscx100\\fscy100)}}{txt}")
    for b in plan["subtitulos"]:
        pals = b["palabras"]
        textos = [limpio(p["texto"].upper() if mayus else p["texto"]) for p in pals]
        for i, p in enumerate(pals):
            ini = b["ini"] if i == 0 else p["ini"]
            fin = pals[i + 1]["ini"] if i + 1 < len(pals) else b["fin"]
            if fin - ini < 0.02:
                continue
            partes = []
            for j, (q, tx) in enumerate(zip(pals, textos)):
                if j == i:
                    partes.append(f"{{\\c{actual}\\fscx112\\fscy112}}{tx}{{\\c{blanco}\\fscx100\\fscy100}}")
                elif q.get("resaltar"):
                    partes.append(f"{{\\c{resalte}}}{tx}{{\\c{blanco}}}")
                else:
                    partes.append(tx)
            pop = "{\\fscx85\\fscy85\\t(0,90,\\fscx100\\fscy100)}" if i == 0 else ""
            lineas.append(f"Dialogue: 1,{t_ass(ini)},{t_ass(fin)},Sub,,0,0,0,,{{\\pos(540,{y})}}{pop}" + " ".join(partes))
    Path(ruta).write_text("\n".join(lineas) + "\n", encoding="utf-8")


def escribir_srt(plan, ruta):
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    out = []
    for k, b in enumerate(plan["subtitulos"], 1):
        out += [str(k), f"{ts(b['ini'])} --> {ts(b['fin'])}", " ".join(p["texto"] for p in b["palabras"]), ""]
    Path(ruta).write_text("\n".join(out), encoding="utf-8")


def escribir_publicacion(plan, marca, ruta):
    tags = " ".join(plan.get("hashtags") or marca.get("hashtags_base", []))
    gancho = plan.get("texto_pantalla_original") or plan.get("texto_pantalla") or plan.get("titulo")
    titulo = plan.get("titulo", "")
    txt = f"""# Publicación · {titulo}

## TikTok
{gancho}
¿Lo sabías? Cuéntame en comentarios 👇
{tags}

## Instagram Reels
{gancho}
📌 Guárdalo para tenerlo a mano y compártelo con alguien que lo necesite.
{tags}

## YouTube Shorts
Título: {sin_emojis(titulo)[:90]} #shorts
Descripción: {sin_emojis(gancho)}. Más trucos en {marca.get('usuario', 'el canal')}.
{tags} #shorts

## Lista antes de publicar
- [ ] Ver el video completo con sonido y sin sonido
- [ ] Revisar que los subtítulos no tengan errores
- [ ] En TikTok: añadir un sonido en tendencia a volumen 1–5 %
- [ ] Portada: subir portada.png
- [ ] Publicar en la franja horaria del plan
"""
    Path(ruta).write_text(txt, encoding="utf-8")


def lufs(ruta):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(ruta), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])["input_i"])


def mezclar_audio(plan, tmp):
    """Voz + efectos + música (con ducking) → mezcla.wav normalizada a -14 LUFS en dos pasadas."""
    dur = plan["duracion"]
    entradas = ["-i", plan["voz"]]
    filtros, idx = [], 1
    tramos = plan.get("audio_tramos")
    if tramos:
        partes = []
        for k, (a, b) in enumerate(tramos):
            fin = f":end={b}" if b is not None else ""
            filtros.append(f"[0:a]atrim=start={a}{fin},asetpts=PTS-STARTPTS[t{k}]")
            partes.append(f"[t{k}]")
        filtros.append(f"{''.join(partes)}concat=n={len(partes)}:v=0:a=1[vozc]")
        voz = "[vozc]"
    else:
        voz = "[0:a]"
    filtros.append(f"{voz}aresample=48000,apad,atrim=0:{dur},asplit=2[voz][vozsc]")
    mezcla = ["[voz]"]
    for k, s in enumerate(plan.get("sfx", [])):
        entradas += ["-i", sfx_archivo(s["tipo"], tmp)]
        ms = int(s["t"] * 1000)
        vol = s.get("volumen", 1.0)
        filtros.append(f"[{idx}:a]aresample=48000,volume={vol},adelay={ms}:all=1[s{k}]")
        mezcla.append(f"[s{k}]")
        idx += 1
    m = plan.get("musica")
    if m and m.get("src"):
        entradas += ["-stream_loop", "-1", "-i", m["src"]]
        filtros.append(f"[{idx}:a]aresample=48000,atrim=0:{dur},volume={m.get('volumen', 0.12)},"
                       f"afade=t=out:st={max(0, dur - 1.5)}:d=1.5[mus]")
        filtros.append("[mus][vozsc]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=350[musd]")
        mezcla.append("[musd]")
    else:
        filtros.append("[vozsc]anullsink")
    filtros.append(f"{''.join(mezcla)}amix=inputs={len(mezcla)}:normalize=0:duration=first[a]")
    bruto = Path(tmp) / "mezcla_bruta.wav"
    ffmpeg(entradas + ["-filter_complex", ";".join(filtros), "-map", "[a]", "-t", f"{dur}",
                       "-ar", "48000", "-c:a", "pcm_s16le", str(bruto)])
    # Ganancia hasta -14 LUFS + limitador (picos ≤ -1,5 dBTP). Dos pasadas: el limitador baja un
    # poco el volumen medio y la segunda pasada lo compensa.
    entrada, ganancia_total = bruto, 0.0
    for paso in range(3):
        faltan = -14.0 - lufs(entrada)
        if abs(faltan) < 0.3:
            break
        ganancia_total += faltan
        final = Path(tmp) / f"mezcla_{paso}.wav"
        ffmpeg(["-i", str(bruto), "-af", f"volume={ganancia_total:.2f}dB,"
                "alimiter=limit=0.84:level=false:attack=3:release=60,aresample=48000",
                "-ar", "48000", "-c:a", "pcm_s16le", str(final)])
        entrada = final
    final = entrada
    return final


def mezclar(plan, video, salida, tmp, borrador, fontsdir):
    dur = plan["duracion"]
    audio = mezclar_audio(plan, tmp)
    ass = str(Path(tmp) / "subs.ass").replace(":", "\\:").replace("'", "\\'")
    vf = f"ass='{ass}':fontsdir='{fontsdir}'"
    if plan.get("barra_progreso", True):
        marca = cargar_marca(plan["marca"])
        color = "0x" + marca["colores"]["acento"].lstrip("#")
        vf += f",drawbox=x=0:y=0:w='iw*t/{dur}':h=12:color={color}@0.95:t=fill"
    ffmpeg(["-i", str(video), "-i", str(audio), "-vf", vf, "-map", "0:v", "-map", "1:a",
            "-t", f"{dur}", "-r", str(FPS), "-c:v", "libx264", "-preset",
            "ultrafast" if borrador else "medium", "-crf", "28" if borrador else "20",
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-movflags", "+faststart", str(salida)])


def render(plan_path, salida=None, borrador=False):
    requiere_ffmpeg()
    plan = leer_json(plan_path)
    marca = cargar_marca(plan["marca"])
    fuentes = marca.get("fuentes", {})
    ruta_sub, fam_sub = buscar_fuente(fuentes.get("subtitulos", ["Montserrat:style=ExtraBold"]))
    ruta_tit, fam_tit = buscar_fuente(fuentes.get("titulos", ["Montserrat:style=Black"]))
    salida = Path(salida or Path(plan_path).with_name("video.mp4"))
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="editor_")
    try:
        # Las fuentes elegidas se copian a la carpeta temporal para que libass las encuentre.
        for r in {ruta_sub, ruta_tit}:
            shutil.copy(r, tmp)
        escenas = plan["escenas"]
        print(f"Renderizando {len(escenas)} escenas…")
        partes = [escena(e, k, tmp, marca, ruta_tit, borrador) for k, e in enumerate(escenas)]
        lista = Path(tmp) / "lista.txt"
        lista.write_text("".join(f"file '{p}'\n" for p in partes))
        video = Path(tmp) / "video_sin_audio.mp4"
        ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(video)])
        escribir_ass(plan, marca, fam_sub, fam_tit, Path(tmp) / "subs.ass")
        mezclar(plan, video, salida, tmp, borrador, fontsdir=tmp)
        escribir_srt(plan, salida.with_name("subtitulos.srt"))
        tarjetas.portada(marca, ruta_tit, plan.get("texto_pantalla") or plan.get("titulo", "")).save(
            salida.with_name("portada.png"))
        escribir_publicacion(plan, marca, salida.with_name("publicacion.md"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"Video listo: {salida} ({duracion(salida):.1f}s)")
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("-o", "--salida")
    ap.add_argument("--borrador", action="store_true", help="Render rápido de baja calidad para revisar")
    a = ap.parse_args()
    render(a.plan, a.salida, a.borrador)


if __name__ == "__main__":
    main()
