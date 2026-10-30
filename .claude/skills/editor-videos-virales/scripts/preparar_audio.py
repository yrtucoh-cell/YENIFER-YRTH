"""Limpia la narración: quita ruido, recorta pausas largas y normaliza el volumen.

Uso: python preparar_audio.py ENTRADA [-o voz.wav] [--pausa-max 0.35]
Acepta mp3, m4a, wav, ogg/opus (notas de voz de WhatsApp), mp4, etc.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import duracion, ffmpeg, requiere_ffmpeg  # noqa: E402


def preparar(entrada, salida, pausa_max=0.35, sin_ruido=True):
    requiere_ffmpeg()
    filtros = ["highpass=f=80", "lowpass=f=14000"]
    if sin_ruido:
        filtros.append("afftdn=nf=-25")
    filtros += [
        # Quita el silencio inicial y acorta cada pausa interna a pausa_max segundos.
        "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05:"
        f"stop_periods=-1:stop_threshold=-40dB:stop_duration={pausa_max + 0.05}:stop_silence={pausa_max}",
        "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2",
        "loudnorm=I=-16:TP=-1.5:LRA=9",
        "aresample=48000",
    ]
    ffmpeg(["-i", str(entrada), "-vn", "-ac", "1", "-af", ",".join(filtros), "-c:a", "pcm_s16le", str(salida)])
    antes, despues = duracion(entrada), duracion(salida)
    print(f"Audio listo: {antes:.1f}s → {despues:.1f}s (pausas recortadas) → {salida}")
    return despues


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("entrada")
    ap.add_argument("-o", "--salida", default="voz.wav")
    ap.add_argument("--pausa-max", type=float, default=0.35, help="Duración máxima de una pausa (s)")
    ap.add_argument("--sin-limpieza", action="store_true", help="No aplicar reducción de ruido")
    a = ap.parse_args()
    preparar(a.entrada, a.salida, a.pausa_max, not a.sin_limpieza)


if __name__ == "__main__":
    main()
