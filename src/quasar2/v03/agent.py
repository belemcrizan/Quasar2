"""Provider-independent, explicit model execution ledger; no automatic API calls."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from quasar2.v03.contracts import Costs, IntegrityError, RuntimeState, reject_hidden
from quasar2.v03.registry import digest, write_json


@dataclass(frozen=True)
class ModelOutput:
    text: str
    costs: Costs


class Model(Protocol):
    def complete(self, request: dict) -> ModelOutput: ...


def execute(
    model: Model,
    *,
    query: str,
    state: RuntimeState,
    evidence: dict[str, str],
    provider: str,
    model_id: str,
    revision: str,
    prompt: str,
    output,
):
    """Call an explicitly supplied model once, recording configuration and output.

    The caller owns credentials and rate/cost limits. This is a ledger primitive,
    not an implemented multi-step agent benchmark or independent verifier.
    """
    if not all(
        isinstance(v, str) and v.strip() for v in (query, provider, model_id, revision, prompt)
    ):
        raise IntegrityError("Explicit query, provider, model, revision and prompt required")
    if set(evidence) != set(state.evidence_ids):
        raise IntegrityError("Evidence does not match frozen state")
    request = {
        "query": query,
        "runtime": state.to_dict(),
        "evidence": dict(evidence),
        "prompt": prompt,
    }
    reject_hidden(request)
    config = {
        "provider": provider,
        "model": model_id,
        "revision": revision,
        "prompt_hash": digest(prompt),
    }
    key = digest({"request": request, "config": config})
    destination = Path(output) / key
    destination.mkdir(parents=True, exist_ok=False)  # reserve before any billable call
    write_json(
        destination / "request.json", {"request": request, "config": config, "request_hash": key}
    )
    try:
        result = model.complete(request)
        if (
            not isinstance(result, ModelOutput)
            or not isinstance(result.text, str)
            or result.costs.model_calls != 1
        ):
            raise IntegrityError("Model must return text and measured single-call costs")
        from dataclasses import asdict

        write_json(
            destination / "response.json",
            {
                "text": result.text,
                "costs": asdict(result.costs),
                "output_hash": digest(result.text),
                "status": "COMPLETE",
                "evaluation": "NOT_EVALUATED",
                "provenance": "provider adapter declared; ledger does not attest execution",
            },
        )
    except Exception as error:
        write_json(
            destination / "FAILED.json", {"status": "FAILED", "error_type": type(error).__name__}
        )
        raise
    return destination
