# 🎬 TROUBLE — Pipeline ACE-Step 1.5 para Google Colab

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/porchenoche-stack/trouble-colab/blob/main/TROUBLE_pipeline_colab.ipynb)

Genera la canción **TROUBLE** (rap bilingüe UK / México) con [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) y monta un vídeo con tus imágenes. Todo corre en Colab, nada en tu PC.

## Cómo usarlo

1. Pulsa el botón **Abrir en Colab** de arriba.
2. **Entorno de ejecución → Cambiar tipo de entorno → GPU T4 → Guardar**.
3. Sube tus imágenes (PNG/JPG/WEBP) al panel 📁 de la izquierda.
4. Ejecuta la celda (▶ o Shift+Enter).

La primera vez tarda ~15-25 min (instala ACE-Step 1.5 y descarga ~10 GB de modelos). Después, ~3-6 min.

## Salida

- `/content/trouble_prod/output/TROUBLE_COMPLETA.wav` — canción masterizada a -14 LUFS
- `/content/trouble_prod/output/TROUBLE_PREVIEW.mp4` — vídeo 1920x1080 con las imágenes

## Opciones (formulario de la celda)

| Opción | Qué hace |
|---|---|
| `MODELO` | `acestep-v15-turbo` (recomendado en T4) o `acestep-v15-xl-turbo` |
| `DURACION_SEG` | Duración de la canción (10-600 s) |
| `SEED` | Semilla: misma semilla = mismo resultado |
| `HACER_VIDEO` | Montar el vídeo con tus imágenes |
| `SOLO_REHACER_VIDEO` | Rehace solo el vídeo sin volver a generar el audio |

## Si falla

El recuadro rojo incluye el **ERROR REAL**: cópialo entero.
