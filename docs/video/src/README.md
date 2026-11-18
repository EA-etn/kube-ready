# Videos as code

Two productions rendered frame by frame from `player.html` with Playwright, assembled with ffmpeg:

- **demo**: a 35-second terminal demo with captions, no audio. GIF for the README + MP4.
- **explainer**: a five-minute narrated walkthrough (title, the problem, the run, how it works,
  scenarios, the fix and the baseline, supply chain, try it) with on-screen subtitles.

The terminal output is the real output of kube-ready on `demo/`. Scenes, captions and the
narration live in `script.js`, in English and Spanish.

The narration comes from `docs/video/voiceover/<lang>/NN.wav`, one file per scene (see the
`GUION.md` there, generated with `--export-script`). Scenes without a file use a draft voice
(espeak-ng). Each scene lasts as long as its audio.

```bash
sudo apt-get install ffmpeg espeak-ng
cd docs/video/src
node build.js --production demo --lang en --gif        # → docs/video/kube-ready-demo-en.{mp4,gif}
node build.js --production explainer --lang es --export-script   # → voiceover/es/GUION.md
node build.js --production explainer --lang es         # → docs/video/kube-ready-explainer-es.mp4
```

`player.html?production=explainer&lang=es` opens in a browser too; `window.seek(seconds)` in the
console scrubs the timeline.
