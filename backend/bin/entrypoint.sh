#!/bin/sh
# PORT is set by Cloud Run. I.e. GCP uses "PORT". We thus need the CMD shell
# form for env var expansion.

PORT=${PORT:-8001}
uv run uvicorn practicepreach.fast:app --host 0.0.0.0 --port ${PORT}
