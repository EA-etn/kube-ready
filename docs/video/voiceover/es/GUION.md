# Guion para la voz (es)

Un audio por escena. Nombra cada archivo con su número (01.wav, 02.wav... o 01-intro.wav) y déjalo en esta carpeta.
Formatos: wav, mp3, m4a, ogg, flac.

Instrucción de estilo para Gemini (pégala en "Style instructions"):

> Lee en español de España, con tono cercano y seguro, como en un tutorial técnico. Ritmo tranquilo, pausas naturales en las comas. Pronuncia en inglés los términos técnicos: kube-ready, Kubernetes, Deployment, latest, root, pipeline, baseline, GitHub, Helm, Kustomize, Argo CD, cosign, SBOM.

## 01-intro  →  01.wav

Esto es kube-ready, un linter para manifiestos de Kubernetes que he construido para responder a una sola pregunta: ¿este manifiesto está listo para producción? No necesita clúster, tarda un segundo, y se integra en el pipeline, en el pre-commit o en una pull request.

## 02-problema  →  02.wav

Empecemos por el problema. Este Deployment parece correcto, y Kubernetes lo acepta sin quejarse. Pero fíjate en los detalles: la imagen usa la etiqueta latest, solo hay una réplica, no hay probes, no hay límites de memoria, y el contenedor puede correr como root. Nada de esto falla hoy. Falla el día que un nodo se cae o que hay que hacer rollback.

## 03-check  →  03.wav

Le paso kube-ready. En un segundo devuelve cada problema con su regla, su severidad y la línea del fichero. Uno es un error, siete son avisos y cuatro son informativos. Y como hay un error, el código de salida es uno: en un pipeline, el despliegue se para aquí, antes de llegar al clúster.

## 04-como-funciona  →  04.wav

Por dentro hay cuatro piezas. Un cargador que entiende YAML multidocumento y la salida de Helm o Kustomize, y que recuerda el fichero y la línea de cada recurso. Un contexto con todos los recursos de la ejecución, para que las reglas puedan mirar objetos relacionados. Unos filtros por configuración, por anotación o por baseline. Y cuatro formatos de salida: texto, JSON, SARIF y anotaciones de GitHub.

## 05-reglas  →  05.wav

Hay veintidós reglas, agrupadas en seis familias: imágenes, recursos, probes, disponibilidad, seguridad e higiene. Cada regla es una función pequeña, con su test, y cada una explica por qué existe. Algunas cruzan recursos: un autoescalado con dos réplicas mínimas satisface la regla de réplicas, y un Service que no selecciona ningún pod se detecta como error de configuración.

## 06-arreglado  →  06.wav

Ahora el mismo Deployment, arreglado: dos réplicas repartidas entre nodos, probes de vida y de disponibilidad, requests y límites, sin root, sistema de ficheros de solo lectura y capacidades eliminadas. El veredicto es listo, incluso con el nivel más estricto.

## 07-config  →  07.wav

Cada equipo tiene sus reglas. Con un fichero de configuración desactivo las reglas que no aplican, subo la severidad de las que considero críticas, como la de una sola réplica, y decido a partir de qué nivel falla el build. Y si un recurso concreto tiene una excepción justificada, se marca con una anotación en el propio manifiesto.

## 08-baseline  →  08.wav

En un repositorio grande, el primer día aparecen cientos de hallazgos. Para eso está el baseline: registra los hallazgos de hoy, se guarda en Git, y a partir de ahí el build solo falla con problemas nuevos. Así el equipo adopta la herramienta sin bloquearse, y va reduciendo la deuda poco a poco.

## 09-pull-request  →  09.wav

En una pull request, el formato de GitHub convierte cada hallazgo en una anotación sobre la línea del diff. Y el informe SARIF aparece en la pestaña Security del repositorio, junto al resto de herramientas de seguridad.

## 10-escenarios  →  10.wav

Por eso encaja en muchos escenarios: repositorios GitOps con Argo CD, charts de Helm y Kustomize, revisión de pull requests, hooks de pre-commit, actualizaciones de versión de Kubernetes, endurecimiento de seguridad, repositorios heredados, y como política común de un equipo de plataforma.

## 11-homelab  →  11.wav

La he probado sobre mi propio homelab, un clúster k3s gestionado con Argo CD. Diez recursos, cero falsos positivos, y tres avisos legítimos en el generador de tráfico sintético, que corre con una sola réplica a propósito.

## 12-cadena-suministro  →  12.wav

Y la herramienta se aplica a sí misma lo que exige. Las acciones del CI están fijadas por SHA y Dependabot las mantiene al día. La imagen se firma con cosign sin claves, con SBOM y atestación de procedencia. Y el CI ejecuta lint, tipado estricto y casi cien tests en cuatro versiones de Python.

## 13-pruebala  →  13.wav

Puedes instalarla con pip, usarla como GitHub Action con una línea, o probarla sin instalar nada con Docker o en el playground del navegador. El código es abierto y está en GitHub. Gracias por verlo.
