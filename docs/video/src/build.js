// Renders a production (demo | explainer) to MP4 (+ optional GIF), frame by frame.
// Usage: node build.js --production explainer --lang es [--fps 12] [--gif] [--out ../]
// Explainer narration is synthesised with espeak-ng + MBROLA voices (apt: espeak-ng mbrola mbrola-es1 mbrola-en1).
const { chromium } = require('playwright');
const { execFileSync, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : (process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : true); };
const production = arg('production', 'demo'), lang = arg('lang', 'en'), fps = +arg('fps', 12);
const outDir = path.resolve(arg('out', '..')), wantGif = !!arg('gif', false);
// Draft voice only: espeak-ng's own voices (no MBROLA, which leaves gaps in Spanish).
// Real narration: one audio file per scene in docs/video/voiceover/<lang>/ (see GUION.md there).
const VOICE = { es: ['es', '-s', '150', '-p', '40'], en: ['en-us', '-s', '160', '-p', '40'] };
const VO_DIR = path.resolve(__dirname, '..', 'voiceover', lang);
const VO_EXT = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac'];
// How the Spanish voice should pronounce English terms (voice only, subtitles stay clean)
const PRON = { es: [[/kube-ready/g, 'kiub redi'], [/latest/g, 'léitest'], [/\broot\b/g, 'rut'], [/cosign/g, 'cosáin'], [/YAML/g, 'yámel'], [/JSON/g, 'yéison'], [/GitHub/g, 'guit jab'], [/pipeline/g, 'páiplain'], [/Kustomize/g, 'kastomáis'], [/pre-commit/g, 'pri commít'], [/Python/g, 'páiton'], [/Deployment/g, 'diplóiment'], [/probes/g, 'proubs'], [/baseline/g, 'béislain'], [/GitOps/g, 'guitops'], [/Docker/g, 'dóker'], [/Helm/g, 'jelm'], [/charts/g, 'charts'], [/SBOM/g, 'ese bom'], [/SHA/g, 'ese hache a'], [/pip/g, 'pip'], [/clúster/g, 'clúster'], [/Action/g, 'ákshon'], [/pull requests/g, 'pul recuésts'], [/Dependabot/g, 'dependabot']], en: [] };

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'kr-video-'));
const run = (cmd, args) => execFileSync(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] }).toString();
const dur = (f) => parseFloat(run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]));

