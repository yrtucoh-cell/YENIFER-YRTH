"""Crea el plan de edición (plan.json) a partir de los tiempos de cada palabra.

El plan decide: escenas (grabaciones de pantalla, B-roll, tarjetas de texto), zooms, subtítulos
palabra por palabra, gancho, efectos de sonido y música. Se puede revisar y editar a mano antes
de renderizar.

Uso: python armar_plan.py palabras.json --guion guion.json --voz voz.wav [--clips DIR]
       [--broll DIR] [--musica ARCHIVO] [--marca atajo-ia] [--corta] [-o plan.json]
"""
import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import EXT_IMAGEN, EXT_VIDEO, cargar_marca, escribir_json, leer_json, normalizar  # noqa: E402

FIN_FRASE = re.compile(r"[.?!:;…]$|[.?!]\W*$")
ESCENA_MAX = 4.5
ZOOMS = ["in", "punch", "out", "in", "punch", "none"]
VACIAS = set("""a al algo como con cual cuando de del donde el ella ellos en entre era es esa ese eso esta este esto
estas estos fue hay la las le les lo los mas me mi mis muy nada ni no nos o para pero por porque que se
si sin sobre solo su sus tambien te tiene tienen todo tu tus un una uno unos y ya yo puedes puede hace
hacer cada otra otro mismo misma donde aqui ahi asi bien tan tanto vez veces cualquier cualquiera
alguien algun alguna mucho mucha muchos muchas siempre ahora despues antes luego tambien sigue sigues""".split())


def archivos(d, exts):
    if not d:
        return []
    return sorted(str(p) for p in Path(d).iterdir() if p.suffix.lower() in exts)


def recortar(palabras):
    """Quita los bloques ✂️ y devuelve (palabras_desplazadas, tramos_de_audio_conservados)."""
    cortes, i, n = [], 0, len(palabras)
    while i < n:
        if not palabras[i].get("recortable"):
            i += 1
            continue
        j = i
        while j < n and palabras[j].get("recortable"):
            j += 1
        a = (palabras[i - 1]["fin"] + palabras[i]["ini"]) / 2 if i > 0 else 0.0
        b = (palabras[j - 1]["fin"] + palabras[j]["ini"]) / 2 if j < n else palabras[-1]["fin"] + 0.3
        marcas = [m for p in palabras[i:j] for m in p.get("marcadores", [])]
        if j < n and marcas:
            palabras[j]["marcadores"] = marcas + palabras[j].get("marcadores", [])
        cortes.append((a, b))
        i = j
    if not cortes:
        return palabras, None
    quedan = [p for p in palabras if not p.get("recortable")]
    for p in quedan:
        quitado = sum(min(b, p["ini"]) - a for a, b in cortes if a < p["ini"])
        p["ini"], p["fin"] = round(p["ini"] - quitado, 3), round(p["fin"] - quitado, 3)
    tramos, cursor = [], 0.0
    for a, b in cortes:
        if a > cursor:
            tramos.append([round(cursor, 3), round(a, 3)])
        cursor = b
    tramos.append([round(cursor, 3), None])
    return quedan, tramos


def frases(palabras):
    out, actual = [], []
    for k, p in enumerate(palabras):
        if actual and (p.get("item") or p.get("cta") != actual[-1].get("cta")):
            out.append(actual)
            actual = []
        actual.append(dict(p, idx=k))
        if FIN_FRASE.search(p["texto"]):
            out.append(actual)
            actual = []
    if actual:
        out.append(actual)
    return out


def frase_negrita(fr):
    grupo, grupos = [], []
    for p in fr:
        if p.get("negrita"):
            grupo.append(p["texto"])
        elif grupo:
            grupos.append(grupo)
            grupo = []
    if grupo:
        grupos.append(grupo)
    if not grupos:
        return None
    return re.sub(r"[,;:.]+$", "", " ".join(max(grupos, key=len)))


def palabra_clave(fr):
    """Elige la palabra más importante de la frase para mostrarla en grande."""
    def puntos(p):
        n = normalizar(p["texto"])
        if not n or n in VACIAS:
            return -1
        return len(n) + (8 if p.get("negrita") else 0) + (6 if re.search(r"\d", n) else 0)
    mejor = max(fr, key=puntos)
    return re.sub(r"^[¿¡\"“(]+|[,;:.?!\"”)]+$", "", mejor["texto"]) if puntos(mejor) > 3 else None


