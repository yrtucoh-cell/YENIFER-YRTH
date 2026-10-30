---
name: editor-videos-virales
description: Edita videos verticales virales (TikTok, Reels, Shorts) a partir de los audios de narración que entrega la usuaria y de los guiones del repo (tecnologia-ia/guiones, guiones/). Limpia el audio y recorta pausas, sincroniza subtítulos palabra por palabra, inserta grabaciones de pantalla en las marcas [PANTALLA], crea tarjetas de texto, zooms, efectos de sonido, barra de progreso, música con ducking y CTA final, y exporta 1080x1920 a -14 LUFS con portada, .srt y textos para publicar. Usar cuando diga "edita el video", "aquí está el audio del día N", "haz el video de este guion", "versión corta/Shorts", o entregue un audio de narración.
---

# Editor de videos virales

Convierte **audio de narración + guion** en un video vertical listo para publicar. Antes de editar,
lee `referencias/formatos-virales.md`: explica qué formato usar y por qué funciona cada recurso.

## Qué necesitas de la usuaria

| Entrada | Obligatorio | Dónde suele estar |
|---|---|---|
| Audio de la narración (m4a, mp3, wav, ogg/opus de WhatsApp, o un video del que se usa el audio) | Sí | `entradas/dia-N/` o archivo subido |
| Qué guion es (archivo + día) | Recomendado | `tecnologia-ia/guiones/semana-1.md`, día N |
| Grabaciones de pantalla, en el orden de las marcas `[PANTALLA]` del guion (`01.mp4`, `02.mp4`…) | Para guiones con [PANTALLA] | `entradas/dia-N/clips/` |
| B-roll (videos o imágenes de apoyo) | Opcional | `entradas/dia-N/broll/` o `entradas/broll/` |
| Música sin copyright (Biblioteca de audio de YouTube) | Opcional | `entradas/musica/` |

Si no dice qué guion es, compara el audio con los guiones (transcribe o pregunta). Si faltan
grabaciones para las marcas `[PANTALLA]`, el plan lo avisa en `grabaciones_pendientes`: díselo y
ofrece renderizar igualmente (esas partes usan tarjetas) o esperar las grabaciones.

## Flujo

1. **Preparar** (una vez por sesión):
   ```bash
   pip install -r .claude/skills/editor-videos-virales/requirements.txt   # faster-whisper + Pillow
   ```
   Requiere `ffmpeg`. Si Whisper no puede descargar su modelo (sin internet), el sistema usa el
   modo **estimado** (alinea el guion con las pausas del audio): funciona, pero los subtítulos pueden
   ir algo desfasados. Avísalo.

2. **Editar** con un solo comando (desde la raíz del repo):
   ```bash
   python .claude/skills/editor-videos-virales/scripts/editar.py \
     --audio entradas/dia-1/voz.m4a \
     --guion tecnologia-ia/guiones/semana-1.md --dia 1 \
     --clips entradas/dia-1/clips --broll entradas/broll --musica entradas/musica/tema.mp3 \
     --marca atajo-ia --ambas --salida videos
   ```
   - `--ambas`: versión **completa** (TikTok, más de 1 min, válida para Creator Rewards) y **corta**
     (sin los bloques ✂️, para Shorts/Reels). `--corta` solo la corta.
   - `--marca`: `atajo-ia` o `mente-y-dinero` (archivos en `marcas/`).
   - `--solo-plan`: se detiene tras crear `plan.json` para revisarlo.
   - `--borrador`: render rápido de baja calidad.
   - `--pausa-max 0.35`: pausa máxima en segundos (más bajo = ritmo más rápido; 0,25 a 0,45).

