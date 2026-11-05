# Apex Sovereign Multi-Stage Production Container
# 100% Pure Python Standard Library | Zero Dependencies

FROM python:3.11-slim AS builder

WORKDIR /app

# Ensure non-root system user
RUN useradd -m -u 1000 apex

# Copy application files
COPY . /app

# Final production stage
FROM python:3.11-slim AS runtime

WORKDIR /app

# Security: Non-root user configuration
RUN useradd -m -u 1000 apex
USER apex

COPY --chown=apex:apex --from=builder /app /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APEX_PORT=8000 \
    APEX_ENV=production

EXPOSE 8000 19999

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python /app/packaging/healthcheck.py || exit 1

ENTRYPOINT ["python", "/app/packaging/standalone_runner.py"]
