"""Edita un video vertical completo: audio → tiempos → plan → render.

Uso:
  python editar.py --audio dia1.m4a --guion tecnologia-ia/guiones/semana-1.md --dia 1
                   [--clips grabaciones/dia1] [--broll broll/] [--musica musica.mp3]
                   [--marca atajo-ia] [--salida videos/] [--corta] [--ambas] [--solo-plan] [--borrador]

--corta   quita los bloques ✂️ del guion (versión para Shorts/Reels)
--ambas   genera la versión completa (TikTok, +1 min) y la corta
--solo-plan  se detiene tras crear plan.json para revisarlo; luego: python render.py plan.json
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import armar_plan  # noqa: E402
import guion as guion_mod  # noqa: E402
import preparar_audio  # noqa: E402
import render  # noqa: E402
import transcribir  # noqa: E402
from comun import duracion, error, escribir_json, slug  # noqa: E402


def tiempos(voz, guion, modelo, estimar):
    gpal = guion["palabras"] if guion else None
    texto = " ".join(p["texto"] for p in gpal) if gpal else ""
    oidas = None if estimar else transcribir.whisper(voz, modelo, texto)
    if oidas:
        pal = transcribir.alinear_con_guion(gpal, oidas) if gpal else None
        if pal:
            return {"fuente": "whisper+guion", "duracion": duracion(voz), "palabras": pal}
        return {"fuente": "whisper", "duracion": duracion(voz),
                "palabras": [dict(o, negrita=False, recortable=False, cta=False, item=None, marcadores=[])
                             for o in oidas]}
    if not gpal:
        error("Sin Whisper hace falta el guion para calcular los tiempos (pip install faster-whisper).")
    return {"fuente": "estimado", "duracion": duracion(voz), "palabras": transcribir.estimar(voz, gpal)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--guion", help="Guion .md (con --dia/--titulo) o .txt")
    ap.add_argument("--dia", type=int)
    ap.add_argument("--titulo")
    ap.add_argument("--clips")
    ap.add_argument("--broll")
    ap.add_argument("--musica")
    ap.add_argument("--marca", default="atajo-ia")
    ap.add_argument("--salida", default="videos")
    ap.add_argument("--nombre", help="Nombre de la carpeta de salida")
    ap.add_argument("--corta", action="store_true")
    ap.add_argument("--ambas", action="store_true")
    ap.add_argument("--pausa-max", type=float, default=0.35)
    ap.add_argument("--modelo", default="small")
    ap.add_argument("--estimar", action="store_true")
    ap.add_argument("--solo-plan", action="store_true")
    ap.add_argument("--borrador", action="store_true")
    a = ap.parse_args()

    g = guion_mod.leer(a.guion, a.dia, a.titulo) if a.guion else {}
    nombre = a.nombre or slug((f"dia-{a.dia}-" if a.dia else "") + (g.get("titulo") or Path(a.audio).stem))
    carpeta = Path(a.salida) / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    if g:
        escribir_json(carpeta / "guion.json", g)

    voz = carpeta / "voz.wav"
    preparar_audio.preparar(a.audio, voz, a.pausa_max)
    datos = tiempos(voz, g, a.modelo, a.estimar)
    escribir_json(carpeta / "palabras.json", datos)
    print(f"Tiempos de palabras: {datos['fuente']}")

    versiones = [("completa", False), ("corta", True)] if a.ambas else [("corta" if a.corta else "completa", a.corta)]
    for etiqueta, corta in versiones:
        sub = carpeta / etiqueta if a.ambas else carpeta
        plan = armar_plan.armar(datos, g, voz, a.clips, a.broll, a.musica, a.marca, corta)
        escribir_json(sub / "plan.json", plan)
        print(f"[{etiqueta}] plan: {len(plan['escenas'])} escenas, {plan['duracion']:.1f}s")
        if plan["grabaciones_pendientes"]:
            print("  Faltan grabaciones de pantalla para:\n   - " + "\n   - ".join(plan["grabaciones_pendientes"]))
        if not a.solo_plan:
            render.render(sub / "plan.json", sub / "video.mp4", a.borrador)
    print(f"Listo → {carpeta}")


if __name__ == "__main__":
    main()
