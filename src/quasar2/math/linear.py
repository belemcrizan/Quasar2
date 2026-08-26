"""Tiny ridge regression. No gold-intent features belong here."""

from __future__ import annotations


def ridge_fit(rows: list[list[float]], targets: list[float], *, lam: float = 1e-3) -> list[float]:
    if not rows:
        raise ValueError("empty design")
    n_features = len(rows[0])
    xtx = [[0.0] * n_features for _ in range(n_features)]
    xty = [0.0] * n_features
    for row, target in zip(rows, targets):
        for i in range(n_features):
            xty[i] += row[i] * target
            for j in range(n_features):
                xtx[i][j] += row[i] * row[j]
    for i in range(n_features):
        xtx[i][i] += lam
    return _solve(xtx, xty)


def _solve(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    n = len(rhs)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        diag = aug[col][col]
        if abs(diag) < 1e-12:
            continue
        scale = 1.0 / diag
        for j in range(col, n + 1):
            aug[col][j] *= scale
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def dot(weights: list[float], features: list[float]) -> float:
    return sum(left * right for left, right in zip(weights, features))
