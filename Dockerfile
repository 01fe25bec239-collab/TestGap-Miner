FROM ghcr.io/astral-sh/uv:0.11.28 AS uv

FROM python:3.12-slim

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

COPY --from=uv /uv /uvx /bin/
COPY apps/api /app/apps/api
COPY scripts/deploy/migrate.sh /app/scripts/deploy/migrate.sh
RUN uv sync --project /app/apps/api --locked --no-dev
RUN groupadd --system app && useradd --system --gid app app && chown -R app:app /app /opt/venv

USER app
WORKDIR /app/apps/api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
