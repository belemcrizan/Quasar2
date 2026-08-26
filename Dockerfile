# Scientific reproduction environment. Not a product image.
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY configs ./configs
COPY data ./data
COPY docs ./docs
COPY experiments ./experiments
COPY tests ./tests
COPY artifacts ./artifacts
RUN pip install --no-cache-dir -e ".[dev]"
CMD ["python", "-m", "quasar2.cli", "reproduce-paper", "--output", "experiments/results/paper_reproduce", "--overwrite"]
