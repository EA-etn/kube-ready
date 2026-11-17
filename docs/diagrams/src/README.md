# Diagrams as code

Same kit as [homelab-k3s](https://github.com/EA-etn/homelab-k3s/tree/main/docs/diagrams/src): HTML +
[Lucide](https://lucide.dev) icons, rendered to PNG and animated SVG in English and Spanish (`i18n.js`).

- `01-how-it-works`: inputs → engine → outputs → where it runs (README).
- `02-scenarios`: the seven places the tool fits (README).
- `00-social`: repository social preview (1280×640): GitHub → Settings → Social preview.

```bash
cd docs/diagrams/src
npm install                        # lucide-static + playwright
npx playwright install chromium    # first time only
pip install fonttools brotli       # pyftsubset, to embed font subsets in the SVGs
npm run render                     # → docs/diagrams/{en,es}/*.{png,svg}
```
