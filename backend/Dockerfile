FROM python:3.11-slim

WORKDIR /app

# ----------------------------------------------------
# Install system dependencies required for:
# - Postgres client
# ----------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    poppler-utils \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libgdk-pixbuf-xlib-2.0-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff5-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*


# ----------------------------------------------------
# Install uv (based on Astral official Docker method)
# ----------------------------------------------------
ENV UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
RUN chmod +x /bin/uv

# ----------------------------------------------------
# Copy dependency file early for caching
# ----------------------------------------------------
COPY requirements.txt .

# ----------------------------------------------------
# Install Python dependencies using uv
# ----------------------------------------------------
RUN uv pip install --system -r requirements.txt

# ----------------------------------------------------
# Install CmdStan for Prophet (requires g++ and make from earlier)
# ----------------------------------------------------
RUN python -m cmdstanpy.install_cmdstan


# ----------------------------------------------------
# Copy application code
# ----------------------------------------------------
COPY . .
# ----------------------------------------------------
EXPOSE 8000
# ----------------------------------------------------
# Health Check
# ----------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# ----------------------------------------------------
# Start Backend
# ----------------------------------------------------
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
