# syntax=docker/dockerfile:1-labs
FROM python:3.13-alpine AS base

RUN apk add --no-cache \
    poetry

COPY pyproject.toml poetry.lock* /build/


# =============================================================================
# DEV-BUILDER STAGE (Development)
# =============================================================================
FROM base AS dev-builder
WORKDIR /build
# Configure Poetry for dev build
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true

# Install all dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/poetry \
    poetry install --all-groups --no-root

RUN ls -la /build/
RUN find /build -name ".venv" -type d

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM python:3.13-alpine AS development

# Create dev user
RUN addgroup -g 1000 devuser && \
    adduser -D -u 1000 -G devuser -s /bin/sh -h /app devuser

# Set working directory
WORKDIR /app

# Copy virtual environment from dev-builder
COPY --from=dev-builder --chown=devuser:devuser /build/.venv /app/.venv

# Switch to unprivileged user
USER devuser

# Copy application source code
COPY --chown=devuser:devuser src/ /app/src

# Configure environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# Create log directories
RUN mkdir -p /app/logs && \
    touch /app/logs/access.log && \
    touch /app/logs/error.log

# =============================================================================
# BUILDER STAGE (Production)
# =============================================================================
FROM base AS builder
WORKDIR /build
# Configure Poetry for production build
RUN poetry config virtualenvs.in-project true
# Install only production dependencies
RUN poetry install --only=main --no-root

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM python:3.13-alpine AS production

# Create production user
RUN addgroup -g 16458 produser && \
    adduser -D -u 16458 -G produser -s /bin/sh -h /app produser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=produser:produser /build/.venv /app/.venv

# Copy application source code
COPY --chown=produser:produser src/ /app/src
COPY --chown=produser:produser --chmod=600 .secrets.yml /app/.secrets.yml

# Switch to unprivileged user
USER produser

# Configure environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# Create log directories
RUN mkdir -p /app/logs && \
    touch /app/logs/access.log && \
    touch /app/logs/error.log



