// Renders a production (demo | explainer) to MP4 (+ optional GIF), frame by frame.
// Usage: node build.js --production explainer --lang es [--fps 12] [--gif] [--out ../]
// Explainer narration is synthesised with espeak-ng + MBROLA voices (apt: espeak-ng mbrola mbrola-es1 mbrola-en1).
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : (process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : true); };
const production = arg('production', 'demo'), lang = arg('lang', 'en'), fps = +arg('fps', 12);
const outDir = path.resolve(arg('out', '..')), wantGif = !!arg('gif', false);
const VOICE = { es: ['mb-es1', '-s', '135', '-p', '45'], en: ['mb-en1', '-s', '150', '-p', '45'] };
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
  run('ffmpeg', ['-y', '-v', 'error', '-i', raw, '-ar', '22050', '-ac', '1', '-af', 'volume=1.4', wav]);
  return wav;
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
    const clips = narration.map((n, i) => (n ? tts(n, i) : null));
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
  if (audio) vargs.push('-c:a', 'aac', '-b:a', '112k', '-shortest');
  vargs.push(`${base}.mp4`);
  run('ffmpeg', vargs);
  console.log(`  wrote ${base}.mp4 (${(fs.statSync(`${base}.mp4`).size / 1e6).toFixed(1)} MB, ${dur(`${base}.mp4`).toFixed(1)}s)`);
  if (wantGif) {
    run('ffmpeg', ['-y', '-v', 'error', '-i', `${base}.mp4`, '-vf', 'fps=10,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle', '-loop', '0', `${base}.gif`]);
    console.log(`  wrote ${base}.gif (${(fs.statSync(`${base}.gif`).size / 1e6).toFixed(1)} MB)`);
  }
  fs.rmSync(tmp, { recursive: true, force: true });
})();
