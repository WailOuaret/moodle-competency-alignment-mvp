# The alignment service for the private teacher pilot.
#
# Build context is the repository root (see docker-compose.yml). Only service/ and the engine
# package are copied in, and only the dependencies they import are installed. No .env, no data
# directory, no research artefacts, no tests.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src:/app

# A fixed, unprivileged account. It owns nothing it needs to write: the engine works in a
# throwaway directory under /tmp, which compose mounts as a tmpfs.
RUN groupadd --system --gid 10001 alignment \
 && useradd --system --uid 10001 --gid alignment --no-create-home --shell /usr/sbin/nologin alignment

WORKDIR /app

COPY deploy/pilot/alignment/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY src/moodle_competency /app/src/moodle_competency
COPY service /app/service

USER alignment

# Listening on 80 inside the container lets Moodle reach it on a port its own HTTP security
# rules already allow. The container may bind it without root because compose sets
# net.ipv4.ip_unprivileged_port_start=0 for this container's network namespace only.
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:80/health', timeout=4).status == 200 else 1)"]

# One worker: the service is stateless, and a pilot of a handful of teachers does not need more.
# --no-server-header and no --reload. /docs stays off unless ALIGNMENT_ENABLE_DOCS is set.
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "80", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
