# Voz del vídeo explicativo

Dos formas de hacerlo; elige una.

## Opción A: todo de golpe (un solo audio)

1. Copia el contenido de `es/TODO-JUNTO.txt` (todas las escenas seguidas, con `<long pause>` entre ellas).
2. Pégalo en un único bloque de Gemini (AI Studio → Playground → modelo TTS), genera y descarga.
3. Guarda el archivo como `es/completo.wav` (o `completo.mp3`).

El montaje corta el audio por las 12 pausas más largas y comprueba que cada trozo dura lo esperado
para su texto. Si avisa con ⚠ en alguna escena, alarga la pausa entre esas dos escenas y vuelve a
generar.

## Opción B: un audio por escena

Genera cada texto de `es/GUION.md` por separado y guárdalo como `01.wav`, `02.wav`, … `13.wav`.
Sirve también para corregir una sola escena de la opción A: un `07.wav` sustituye al trozo 7 de
`completo.wav`.

## Si las pausas entre escenas no se notan

Algunas voces ignoran `<long pause>`. Entonces:

```bash
pip install librosa numpy
python docs/video/src/align.py es    # escribe es/completo.cortes.txt
```

Alinea una lectura sintética del guion con tu audio y escribe los 12 tiempos de corte. Puedes
retocarlos a mano en ese fichero.

## Regenerar el vídeo

```bash
cd docs/video/src
node build.js --production explainer --lang es
```

Cada escena dura lo que dure su audio. Se recortan los silencios del principio y del final y se
nivela el volumen.
