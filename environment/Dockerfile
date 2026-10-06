FROM python:3.11-slim@sha256:ad5dadd957a398226996bc4846e522c39f2a77340b531b28aaab85b2d361210b

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    jq \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install standard analytical packages
RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    openpyxl==3.1.5 \
    pyarrow==16.1.0 \
    pypdf==4.2.0

WORKDIR /workspace

# Create output and logs directory structure
RUN mkdir -p /workspace/output /logs/verifier
