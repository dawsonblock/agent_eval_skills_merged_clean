FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Base system deps
RUN apt-get update && apt-get install -y \
    curl wget git ca-certificates gnupg \
    python3 python3-pip rsync postgresql-client \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libatspi2.0-0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxrandr2 libgbm1 libxcb1 \
    libxkbcommon0 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Create venv OUTSIDE /workspace so it is not shadowed by the volume mount
# camel-ai brings: openai, pyyaml, httpx, tiktoken, etc.
RUN uv venv /opt/venv && uv pip install --python /opt/venv/bin/python \
    "camel-ai" \
    "anthropic" \
    "playwright==1.52.0" \
    "psycopg2-binary" \
    "openpyxl" \
    "python-docx" \
    "python-pptx" \
    "termcolor" \
    "aiofiles" \
    "psutil" \
    "addict" \
    "arxiv" \
    "bibtexparser" \
    "canvasapi" \
    "prompt_toolkit"

ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"
ENV SKIP_EXISTING_ARTIFACTS=1
ARG INSTALL_PLAYWRIGHT=0

# Install Playwright browser only when explicitly requested.
RUN if [ "$INSTALL_PLAYWRIGHT" = "1" ]; then \
            playwright install chromium; \
        else \
            echo "Skipping Playwright browser install (INSTALL_PLAYWRIGHT=$INSTALL_PLAYWRIGHT)"; \
        fi

# Copy only required runtime/build inputs to keep cache stable and context small.
COPY scripts/ /workspace/scripts/
COPY configs/ /workspace/configs/
COPY local_servers/ /opt/local_servers/
ENV LOCAL_SERVERS_PATH="/opt/local_servers"
WORKDIR /workspace
RUN bash scripts/build_required_mcp_artifacts.sh && \
    find /opt/local_servers -type d -name node_modules -prune -exec rm -rf '{}' +
RUN python scripts/preflight_mcp_paths.py

CMD ["/bin/bash"]
