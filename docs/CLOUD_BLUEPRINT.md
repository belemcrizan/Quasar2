# Cloud blueprint (not executed)

This is a **local-first** blueprint. It is not a deployment log. Do not paste secrets into the image or compose file.

## Provider-agnostic sketch

1. Build: `docker compose build`
2. Run: `docker compose up`
3. Smoke: `curl http://127.0.0.1:8080/health` then `curl http://127.0.0.1:8080/ready`
4. Rollback: previous image tag; artifacts live on a read-only volume (`experiments/results`)
5. Secrets: inject via the orchestrator's secret store (never `ENV TOKEN=` in Dockerfile)
6. Logs: stdout JSON from the stdlib server (request id header `X-Request-ID`)
7. Cost: sanity CPU-only; no GPU required; neural extras optional and expensive

## Gate G

Local `/health` probes at concurrency 1 and 10 are **TESTED**. Cloud SLO is **NOT_RUN** until an authorized environment exists.

Estimated order of magnitude for the stdlib cockpit: one small CPU instance. Do not quote a vendor invoice from this document.