3. **Revisar siempre antes de entregar**:
   ```bash
   python .claude/skills/editor-videos-virales/scripts/revisar.py videos/<carpeta>/video.mp4 -n 16
   ```
   Abre `revision.png` con Read y comprueba:
   - El gancho se ve en el primer fotograma y se lee en menos de 2 s.
   - Los subtítulos no tapan nada importante de las grabaciones de pantalla.
   - Las palabras clave grandes (escenas `fondo`) tienen sentido; si no, cámbialas en el plan.
   - Hay un cambio visual cada 2–4 s.
   - La tarjeta final (CTA) aparece.
   Si `fuente_tiempos` es `estimado`, extrae 2–3 fotogramas sueltos con ffmpeg y compara el subtítulo
   con lo que se dice en ese momento.

4. **Ajustar** `plan.json` y volver a renderizar solo esa versión:
   ```bash
   python .claude/skills/editor-videos-virales/scripts/render.py videos/<carpeta>/plan.json
   ```
   Ajustes habituales en `plan.json`:
   - `escenas[i].texto`: la palabra o frase grande de una tarjeta o fondo.
   - `escenas[i].tipo`: `clip` | `tarjeta` (`variante`: `gancho`, `lista`, `concepto`) | `fondo` | `cta`.
   - `escenas[i].zoom`: `in` | `out` | `punch` | `none`. Para grabaciones de pantalla usa `in` o `none`.
   - `escenas[i].foco`: `[x, y]` de 0 a 1, el punto hacia el que se hace zoom (p. ej. `[0.5, 0.2]` = arriba).
   - `escenas[i].desde`: segundo de la grabación desde el que empieza.
   - `subtitulos[j].palabras[k].texto`: corregir errores de transcripción. `resaltar: true` pinta la palabra.
   - `gancho.texto` / `gancho.mostrar`: el texto en caja blanca de los primeros 3 s (se muestra cuando
     la primera escena es un clip).
   - `sfx`: lista `{t, tipo: whoosh|pop|ding, volumen}`.
   - `musica.volumen`: entre 0,08 y 0,15 (la voz siempre por encima; ya se aplica ducking).
   - Los tiempos de las escenas deben ser contiguos (el `fin` de una es el `ini` de la siguiente).

5. **Entregar**: envía `video.mp4`, `portada.png` y `publicacion.md` con SendUserFile. Resume:
   duración, versión, qué revisaste, qué falta (grabaciones pendientes, tiempos estimados).
   **No subas los .mp4 a git** (`videos/` y `entradas/` están en `.gitignore`); solo se versionan
   guiones, marcas y la skill.

## Salidas por video (`videos/<dia-N-titulo>/`)

| Archivo | Uso |
|---|---|
| `video.mp4` | 1080x1920, 30 fps, H.264 + AAC, -14 LUFS, listo para subir |
| `portada.png` | Portada para Reels/TikTok/Shorts |
| `subtitulos.srt` | Para subir como subtítulos aparte (YouTube) |
| `publicacion.md` | Descripción y hashtags para cada plataforma + lista de comprobación |
| `plan.json` | Decisiones de edición (editable) |
| `voz.wav`, `palabras.json`, `guion.json` | Intermedios (audio limpio y tiempos) |

## Personalizar la marca

Edita `marcas/<marca>.json`: colores, `usuario`, `cta_texto`, tamaño y altura de los subtítulos,
`palabras_clave` (se resaltan siempre) y `hashtags_base`. Para usar una tipografía propia (Montserrat
ExtraBold, Anton, The Bold Font…), copia el `.ttf` en `fuentes/`: se elige automáticamente si su nombre
aparece en `fuentes.subtitulos` / `fuentes.titulos`. Para efectos de sonido propios, pon
`whoosh.wav`, `pop.wav` o `ding.wav` en `sfx/` (si no, se sintetizan).

## Guiones sin formato de semana

Para un video que no está en un `.md` de guiones, pasa un `.txt` con la narración en `--guion`
(cada línea es narración) o no pases guion: con Whisper se transcribe directamente.
Los videos largos de YouTube (8+ min, horizontales) no son el objetivo de esta skill.