def subtitulos(palabras, marca):
    max_pal = marca.get("subtitulos", {}).get("palabras_por_bloque", 3)
    max_car = marca.get("subtitulos", {}).get("caracteres_max", 18)
    claves = {normalizar(x) for x in marca.get("palabras_clave", [])}
    bloques, actual = [], []
    for p in palabras:
        largo = sum(len(x["texto"]) + 1 for x in actual) + len(p["texto"])
        nuevo_item = p.get("item") and actual
        if actual and (len(actual) >= max_pal or largo > max_car or nuevo_item):
            bloques.append(actual)
            actual = []
        actual.append(p)
        if re.search(r"[.?!:,;]$", p["texto"]):
            bloques.append(actual)
            actual = []
    if actual:
        bloques.append(actual)
    res = []
    for k, b in enumerate(bloques):
        ini = b[0]["ini"]
        fin = b[-1]["fin"] + 0.15
        if k + 1 < len(bloques) and bloques[k + 1][0]["ini"] - b[-1]["fin"] < 0.6:
            fin = bloques[k + 1][0]["ini"]
        res.append({
            "ini": round(ini, 3), "fin": round(fin, 3),
            "palabras": [{"texto": re.sub(r'["“”«»]', "", p["texto"]), "ini": p["ini"], "fin": p["fin"],
                          "resaltar": bool(p.get("negrita") or re.search(r"\d", p["texto"])
                                           or normalizar(p["texto"]) in claves)} for p in b],
        })
    return res


