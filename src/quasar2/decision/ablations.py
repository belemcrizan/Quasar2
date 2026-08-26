"""Named policy ablations. Legacy pipeline ablations stay frozen separately."""

from __future__ import annotations

# Frozen v0.1.1 loop ablations live in pipeline.VALID_ABLATIONS.
# The set below is for v2 shadow / MyopicVoIPolicy only.

V2_POLICY_ABLATIONS = frozenset(
    {
        "full",
        "noHyp",
        "noAnalyze",
        "noExplore",
        "noAsk",
        "noUpdate",
        "randomExplore",
        "legacy",
        "noRecoverability",
        "noVoI",
        "noUCB",
        "noConformal",
        "noRisk",
        "noCost",
    }
)

ABLATION_QUESTIONS = {
    "full": "Does the complete v2 recommendation differ from legacy execution?",
    "noHyp": "Does removing competing hypotheses collapse recoverability?",
    "noAnalyze": "Does forbidding ANALYZE change recommended_action_v2?",
    "noExplore": "Does forbidding EXPLORE shift mass onto ASK/DEFER/ANSWER?",
    "noAsk": "Does forbidding ASK increase DEFER or forced ANSWER recommendations?",
    "noUpdate": "Does freezing belief make ANALYZE/EXPLORE recommendations vacuous?",
    "randomExplore": "Does a random explore policy match discriminative EXPLORE?",
    "legacy": "Does the v2 recommender copy the executed legacy action?",
    "noRecoverability": "Does dropping recoverability make EXPLORE track entropy alone?",
    "noVoI": "Does dropping VoI make stopping/UCB undefined and EXPLORE entropy-driven?",
    "noUCB": "Does point NetVoI without UCB over-stop relative to Bonferroni?",
    "noConformal": "Does the heuristic prediction set change the recommendation?",
    "noRisk": "Does ignoring risk increase ANSWER under high unknown mass?",
    "noCost": "Does ignoring cost increase EXPLORE/ASK rates?",
}
