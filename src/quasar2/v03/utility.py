"""Explicit terminal reward and additive measured/proxy acquisition costs."""

from dataclasses import dataclass, fields
from quasar2.v03.contracts import Action, Costs, Outcome, finite


@dataclass(frozen=True)
class Utility:
    correct_reward: float = 1.0
    wrong_penalty: float = 1.0
    ask_cost: float = 0.28
    defer_cost: float = 0.05
    retrieval_price: float = 0.05
    model_price: float = 0
    token_price: float = 0
    latency_price: float = 0
    document_price: float = 0
    reranker_price: float = 0
    tool_price: float = 0
    monetary_weight: float = 0

    def __post_init__(self):
        for field in fields(self):
            finite(getattr(self, field.name), field.name)

    def cost(self, costs: Costs) -> float:
        return (
            costs.retrieval_calls * self.retrieval_price
            + costs.model_calls * self.model_price
            + (costs.input_tokens + costs.output_tokens) * self.token_price
            + costs.latency_ms * self.latency_price
            + costs.documents * self.document_price
            + costs.reranker_calls * self.reranker_price
            + costs.tool_calls * self.tool_price
            + costs.monetary * self.monetary_weight
        )

    def value(self, outcome: Outcome) -> float:
        if outcome.action == Action.DEFER:
            terminal = -self.defer_cost
        else:
            terminal = self.correct_reward if outcome.correct else -self.wrong_penalty
            if outcome.action == Action.ASK:
                terminal -= self.ask_cost
        return terminal - self.cost(outcome.costs)

    def delta(self, stop: Outcome, additional: Outcome) -> float:
        # Costs on additional outcomes are TOTAL trajectory costs, not deltas.
        return self.value(additional) - self.value(stop)


def require_extra_budget(stop: Outcome, additional: Outcome, maximum: int = 1):
    for field in fields(Costs):
        if getattr(additional.costs, field.name) < getattr(stop.costs, field.name):
            raise ValueError("Total trajectory costs cannot decrease")
    delta = additional.costs.retrieval_calls - stop.costs.retrieval_calls
    if delta < 0 or delta > maximum:
        raise ValueError("Counterfactual violates additional-call budget")