def armar(datos, guion, voz, clips_dir=None, broll_dir=None, musica=None, marca_nombre="atajo-ia",
          corta=False):
    marca = cargar_marca(marca_nombre)
    palabras = [dict(p) for p in datos["palabras"]]
    tramos = None
    if corta:
        palabras, tramos = recortar(palabras)
    dur_voz = datos["duracion"]
    if tramos:
        dur_voz = sum(((b if b is not None else datos["duracion"]) - a) for a, b in tramos)
    duracion = round(max(dur_voz, palabras[-1]["fin"]) + 0.6, 3)

    clips = archivos(clips_dir, EXT_VIDEO | EXT_IMAGEN)
    broll = archivos(broll_dir, EXT_VIDEO | EXT_IMAGEN)
    frs = frases(palabras)

    # 1. Asignar grabaciones de pantalla a las frases según las marcas [PANTALLA].
    clip_de, pendientes, n_marca = {}, [], 0
    for s, fr in enumerate(frs):
        for k, p in enumerate(fr):
            descs = list(p.get("marcadores", [])) + list(p.get("marcadores_despues", []))
            for d in descs:
                antes_de_frase = k == 0 and not p.get("marcadores_despues")
                rango = [s - 1, s] if antes_de_frase and s > 0 else [s, s + 1]
                if n_marca < len(clips):
                    for r in rango:
                        if 0 <= r < len(frs):
                            clip_de[r] = (clips[n_marca], d)
                elif clips:
                    for r in rango:
                        if 0 <= r < len(frs):
                            clip_de[r] = (clips[-1], d)
                else:
                    pendientes.append(d)
                n_marca += 1

    # 2. Escenas base: una por frase.
    escenas, n_broll, n_fondo = [], 0, 0
    for s, fr in enumerate(frs):
        ini = 0.0 if s == 0 else round(fr[0]["ini"] - 0.04, 3)
        e = {"ini": ini}
        negr = frase_negrita(fr)
        if s in clip_de:
            e.update(tipo="clip", src=clip_de[s][0], nota=clip_de[s][1])
        elif fr[0].get("cta"):
            e.update(tipo="cta", texto=marca.get("cta_texto", "SÍGUEME"))
        elif s == 0:
            if broll:
                e.update(tipo="clip", src=broll[0])
                n_broll = 1
            else:
                e.update(tipo="tarjeta", variante="gancho", texto=guion.get("texto_pantalla", ""))
        elif fr[0].get("item"):
            num = fr[0]["item"]
            texto = negr or " ".join(p["texto"] for p in fr[:4])
            e.update(tipo="tarjeta", variante="lista", numero=None if num == "•" else num,
                     texto=re.sub(r"[:,.]+$", "", texto))
        elif negr and len(negr) <= 40:
            e.update(tipo="tarjeta", variante="concepto", texto=negr)
        elif n_broll < len(broll) and (s % 2 == 1 or len(broll) >= len(frs) // 2):
            # Cada B-roll se usa una vez; si hay pocos, se alternan con palabras clave.
            e.update(tipo="clip", src=broll[n_broll])
            n_broll += 1
        else:
            e.update(tipo="fondo", variante=n_fondo % 3, texto=palabra_clave(fr))
            n_fondo += 1
        escenas.append(e)

    # Fusionar escenas consecutivas del mismo clip y continuar su reproducción.
    fus = []
    for e in escenas:
        if fus and e["tipo"] == "clip" and fus[-1].get("src") == e.get("src") and fus[-1]["tipo"] == "clip":
            continue
        if fus and e["tipo"] == "cta" and fus[-1]["tipo"] == "cta":
            continue
        fus.append(e)
    for k, e in enumerate(fus):
        e["fin"] = fus[k + 1]["ini"] if k + 1 < len(fus) else duracion

    # 3. Partir escenas largas (cambio de plano cada ~3,5 s mantiene la atención).
    finales, z, avance = [], 0, {}
    for e in fus:
        d = e["fin"] - e["ini"]
        partes = max(1, math.ceil(d / 3.5)) if d > ESCENA_MAX and e["tipo"] != "cta" else 1
        for k in range(partes):
            q = dict(e)
            q["ini"] = round(e["ini"] + d * k / partes, 3)
            q["fin"] = round(e["ini"] + d * (k + 1) / partes, 3)
            if q["tipo"] == "clip":
                q["desde"] = round(avance.get(q["src"], 0.0), 3)
                avance[q["src"]] = q["desde"] + (q["fin"] - q["ini"])
                es_pantalla = "nota" in q
                q["zoom"] = "in" if es_pantalla and k % 2 == 0 else ("none" if es_pantalla else ZOOMS[z % 6])
            elif q["tipo"] == "cta":
                q["zoom"] = "in"
            else:
                q["zoom"] = ZOOMS[z % 6]
            z += 1
            finales.append(q)

    # 4. Efectos de sonido en cada corte.
    sfx, ultimo = [{"t": 0.0, "tipo": "pop"}], -9.0
    for e in finales[1:]:
        if e["ini"] - ultimo >= 1.2:
            sfx.append({"t": round(max(0, e["ini"] - 0.12), 3), "tipo": "whoosh"})
            ultimo = e["ini"]
        if e.get("variante") == "lista":
            sfx.append({"t": round(e["ini"] + 0.05, 3), "tipo": "ding"})

    gancho_visible = finales[0]["tipo"] != "tarjeta"
    plan = {
        "version": 1,
        "marca": marca_nombre,
        "titulo": guion.get("titulo", ""),
        "texto_pantalla": guion.get("texto_pantalla", ""),
        "texto_pantalla_original": guion.get("texto_pantalla_original", ""),
        "hashtags": guion.get("hashtags", []),
        "fuente_tiempos": datos.get("fuente"),
        "voz": str(Path(voz).resolve()),
        "audio_tramos": tramos,
        "duracion": duracion,
        "gancho": {"texto": guion.get("texto_pantalla", ""), "ini": 0.0,
                   "fin": round(min(3.0, frs[0][-1]["fin"] + 0.3), 3), "mostrar": gancho_visible},
        "escenas": finales,
        "subtitulos": subtitulos(palabras, marca),
        "sfx": sfx,
        "musica": {"src": str(Path(musica).resolve()), "volumen": 0.12} if musica else None,
        "barra_progreso": True,
        "grabaciones_pendientes": pendientes,
    }
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("palabras")
    ap.add_argument("--guion")
    ap.add_argument("--voz", required=True)
    ap.add_argument("--clips", help="Carpeta con grabaciones de pantalla (en el orden de las marcas [PANTALLA])")
    ap.add_argument("--broll", help="Carpeta con videos/imágenes de apoyo")
    ap.add_argument("--musica")
    ap.add_argument("--marca", default="atajo-ia")
    ap.add_argument("--corta", action="store_true", help="Quitar los bloques ✂️ (versión Shorts/Reels)")
    ap.add_argument("-o", "--salida", default="plan.json")
    a = ap.parse_args()
    guion = leer_json(a.guion) if a.guion else {}
    plan = armar(leer_json(a.palabras), guion, a.voz, a.clips, a.broll, a.musica, a.marca, a.corta)
    escribir_json(a.salida, plan)
    print(f"Plan: {len(plan['escenas'])} escenas, {len(plan['subtitulos'])} subtítulos, "
          f"{plan['duracion']:.1f}s → {a.salida}")
    if plan["grabaciones_pendientes"]:
        print("Faltan grabaciones de pantalla para:\n  - " + "\n  - ".join(plan["grabaciones_pendientes"]))


if __name__ == "__main__":
    main()
