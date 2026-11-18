"""Find the scene boundaries in a single narration file (voiceover/<lang>/completo.wav).

TTS tools do not always honour long pauses between scenes, so cutting at the longest silences is
unreliable. This script reads the script with espeak-ng (where every scene boundary is known),
aligns that reading to the real narration with dynamic time warping on MFCCs, and snaps each
boundary to the nearest real pause. It writes voiceover/<lang>/completo.cortes.txt, which build.js
uses. Edit that file by hand to nudge a cut.

    pip install librosa numpy
    python align.py es
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np

HERE = Path(__file__).resolve().parent
SR, HOP = 16000, 640  # 40 ms frames
VOICE = {"es": "es", "en": "en-us"}


def narration(lang: str) -> list[str]:
    js = (
        "const fs=require('fs'),vm=require('vm');const c={window:{}};"
        f"vm.runInNewContext(fs.readFileSync({json.dumps(str(HERE / 'script.js'))},'utf8'),c);"
        f"console.log(JSON.stringify(c.window.SCRIPT.explainer({json.dumps(lang)}).map(s=>s.narration)))"
    )
    return json.loads(
        subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    )


def mfcc(y: np.ndarray) -> np.ndarray:
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, hop_length=HOP, n_fft=1024)[1:]
    return (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-8)


def pauses(path: Path) -> list[tuple[float, float]]:
    err = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "info",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-42dB:d=0.12",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stderr
    out, start = [], None
    for line in err.splitlines():
        if m := re.search(r"silence_start: ([\d.]+)", line):
            start = float(m.group(1))
        if (
            m := re.search(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", line)
        ) and start is not None:
            out.append(((start + float(m.group(1))) / 2, float(m.group(2))))
            start = None
    return out


def main() -> None:
    lang = sys.argv[1] if len(sys.argv) > 1 else "es"
    vo = HERE.parent / "voiceover" / lang
    target = next(
        p
        for p in vo.iterdir()
        if re.match(r"(completo|full)\.(wav|mp3|m4a|ogg|flac|aac)$", p.name, re.I)
    )
    texts = narration(lang)
    with tempfile.TemporaryDirectory() as tmp:
        refs = []
        for i, t in enumerate(texts):
            wav = Path(tmp) / f"{i:02d}.wav"
            subprocess.run(
                ["espeak-ng", "-v", VOICE[lang], "-s", "165", "-w", str(wav), t], check=True
            )
            refs.append(librosa.load(wav, sr=SR)[0])
    bounds, acc = [], 0
    for r in refs[:-1]:
        acc += len(r)
        bounds.append(acc / HOP)
    tgt = librosa.load(target, sr=SR)[0]
    _, wp = librosa.sequence.dtw(
        X=mfcc(np.concatenate(refs)), Y=mfcc(tgt), metric="cosine", backtrack=True
    )
    wp = wp[::-1]
    sil = pauses(target)
    lines = [f"# Scene boundaries in {target.name} (seconds). One per line; edit to nudge a cut."]
    for i, b in enumerate(bounds):
        t = float(wp[min(np.searchsorted(wp[:, 0], b), len(wp) - 1), 1] * HOP / SR)
        near = min(sil, key=lambda p: abs(p[0] - t)) if sil else None
        snapped = near[0] if near and abs(near[0] - t) <= 1.2 else t
        note = "pause" if snapped != t else "NO PAUSE NEAR: check this cut"
        lines.append(f"{snapped:.2f}   # {i + 1:02d}→{i + 2:02d}  aligned {t:.2f}s, {note}")
        print(lines[-1])
    out = vo / f"{target.stem}.cortes.txt"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
