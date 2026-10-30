"""Hoja de revisión: extrae N fotogramas del video en una cuadrícula PNG para revisar la edición.

Uso: python revisar.py video.mp4 [-n 12] [-o revision.png]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import duracion, ffmpeg  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("-n", type=int, default=12)
    ap.add_argument("-o", "--salida")
    a = ap.parse_args()
    d = duracion(a.video)
    cols = 4
    filas = -(-a.n // cols)
    salida = a.salida or str(Path(a.video).with_name("revision.png"))
    fps = a.n / d
    ffmpeg(["-i", a.video, "-vf",
            f"fps={fps:.5f},scale=270:480,drawtext=text='%{{pts\\:hms}}':x=8:y=h-30:fontsize=20:"
            f"fontcolor=white:box=1:boxcolor=black@0.6,tile={cols}x{filas}:padding=6:color=gray",
            "-frames:v", "1", salida])
    print(f"Revisión → {salida}")


if __name__ == "__main__":
    main()
