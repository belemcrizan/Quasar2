# Scientific + API image. No secrets. Offline sanity fixtures are copied in.
FROM python:3.13-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --prefix=/install .

FROM python:3.13-slim
WORKDIR /app
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin quasar \
    && mkdir -p /app && chown -R quasar:quasar /app
COPY --from=builder /install /usr/local
COPY --chown=quasar:quasar pyproject.toml README.md LICENSE ./
COPY --chown=quasar:quasar src ./src
COPY --chown=quasar:quasar configs ./configs
COPY --chown=quasar:quasar data ./data
COPY --chown=quasar:quasar docs ./docs
COPY --chown=quasar:quasar experiments ./experiments
COPY --chown=quasar:quasar tests ./tests
COPY --chown=quasar:quasar artifacts ./artifacts
ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1
USER quasar
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["python", "-m", "quasar2.cli", "serve", "--host", "0.0.0.0", "--port", "8080"]
