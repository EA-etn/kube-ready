# Videos as code

Two productions rendered frame by frame from `player.html` with Playwright, assembled with ffmpeg:

- **demo**: a 35-second terminal demo with captions, no audio. GIF for the README + MP4.
- **explainer**: a two-minute narrated walkthrough (title, the problem, the run, how it works,
  scenarios, the fix and the baseline, supply chain, try it) with on-screen subtitles.

The terminal output is the real output of kube-ready on `demo/`. Scenes, captions and the
narration live in `script.js`, in English and Spanish. The voice is synthetic: espeak-ng with
MBROLA voices, so it is understandable but clearly not a person. Replace it by dropping your own
recordings in place of the generated clips if you want a human voice.

```bash
sudo apt-get install ffmpeg espeak-ng mbrola mbrola-es1 mbrola-en1
cd docs/video/src
node build.js --production demo --lang en --gif        # → docs/video/kube-ready-demo-en.{mp4,gif}
node build.js --production explainer --lang es         # → docs/video/kube-ready-explainer-es.mp4
```

`player.html?production=explainer&lang=es` opens in a browser too; `window.seek(seconds)` in the
console scrubs the timeline.
