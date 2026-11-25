# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY pyproject.toml ./
COPY app ./app
# WITH_VOICE=1 adds faster-whisper (free, local speech-to-text; ~200 MB)
ARG WITH_VOICE=1
RUN pip install --prefix=/install ".${WITH_VOICE:+[voice]}"

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 app
COPY --from=build /install /usr/local
WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
RUN mkdir -p /app/data/uploads /app/data/models && chown -R app:app /app/data
USER app
ENV PYTHONUNBUFFERED=1 UPLOAD_DIR=/app/data/uploads HF_HOME=/app/data/models
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s CMD python -c "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/health').status != 200)"
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
