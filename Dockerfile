# Requires configuration as env vars (.env).
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg && \
    update-ca-certificates && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        > /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-cloud-cli && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --no-group keyword --no-group dev
RUN uv run python -c "import nltk; nltk.download('punkt_tab')"

COPY practicepreach practicepreach/
COPY bin bin/
COPY bin/entrypoint.sh /entrypoint.sh

ENV PORT=8000

ENTRYPOINT ["/entrypoint.sh"]
