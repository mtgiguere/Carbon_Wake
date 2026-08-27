# The web app container (deployment step; PROJECT_SPEC: single VM, Docker
# Compose, deliberately no managed services). One image serves the API, the
# map page, and static assets (WhiteNoise) behind Caddy.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the package first so the layer caches across code-only changes is
# NOT possible with a src layout + pyproject alone; keep it simple and honest:
# copy, install, run. The image rebuilds in ~a minute; this project optimizes
# for auditability over build cleverness.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . gunicorn

COPY manage.py docker-entrypoint.py ./

EXPOSE 8000

# Two workers is plenty for portfolio traffic on a small VM; WhiteNoise
# serves static from the installed package (finders mode, ADR-0015). The
# entrypoint applies the idempotent schema so a fresh stack serves the honest
# empty state instead of a 500 on a missing table.
ENTRYPOINT ["python", "docker-entrypoint.py"]
CMD ["gunicorn", "carbon_atlas.web.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]
