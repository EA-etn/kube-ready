# Voice-over script (en)

One audio file per scene, named by its number (01.wav, 02.wav... or 01-intro.wav), in this folder.
Formats: wav, mp3, m4a, ogg, flac.

Style instruction for Gemini:

> Read in clear, friendly English, like a calm technical walkthrough. Natural pauses at commas.

## 01-intro  →  01.wav

This is kube-ready, a linter for Kubernetes manifests that I built to answer one question: is this manifest ready for production? It needs no cluster, runs in a second, and fits in the pipeline, the pre-commit hook or a pull request.

## 02-problema  →  02.wav

Let us start with the problem. This Deployment looks fine, and Kubernetes accepts it without complaint. But look at the details: the image uses the latest tag, there is one replica, no probes, no memory limit, and the container may run as root. None of this fails today. It fails the day a node goes down or you need to roll back.

## 03-check  →  03.wav

I run kube-ready on it. In a second it returns every problem with its rule, its severity and the line in the file. One error, seven warnings and four info. And because there is an error, the exit code is one: in a pipeline, the deployment stops here, before it reaches the cluster.

## 04-como-funciona  →  04.wav

Inside there are four parts. A loader that understands multi-document YAML and the output of Helm or Kustomize, and remembers the file and line of every resource. A context with every resource of the run, so rules can look at related objects. Filters by config, by annotation or by baseline. And four output formats: text, JSON, SARIF and GitHub annotations.

## 05-reglas  →  05.wav

There are twenty-two rules in six families: images, resources, probes, availability, security and hygiene. Each rule is a small function with its own test, and each one explains why it exists. Some look across resources: an autoscaler with two minimum replicas satisfies the replica rule, and a Service that selects no pods is caught as a misconfiguration.

## 06-arreglado  →  06.wav

Now the same Deployment, fixed: two replicas spread across nodes, liveness and readiness probes, requests and limits, non-root, a read-only filesystem and all capabilities dropped. The verdict is ready, even at the strictest level.

## 07-config  →  07.wav

Every team has its own bar. With a config file I disable the rules that do not apply, raise the severity of the ones I consider critical, like a single replica, and decide at which level the build fails. And when one resource has a justified exception, an annotation in the manifest itself marks it.

## 08-baseline  →  08.wav

In a big repository, day one shows hundreds of findings. That is what the baseline is for: it records today's findings, lives in Git, and from then on the build fails only on new problems. The team adopts the tool without being blocked and pays the debt down over time.

## 09-pull-request  →  09.wav

In a pull request, the GitHub format turns every finding into an annotation on the line of the diff. And the SARIF report shows up in the repository's Security tab, next to the other security tools.

## 10-escenarios  →  10.wav

That is why it fits so many scenarios: GitOps repositories with Argo CD, Helm and Kustomize charts, pull request review, pre-commit hooks, Kubernetes upgrades, security hardening, legacy repositories, and as a shared policy for a platform team.

## 11-homelab  →  11.wav

I tried it on my own homelab, a k3s cluster managed with Argo CD. Ten resources, zero false positives, and three legitimate warnings on the synthetic traffic generator, which runs a single replica on purpose.

## 12-cadena-suministro  →  12.wav

And the tool applies to itself what it demands. CI actions are pinned by SHA and Dependabot keeps them current. The image is signed keyless with cosign, with an SBOM and provenance attestation. And CI runs lint, strict typing and nearly a hundred tests on four Python versions.

## 13-pruebala  →  13.wav

Install it with pip, use it as a GitHub Action in one line, or try it without installing anything with Docker or the browser playground. The code is open and on GitHub. Thanks for watching.
