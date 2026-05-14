FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/apps/api/.venv \
    PATH="/app/apps/api/.venv/bin:/root/.local/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY apps/api/pyproject.toml apps/api/uv.lock ./apps/api/
COPY apps/api/README.md ./apps/api/README.md
COPY apps/api/src ./apps/api/src
COPY apps/api/prompts ./apps/api/prompts
COPY apps/api/collector-seeds.json ./apps/api/collector-seeds.json
COPY packages/database/prisma ./packages/database/prisma

RUN uv sync --project apps/api --frozen --no-dev

# Prisma Client Python generation does not need the production database,
# but Prisma expects DATABASE_URL to exist while reading the schema.
ARG PRISMA_GENERATE_DATABASE_URL="postgresql://lockerpulse:lockerpulse@localhost:5432/lockerpulse"
RUN DATABASE_URL="${PRISMA_GENERATE_DATABASE_URL}" uv run --project apps/api prisma generate --schema packages/database/prisma/schema.prisma

EXPOSE 8000

CMD ["sh", "-c", "uv run --project apps/api uvicorn locker_pulse_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
