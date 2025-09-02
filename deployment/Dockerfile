# ---- Base: Python slim with a few OS deps ----
FROM python:3.11-slim AS base

# Prevents python from writing .pyc files & enables unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    TZ=UTC

# System deps:
# - build-essential: safer for wheels that may need compilation
# - tzdata: timezone handling
# - libgomp1: numba / vectorbt parallelization
# - git, curl: optional but handy
# - libfreetype6, libpng16-16: matplotlib runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tzdata libgomp1 git curl ca-certificates \
    libfreetype6 libpng16-16 \
 && rm -rf /var/lib/apt/lists/*

# Create non-root user
ARG USER=appuser
ARG UID=10001
RUN useradd -m -u ${UID} -s /bin/bash ${USER}

WORKDIR /app

# ---- Dependencies layer (leverages Docker cache) ----
# Check if production requirements exist, otherwise use dev requirements
COPY requirements*.txt ./
RUN if [ -f requirements-prod.txt ]; then \
        echo "Installing production requirements..." && \
        pip install --upgrade pip && pip install -r requirements-prod.txt; \
    else \
        echo "Installing development requirements..." && \
        pip install --upgrade pip && pip install -r requirements.txt; \
    fi

# ---- App code ----
COPY . /app

# Ensure reports/ and data/ exist & writable
RUN mkdir -p /app/reports /app/data /app/logs && chown -R ${USER}:${USER} /app
USER ${USER}

# Expose port for web dashboard
EXPOSE 8000

# Default entrypoint is the CLI; can be overridden by docker-compose
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--help"]

# For web dashboard, use: CMD ["python", "run_live_dashboard.py"]