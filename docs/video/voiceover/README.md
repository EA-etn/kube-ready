# Voz del vídeo explicativo

1. Abre `es/GUION.md` (o `en/GUION.md`): hay un texto por escena.
2. Genera cada texto con una voz (Gemini en AI Studio, ElevenLabs o tu propia grabación).
3. Guarda cada audio con el número de su escena: `01.wav`, `02.wav`, … `13.wav` (también vale mp3, m4a, ogg).
4. Súbelos a esta carpeta (`docs/video/voiceover/es/`) y regenera:

```bash
cd docs/video/src
node build.js --production explainer --lang es
```

Cada escena dura lo que dure su audio (más un pequeño margen). Las escenas sin audio usan una voz de
borrador. El montaje recorta silencios al principio y al final de cada archivo y nivela el volumen.
