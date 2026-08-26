"""Proxy observation kernels for shadow recoverability.

These kernels are not claimed to be the true p(o | H, a). They exist so
recoverability can be computed without contaminating the executed legacy policy.
"""

from __future__ import annotations

from typing import Mapping


def bernoulli_support_kernels(
    supports: Mapping[str, float],
) -> dict[str, dict[str, float]]:
    """Map each hypothesis to a two-outcome proxy: hit vs miss.

    P(hit | H) is clipped support in [0, 1]. Label the method as a proxy in
    telemetry; do not treat the kernels as oracle observation models.
    """

    kernels: dict[str, dict[str, float]] = {}
    for hyp, support in supports.items():
        p_hit = max(0.0, min(1.0, float(support)))
        kernels[str(hyp)] = {"hit": p_hit, "miss": 1.0 - p_hit}
    return kernels
