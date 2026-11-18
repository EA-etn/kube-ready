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
  const HOMELAB = [
    '', 'platform/monitoring/synthetic-traffic.yaml',
    '  ▲ RDY004  Deployment/monitoring/synthetic-traffic (line 4)  container "curl" has no livenessProbe',
    '  ▲ RDY005  Deployment/monitoring/synthetic-traffic (line 4)  container "curl" has no readinessProbe',
    '  ▲ RDY006  Deployment/monitoring/synthetic-traffic (line 4)  runs 1 replica',
    '', '0 errors, 3 warnings, 0 info across 10 resources in 10 files.',
  ];
  const CFG = ['disable: [RDY016, RDY021, RDY022]', 'severity:', '  RDY006: error', 'fail-on: warning'];
  const CFGCHECK = [
    '', 'deploy.yaml',
    '  ✖ RDY001  Deployment/shop/api (line 1)  container "api" uses image "ghcr.io/shop/api:latest" with tag latest',
    '  ▲ RDY002  Deployment/shop/api (line 1)  container "api" has no cpu or memory request',
    '  ▲ RDY003  Deployment/shop/api (line 1)  container "api" has no memory limit',
    '  ▲ RDY004  Deployment/shop/api (line 1)  container "api" has no livenessProbe',
    '  ▲ RDY005  Deployment/shop/api (line 1)  container "api" has no readinessProbe',
    '  ✖ RDY006  Deployment/shop/api (line 1)  runs 1 replica',
    '  ▲ RDY010  Deployment/shop/api (line 1)  container "api" does not set allowPrivilegeEscalation: false',
    '  ▲ RDY011  Deployment/shop/api (line 1)  container "api" may run as root',
    '  ℹ RDY012  Deployment/shop/api (line 1)  container "api" has a writable root filesystem',
    '', '2 errors, 6 warnings, 1 info across 1 resources in 1 files.',
  ];
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
    cfg1: { cmd: 'cat .kube-ready.yaml', out: CFG, cap: '', accent: '#8b5cf6', clear: true },
    cfg2: { cmd: 'kube-ready check deploy.yaml', out: CFGCHECK, cap: '', accent: '#8b5cf6' },
    homelab: { cmd: 'kube-ready check apps/ platform/ bootstrap/', out: HOMELAB, cap: '', accent: '#10b981', clear: true },
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
      'Esto es kube-ready, un linter para manifiestos de Kubernetes que he construido para responder a una sola pregunta: ¿este manifiesto está listo para producción? No necesita clúster, tarda un segundo, y se integra en el pipeline, en el pre-commit o en una pull request.',
      'Empecemos por el problema. Este Deployment parece correcto, y Kubernetes lo acepta sin quejarse. Pero fíjate en los detalles: la imagen usa la etiqueta latest, solo hay una réplica, no hay probes, no hay límites de memoria, y el contenedor puede correr como root. Nada de esto falla hoy. Falla el día que un nodo se cae o que hay que hacer rollback.',
      'Le paso kube-ready. En un segundo devuelve cada problema con su regla, su severidad y la línea del fichero. Uno es un error, siete son avisos y cuatro son informativos. Y como hay un error, el código de salida es uno: en un pipeline, el despliegue se para aquí, antes de llegar al clúster.',
      'Por dentro hay cuatro piezas. Un cargador que entiende YAML multidocumento y la salida de Helm o Kustomize, y que recuerda el fichero y la línea de cada recurso. Un contexto con todos los recursos de la ejecución, para que las reglas puedan mirar objetos relacionados. Unos filtros por configuración, por anotación o por baseline. Y cuatro formatos de salida: texto, JSON, SARIF y anotaciones de GitHub.',
      'Hay veintidós reglas, agrupadas en seis familias: imágenes, recursos, probes, disponibilidad, seguridad e higiene. Cada regla es una función pequeña, con su test, y cada una explica por qué existe. Algunas cruzan recursos: un autoescalado con dos réplicas mínimas satisface la regla de réplicas, y un Service que no selecciona ningún pod se detecta como error de configuración.',
      'Ahora el mismo Deployment, arreglado: dos réplicas repartidas entre nodos, probes de vida y de disponibilidad, requests y límites, sin root, sistema de ficheros de solo lectura y capacidades eliminadas. El veredicto es listo, incluso con el nivel más estricto.',
      'Cada equipo tiene sus reglas. Con un fichero de configuración desactivo las reglas que no aplican, subo la severidad de las que considero críticas, como la de una sola réplica, y decido a partir de qué nivel falla el build. Y si un recurso concreto tiene una excepción justificada, se marca con una anotación en el propio manifiesto.',
      'En un repositorio grande, el primer día aparecen cientos de hallazgos. Para eso está el baseline: registra los hallazgos de hoy, se guarda en Git, y a partir de ahí el build solo falla con problemas nuevos. Así el equipo adopta la herramienta sin bloquearse, y va reduciendo la deuda poco a poco.',
      'En una pull request, el formato de GitHub convierte cada hallazgo en una anotación sobre la línea del diff. Y el informe SARIF aparece en la pestaña Security del repositorio, junto al resto de herramientas de seguridad.',
      'Por eso encaja en muchos escenarios: repositorios GitOps con Argo CD, charts de Helm y Kustomize, revisión de pull requests, hooks de pre-commit, actualizaciones de versión de Kubernetes, endurecimiento de seguridad, repositorios heredados, y como política común de un equipo de plataforma.',
      'La he probado sobre mi propio homelab, un clúster k3s gestionado con Argo CD. Diez recursos, cero falsos positivos, y tres avisos legítimos en el generador de tráfico sintético, que corre con una sola réplica a propósito.',
      'Y la herramienta se aplica a sí misma lo que exige. Las acciones del CI están fijadas por SHA y Dependabot las mantiene al día. La imagen se firma con cosign sin claves, con SBOM y atestación de procedencia. Y el CI ejecuta lint, tipado estricto y casi cien tests en cuatro versiones de Python.',
      'Puedes instalarla con pip, usarla como GitHub Action con una línea, o probarla sin instalar nada con Docker o en el playground del navegador. El código es abierto y está en GitHub. Gracias por verlo.',
    ],
    en: [
      'This is kube-ready, a linter for Kubernetes manifests that I built to answer one question: is this manifest ready for production? It needs no cluster, runs in a second, and fits in the pipeline, the pre-commit hook or a pull request.',
      'Let us start with the problem. This Deployment looks fine, and Kubernetes accepts it without complaint. But look at the details: the image uses the latest tag, there is one replica, no probes, no memory limit, and the container may run as root. None of this fails today. It fails the day a node goes down or you need to roll back.',
      'I run kube-ready on it. In a second it returns every problem with its rule, its severity and the line in the file. One error, seven warnings and four info. And because there is an error, the exit code is one: in a pipeline, the deployment stops here, before it reaches the cluster.',
      'Inside there are four parts. A loader that understands multi-document YAML and the output of Helm or Kustomize, and remembers the file and line of every resource. A context with every resource of the run, so rules can look at related objects. Filters by config, by annotation or by baseline. And four output formats: text, JSON, SARIF and GitHub annotations.',
      'There are twenty-two rules in six families: images, resources, probes, availability, security and hygiene. Each rule is a small function with its own test, and each one explains why it exists. Some look across resources: an autoscaler with two minimum replicas satisfies the replica rule, and a Service that selects no pods is caught as a misconfiguration.',
      'Now the same Deployment, fixed: two replicas spread across nodes, liveness and readiness probes, requests and limits, non-root, a read-only filesystem and all capabilities dropped. The verdict is ready, even at the strictest level.',
      'Every team has its own bar. With a config file I disable the rules that do not apply, raise the severity of the ones I consider critical, like a single replica, and decide at which level the build fails. And when one resource has a justified exception, an annotation in the manifest itself marks it.',
      'In a big repository, day one shows hundreds of findings. That is what the baseline is for: it records today\'s findings, lives in Git, and from then on the build fails only on new problems. The team adopts the tool without being blocked and pays the debt down over time.',
      'In a pull request, the GitHub format turns every finding into an annotation on the line of the diff. And the SARIF report shows up in the repository\'s Security tab, next to the other security tools.',
      'That is why it fits so many scenarios: GitOps repositories with Argo CD, Helm and Kustomize charts, pull request review, pre-commit hooks, Kubernetes upgrades, security hardening, legacy repositories, and as a shared policy for a platform team.',
      'I tried it on my own homelab, a k3s cluster managed with Argo CD. Ten resources, zero false positives, and three legitimate warnings on the synthetic traffic generator, which runs a single replica on purpose.',
      'And the tool applies to itself what it demands. CI actions are pinned by SHA and Dependabot keeps them current. The image is signed keyless with cosign, with an SBOM and provenance attestation. And CI runs lint, strict typing and nearly a hundred tests on four Python versions.',
      'Install it with pip, use it as a GitHub Action in one line, or try it without installing anything with Docker or the browser playground. The code is open and on GitHub. Thanks for watching.',
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
      rules: '22 reglas, 6 familias', rulesSub: 'Una función pequeña por regla, con su test y su porqué',
      r1: '<b>Imágenes</b>: tag inmutable o digest, nunca latest',
      r2: '<b>Recursos</b>: requests de CPU y memoria, límite de memoria',
      r3: '<b>Probes</b>: liveness y readiness',
      r4: '<b>Disponibilidad</b>: réplicas, PodDisruptionBudget, reparto entre nodos',
      r5: '<b>Seguridad</b>: root, privileged, hostPath, capabilities, seccomp',
      r6: '<b>Higiene</b>: APIs eliminadas, Secrets en Git, TLS, etiquetas',
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
      rules: '22 rules, 6 families', rulesSub: 'One small function per rule, with its test and its why',
      r1: '<b>Images</b>: immutable tag or digest, never latest',
      r2: '<b>Resources</b>: CPU and memory requests, memory limit',
      r3: '<b>Probes</b>: liveness and readiness',
      r4: '<b>Availability</b>: replicas, PodDisruptionBudget, spread across nodes',
      r5: '<b>Security</b>: root, privileged, hostPath, capabilities, seccomp',
      r6: '<b>Hygiene</b>: removed APIs, Secrets in Git, TLS, labels',
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
      { id: '01-intro', type: 'slide', kind: 'title', eyebrow: 'github.com/EA-etn/kube-ready', title: 'kube-ready', sub: s.tagline, narration: n[0] },
      { id: '02-problema', type: 'terminal', blocks: [b.cat], narration: n[1] },
      { id: '03-check', type: 'terminal', blocks: [b.check, b.exit], narration: n[2] },
      { id: '04-como-funciona', type: 'slide', kind: 'image', title: s.how, sub: s.howSub, bullets: [s.how1, s.how2, s.how3, s.how4], image: `../../diagrams/${lang}/01-how-it-works.png`, narration: n[3] },
      { id: '05-reglas', type: 'slide', kind: 'bullets', title: s.rules, sub: s.rulesSub, bullets: [s.r1, s.r2, s.r3, s.r4, s.r5, s.r6], narration: n[4] },
      { id: '06-arreglado', type: 'terminal', blocks: [b.fixed], narration: n[5] },
      { id: '07-config', type: 'terminal', blocks: [b.cfg1, b.cfg2], narration: n[6] },
      { id: '08-baseline', type: 'terminal', blocks: [b.base1, b.base2], narration: n[7] },
      { id: '09-pull-request', type: 'terminal', blocks: [b.gh], narration: n[8] },
      { id: '10-escenarios', type: 'slide', kind: 'image', title: s.sc, sub: s.scSub, bullets: [s.sc1, s.sc2, s.sc3, s.sc4, s.sc5, s.sc6, s.sc7], image: `../../diagrams/${lang}/02-scenarios.png`, narration: n[9] },
      { id: '11-homelab', type: 'terminal', blocks: [b.homelab], narration: n[10] },
      { id: '12-cadena-suministro', type: 'slide', kind: 'bullets', title: s.sup, sub: s.supSub, bullets: [s.sup1, s.sup2, s.sup3, s.sup4], narration: n[11] },
      { id: '13-pruebala', type: 'slide', kind: 'cta', title: s.cta, sub: s.ctaSub, narration: n[12] },
    ];
  };

  window.SCRIPT = { demo, explainer };
})();
