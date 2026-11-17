# Multi-stage, multi-arch (amd64 + arm64), runs as non-root. ~60 MB.
FROM python:3.13-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.13-slim
LABEL org.opencontainers.image.source="https://github.com/EA-etn/kube-ready" \
      org.opencontainers.image.description="Is this Kubernetes manifest ready for production?" \
      org.opencontainers.image.licenses="MIT"
COPY --from=build /install /usr/local
RUN useradd --uid 10001 --no-create-home kube-ready
USER 10001
WORKDIR /work
ENTRYPOINT ["kube-ready"]
CMD ["--help"]