function tts(text, i) {
  let spoken = text; for (const [re, to] of PRON[lang] || []) spoken = spoken.replace(re, to);
  const txt = path.join(tmp, `n${i}.txt`), raw = path.join(tmp, `n${i}.raw.wav`), wav = path.join(tmp, `n${i}.wav`);
  fs.writeFileSync(txt, spoken);
  run('espeak-ng', ['-v', VOICE[lang][0], ...VOICE[lang].slice(1), '-f', txt, '-w', raw]);
  run('ffmpeg', ['-y', '-v', 'error', '-i', raw, '-ar', '44100', '-ac', '1', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', wav]);
  return wav;
}

// One file with the whole narration (completo.wav / full.wav): split at the N-1 longest pauses.
function splitFull(n, narration) {
  if (!fs.existsSync(VO_DIR)) return null;
  const f = fs.readdirSync(VO_DIR).find((x) => /^(completo|full)\.(wav|mp3|m4a|ogg|flac|aac)$/i.test(x));
  if (!f) return null;
  const src = path.join(VO_DIR, f);
  const total = dur(src);
  const text = spawnSync('ffmpeg', ['-v', 'info', '-i', src, '-af', 'silencedetect=noise=-38dB:d=0.45', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
  const sil = []; let s0 = null;
  for (const line of text.split('\n')) {
    let m = line.match(/silence_start: ([\d.]+)/); if (m) s0 = +m[1];
    m = line.match(/silence_end: ([\d.]+) \| silence_duration: ([\d.]+)/); if (m && s0 !== null) { sil.push({ start: s0, end: +m[1], d: +m[2] }); s0 = null; }
  }
  const cutFile = path.join(VO_DIR, f.replace(/\.[^.]+$/, '.cortes.txt'));
  let cuts;
  if (fs.existsSync(cutFile)) {
    cuts = fs.readFileSync(cutFile, 'utf8').split('\n').map((l) => l.replace(/#.*/, '').trim()).filter(Boolean).map(Number);
    if (cuts.length !== n - 1 || cuts.some(isNaN)) throw new Error(`${cutFile}: need ${n - 1} cut times, found ${cuts.length}`);
    console.log(`  cuts from ${path.basename(cutFile)}`);
  } else {
  const inner = sil.filter((x) => x.start > 0.5 && x.end < total - 0.5);
  if (inner.length < n - 1) throw new Error(`${f}: found ${inner.length} pauses, need ${n - 1}. Run align.py or leave a long pause between scenes.`);
  cuts = inner.sort((a, b) => b.d - a.d).slice(0, n - 1).sort((a, b) => a.start - b.start).map((x) => (x.start + x.end) / 2);
  }
  const bounds = [0, ...cuts, total];
  // Sanity check: each piece should be roughly proportional to the length of its text.
  const chars = narration.map((x) => x.length), sumC = chars.reduce((a, b) => a + b, 0);
  const clips = [];
  for (let i = 0; i < n; i++) {
    const a = bounds[i], b = bounds[i + 1], got = b - a, want = (chars[i] / sumC) * total;
    const flag = got < want * 0.55 || got > want * 1.6 ? '  ⚠ check this scene' : '';
    console.log(`  scene ${String(i + 1).padStart(2, '0')}: ${a.toFixed(1)}–${b.toFixed(1)}s (${got.toFixed(1)}s, expected ~${want.toFixed(1)}s)${flag}`);
    const out = path.join(tmp, `full_${i}.wav`);
    run('ffmpeg', ['-y', '-v', 'error', '-i', src, '-ss', a.toFixed(3), '-to', b.toFixed(3), out]);
    clips.push(out);
  }
  return clips;
}
function findVoiceover(id) {
  if (!fs.existsSync(VO_DIR)) return null;
  const num = id.split('-')[0];
  const f = fs.readdirSync(VO_DIR).find((x) => VO_EXT.includes(path.extname(x).toLowerCase()) && (x.startsWith(id) || x.split(/[-_. ]/)[0] === num));
  return f ? path.join(VO_DIR, f) : null;
}
function normalise(file, i) {
  // Same format for every clip; trim leading/trailing silence that TTS tools add.
  const wav = path.join(tmp, `v${i}.wav`);
  run('ffmpeg', ['-y', '-v', 'error', '-i', file, '-ac', '1', '-ar', '44100',
    '-af', 'silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,loudnorm=I=-16:TP=-1.5:LRA=11', wav]);
  return wav;
}
function exportScript(ids, narration) {
  fs.mkdirSync(VO_DIR, { recursive: true });
  const es = lang === 'es';
  const head = es
    ? `# Guion para la voz (${lang})\n\nUn audio por escena. Nombra cada archivo con su número (01.wav, 02.wav... o 01-intro.wav) y déjalo en esta carpeta.\nFormatos: wav, mp3, m4a, ogg, flac.\n\nInstrucción de estilo para Gemini (pégala en "Style instructions"):\n\n> Lee en español de España, con tono cercano y seguro, como en un tutorial técnico. Ritmo tranquilo, pausas naturales en las comas. Pronuncia en inglés los términos técnicos: kube-ready, Kubernetes, Deployment, latest, root, pipeline, baseline, GitHub, Helm, Kustomize, Argo CD, cosign, SBOM.\n\n`
    : `# Voice-over script (${lang})\n\nOne audio file per scene, named by its number (01.wav, 02.wav... or 01-intro.wav), in this folder.\nFormats: wav, mp3, m4a, ogg, flac.\n\nStyle instruction for Gemini:\n\n> Read in clear, friendly English, like a calm technical walkthrough. Natural pauses at commas.\n\n`;
  const body = ids.map((id, i) => `## ${id}  →  ${id.split('-')[0]}.wav\n\n${narration[i]}\n`).join('\n');
  fs.writeFileSync(path.join(VO_DIR, 'GUION.md'), head + body);
  fs.writeFileSync(path.join(VO_DIR, 'TODO-JUNTO.txt'), narration.join('\n\n<long pause> <long pause>\n\n') + '\n');
  console.log(`wrote ${path.join(VO_DIR, 'GUION.md')}`);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => { console.error('page error:', e.message); process.exitCode = 1; });
  await page.goto(`file://${path.join(__dirname, 'player.html')}?production=${production}&lang=${lang}`);
  await page.evaluate(() => window.ready());
  const visual = await page.evaluate(() => window.VISUAL);
  let durs = visual, audio = null;
  if (production === 'explainer') {
    const narration = await page.evaluate(() => window.NARRATION);
    const ids = await page.evaluate(() => window.SCENE_IDS);
    if (arg('export-script', false)) { exportScript(ids, narration); await browser.close(); return; }
    let external = 0;
    const full = splitFull(ids.length, narration);
    const clips = narration.map((n, i) => {
      const own = findVoiceover(ids[i]);              // a per-scene file always wins (to redo one scene)
      if (own) { external++; return normalise(own, i); }
      if (full) { external++; return normalise(full[i], i); }
      return n ? tts(n, i) : null;
    });
    console.log(`  narration: ${external}/${ids.length} scenes from ${VO_DIR}, the rest with the draft voice`);
    durs = visual.map((v, i) => (clips[i] ? Math.max(v, dur(clips[i]) + 0.9) : v));
    // Mix: every clip starts at its scene start
    const starts = []; let acc = 0; for (const d of durs) { starts.push(acc); acc += d; }
    const inputs = [], filters = [], tags = [];
    clips.forEach((c, i) => { if (!c) return; const k = inputs.length / 2; inputs.push('-i', c); const ms = Math.round(starts[i] * 1000); filters.push(`[${k}]adelay=${ms}|${ms}[a${k}]`); tags.push(`[a${k}]`); });
    audio = path.join(tmp, 'audio.wav');
    run('ffmpeg', ['-y', '-v', 'error', ...inputs, '-filter_complex', `${filters.join(';')};${tags.join('')}amix=inputs=${tags.length}:normalize=0:dropout_transition=0,apad,atrim=0:${acc.toFixed(3)}`, audio]);
  }
  const total = await page.evaluate((d) => window.setTimeline(d), durs);
  const frames = Math.ceil(total * fps);
  console.log(`${production}/${lang}: ${durs.length} scenes, ${total.toFixed(1)}s, ${frames} frames @ ${fps} fps`);
  const fdir = path.join(tmp, 'frames'); fs.mkdirSync(fdir);
  for (let i = 0; i < frames; i++) {
    await page.evaluate((t) => window.seek(t), i / fps);
    await page.screenshot({ path: path.join(fdir, `f_${String(i).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 92 });
    if (i % 200 === 0) process.stdout.write(`  frame ${i}/${frames}\n`);
  }
  await browser.close();
  fs.mkdirSync(outDir, { recursive: true });
  const base = path.join(outDir, `kube-ready-${production}-${lang}`);
  const vargs = ['-y', '-v', 'error', '-framerate', String(fps), '-i', path.join(fdir, 'f_%05d.jpg')];
  if (audio) vargs.push('-i', audio);
  vargs.push('-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23', '-preset', 'medium', '-movflags', '+faststart');
  if (audio) vargs.push('-c:a', 'aac', '-b:a', '160k', '-shortest');
  vargs.push(`${base}.mp4`);
  run('ffmpeg', vargs);
  console.log(`  wrote ${base}.mp4 (${(fs.statSync(`${base}.mp4`).size / 1e6).toFixed(1)} MB, ${dur(`${base}.mp4`).toFixed(1)}s)`);
  if (wantGif) {
    run('ffmpeg', ['-y', '-v', 'error', '-i', `${base}.mp4`, '-vf', 'fps=10,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle', '-loop', '0', `${base}.gif`]);
    console.log(`  wrote ${base}.gif (${(fs.statSync(`${base}.gif`).size / 1e6).toFixed(1)} MB)`);
  }
  fs.rmSync(tmp, { recursive: true, force: true });
})();
