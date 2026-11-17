// Scenes and narration for the two productions, in Spanish and English.
// Terminal output is the real output of kube-ready 0.1.0 on docs/video/src/demo/.
(function () {
  const DEPLOY = [
    'apiVersion: apps/v1', 'kind: Deployment', 'metadata:', '  name: api', '  namespace: shop',
    'spec:', '  replicas: 1', '  selector:', '    matchLabels: {app: api}', '  template:',
    '    metadata:', '      labels: {app: api}', '    spec:', '      containers:', '        - name: api',
    '          image: ghcr.io/shop/api:latest', '          ports:', '            - containerPort: 3000',
  ];
  const CHECK = [
    '', 'deploy.yaml',
    '  ✖ RDY001  Deployment/shop/api (line 1)  container "api" uses image "ghcr.io/shop/api:latest" with tag latest',
    '  ▲ RDY002  Deployment/shop/api (line 1)  container "api" has no cpu or memory request',
    '  ▲ RDY003  Deployment/shop/api (line 1)  container "api" has no memory limit',
    '  ▲ RDY004  Deployment/shop/api (line 1)  container "api" has no livenessProbe',
    '  ▲ RDY005  Deployment/shop/api (line 1)  container "api" has no readinessProbe',
    '  ▲ RDY006  Deployment/shop/api (line 1)  runs 1 replica',
    '  ▲ RDY010  Deployment/shop/api (line 1)  container "api" does not set allowPrivilegeEscalation: false',
    '  ▲ RDY011  Deployment/shop/api (line 1)  container "api" may run as root',
    '  ℹ RDY012  Deployment/shop/api (line 1)  container "api" has a writable root filesystem',
    '  ℹ RDY016  Deployment/shop/api (line 1)  has no app.kubernetes.io/name label',
    '  ℹ RDY021  Deployment/shop/api (line 1)  container "api" does not drop all capabilities',
    '  ℹ RDY022  Deployment/shop/api (line 1)  container "api" has no seccomp profile',
    '', '1 error, 7 warnings, 4 info across 1 resources in 1 files.',
    'Run with --verbose to see how to fix each finding, or `kube-ready rules` for the full list.',
  ];
  const FIXED = ['✔ Ready. 2 resources in 1 files, no findings.'];
  const BASE1 = ['34 findings recorded in .kube-ready-baseline.json. Commit it and run `kube-ready check ... --baseline .kube-ready-baseline.json`.'];
  const BASE2 = ['✔ Ready. 5 resources in 1 files, no new findings. (34 known findings hidden by baseline .kube-ready-baseline.json)'];
  const GH = [
    '::error file=deploy.yaml,line=1,title=RDY001 Image tag is mutable::Deployment/shop/api: container "api" uses image "ghcr.io/shop/api:latest" with tag latest. Pin a version (`app:1.4.2`) or a digest (`app@sha256:…`).',
    '::warning file=deploy.yaml,line=1,title=RDY002 Missing resource requests::Deployment/shop/api: container "api" has no cpu or memory request. Set `resources.requests.cpu` and `resources.requests.memory`.',
  ];

  const T = {
    es: {
      cap1: 'Un Deployment que Kubernetes acepta sin quejarse',
      cap2: 'kube-ready: cada problema con su línea, su severidad y cómo arreglarlo',
      cap3: 'Código de salida 1: el pipeline se para aquí',
      cap4: 'Arreglado: dos réplicas, probes, límites, sin root',
      cap5: '¿Repo grande? Registra lo de hoy y falla solo con lo nuevo',
      cap6: 'En un PR: anotaciones en el diff, SARIF en la pestaña Security',
    },
    en: {
      cap1: 'A Deployment that Kubernetes accepts without complaint',
      cap2: 'kube-ready: every problem with its line, severity and how to fix it',
      cap3: 'Exit code 1: the pipeline stops here',
      cap4: 'Fixed: two replicas, probes, limits, non-root',
      cap5: 'Big repo? Record today\'s findings, fail only on new ones',
      cap6: 'In a PR: annotations on the diff, SARIF in the Security tab',
    },
  };

  const blocks = (t) => ({
    cat: { cmd: 'cat deploy.yaml', out: DEPLOY, cap: t.cap1, accent: '#8b5cf6' },
    check: { cmd: 'kube-ready check deploy.yaml', out: CHECK, cap: t.cap2, accent: '#f97316', clear: true },
    exit: { cmd: 'echo $?', out: ['1'], cap: t.cap3, accent: '#f43f5e' },
    fixed: { cmd: 'kube-ready check deploy-fixed.yaml --fail-on info', out: FIXED, cap: t.cap4, accent: '#10b981', clear: true },
    base1: { cmd: 'kube-ready baseline manifests/', out: BASE1, cap: t.cap5, accent: '#06b6d4' },
    base2: { cmd: 'kube-ready check manifests/ --baseline .kube-ready-baseline.json', out: BASE2, cap: t.cap5, accent: '#06b6d4' },
    gh: { cmd: 'kube-ready check deploy.yaml --format github', out: GH, cap: t.cap6, accent: '#3b82f6', clear: true },
  });

  const demo = (lang) => {
    const b = blocks(T[lang]);
    return [
      { type: 'terminal', blocks: [b.cat, b.check, b.exit] },
      { type: 'terminal', blocks: [b.fixed, b.base1, b.base2] },
      { type: 'terminal', blocks: [b.gh] },
    ];
  };

  // Narration: plain text for the voice. English terms are spelled the way a Spanish
  // voice should say them.
  const N = {
    es: [
      'kube-ready es un linter para manifiestos de Kubernetes. Responde a una sola pregunta: ¿este manifiesto está listo para producción?',
      'Este Deployment parece correcto, y Kubernetes lo acepta sin quejarse. Pero usa la etiqueta latest, tiene una sola réplica, no tiene probes ni límites de memoria, y corre como root. Todo eso duele el día que algo falla.',
      'kube-ready lo lee en un segundo, sin conectarse a ningún clúster. Devuelve cada problema con su línea, su severidad y una pista para arreglarlo. Si hay errores, el código de salida es uno, y el pipeline se para.',
      'Por dentro hay cuatro piezas. Un cargador que entiende YAML multidocumento y recuerda fichero y línea. Veintidós reglas, cada una una función pequeña que explica por qué existe. Filtros por configuración, por anotación o por baseline. Y cuatro salidas: texto, JSON, SARIF y anotaciones de GitHub.',
      'Encaja en siete escenarios: repositorios GitOps, charts de Helm y Kustomize, revisión de pull requests, pre-commit, actualizaciones de clúster, endurecimiento de seguridad, y repositorios grandes heredados, gracias al baseline.',
      'Arreglado el manifiesto, el veredicto es listo. Y en un repositorio grande, el baseline registra los hallazgos de hoy para fallar solo con los nuevos.',
      'La herramienta se aplica a sí misma lo que exige: acciones fijadas por SHA, imagen firmada con cosign, SBOM, Dependabot, y tests en cuatro versiones de Python.',
      'Instálala con pip, úsala como GitHub Action, o pruébala sin instalar nada con Docker. El código está en GitHub.',
    ],
    en: [
      'kube-ready is a linter for Kubernetes manifests. It answers one question: is this manifest ready for production?',
      'This Deployment looks fine, and Kubernetes accepts it without complaint. But it uses the latest tag, runs one replica, has no probes and no memory limit, and runs as root. All of that hurts on the day something fails.',
      'kube-ready reads it in a second, without talking to any cluster. It returns every problem with its line, its severity and a hint to fix it. If there are errors, the exit code is one, and the pipeline stops.',
      'Inside there are four parts. A loader that understands multi-document YAML and remembers file and line. Twenty-two rules, each a small function that explains why it exists. Filters by config, by annotation or by baseline. And four outputs: text, JSON, SARIF and GitHub annotations.',
      'It fits seven scenarios: GitOps repositories, Helm and Kustomize charts, pull request review, pre-commit, cluster upgrades, security hardening, and big legacy repositories, thanks to the baseline.',
      'With the manifest fixed, the verdict is ready. And in a big repository, the baseline records today\'s findings so the build fails only on new ones.',
      'The tool applies to itself what it demands: actions pinned by SHA, an image signed with cosign, an SBOM, Dependabot, and tests on four Python versions.',
      'Install it with pip, use it as a GitHub Action, or try it with Docker without installing anything. The code is on GitHub.',
    ],
  };

  const S = {
    es: {
      tagline: '¿Este manifiesto de Kubernetes está listo para producción?',
      how: 'Cómo funciona', howSub: 'De los manifiestos al veredicto en un segundo',
      how1: '<b>Cargador</b>: YAML multidocumento, fichero y línea',
      how2: '<b>22 reglas</b>: una función pequeña, cada una explica el porqué',
      how3: '<b>Filtros</b>: config, anotación ignore, baseline',
      how4: '<b>Salidas</b>: texto, JSON, SARIF, anotaciones GitHub',
      sc: 'Escenarios', scSub: 'Una herramienta, siete sitios donde se gana el sueldo',
      sc1: 'Repositorio GitOps', sc2: 'Helm y Kustomize', sc3: 'Revisión de pull requests', sc4: 'Pre-commit',
      sc5: 'Actualización del clúster', sc6: 'Endurecimiento de seguridad', sc7: 'Repo grande heredado',
      sup: 'Cadena de suministro', supSub: 'Se aplica a sí misma lo que exige',
      sup1: 'Acciones <b>fijadas por SHA</b>, Dependabot al día',
      sup2: 'Imagen <b>firmada con cosign</b>, sin claves',
      sup3: '<b>SBOM</b> y atestación de procedencia',
      sup4: 'Tests en <b>cuatro versiones</b> de Python, mypy strict',
      cta: 'Pruébala', ctaSub: 'Sin clúster. Un segundo. Sin instalar nada si no quieres.',
    },
    en: {
      tagline: 'Is this Kubernetes manifest ready for production?',
      how: 'How it works', howSub: 'From manifests to a verdict in one second',
      how1: '<b>Loader</b>: multi-document YAML, file and line',
      how2: '<b>22 rules</b>: one small function, each one says why',
      how3: '<b>Filters</b>: config, ignore annotation, baseline',
      how4: '<b>Outputs</b>: text, JSON, SARIF, GitHub annotations',
      sc: 'Scenarios', scSub: 'One tool, seven places it earns its keep',
      sc1: 'GitOps repository', sc2: 'Helm and Kustomize', sc3: 'Pull request review', sc4: 'Pre-commit',
      sc5: 'Cluster upgrade', sc6: 'Security hardening', sc7: 'Big legacy repository',
      sup: 'Supply chain', supSub: 'It applies to itself what it demands',
      sup1: 'Actions <b>pinned by SHA</b>, Dependabot keeps them current',
      sup2: 'Image <b>signed with cosign</b>, keyless',
      sup3: '<b>SBOM</b> and provenance attestation',
      sup4: 'Tests on <b>four Python versions</b>, mypy strict',
      cta: 'Try it', ctaSub: 'No cluster. One second. Nothing to install if you do not want to.',
    },
  };

  const explainer = (lang) => {
    const b = blocks(T[lang]); const s = S[lang]; const n = N[lang];
    return [
      { type: 'slide', kind: 'title', eyebrow: 'github.com/EA-etn/kube-ready', title: 'kube-ready', sub: s.tagline, narration: n[0] },
      { type: 'terminal', blocks: [b.cat], narration: n[1] },
      { type: 'terminal', blocks: [b.check, b.exit], narration: n[2] },
      { type: 'slide', kind: 'image', title: s.how, sub: s.howSub, bullets: [s.how1, s.how2, s.how3, s.how4], image: `../../diagrams/${lang}/01-how-it-works.png`, narration: n[3] },
      { type: 'slide', kind: 'image', title: s.sc, sub: s.scSub, bullets: [s.sc1, s.sc2, s.sc3, s.sc4, s.sc5, s.sc6, s.sc7], image: `../../diagrams/${lang}/02-scenarios.png`, narration: n[4] },
      { type: 'terminal', blocks: [b.fixed, b.base1, b.base2], narration: n[5] },
      { type: 'slide', kind: 'bullets', title: s.sup, sub: s.supSub, bullets: [s.sup1, s.sup2, s.sup3, s.sup4], narration: n[6] },
      { type: 'slide', kind: 'cta', title: s.cta, sub: s.ctaSub, narration: n[7] },
    ];
  };

  window.SCRIPT = { demo, explainer };
})();
