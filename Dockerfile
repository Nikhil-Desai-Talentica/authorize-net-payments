FROM python:3.12-slim

WORKDIR /app

# System deps (optional, add as needed)
RUN apt-get update \
    && apt-get install -y build-essential netcat-traditional postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./ 

# Install uv
RUN pip install uv

# Install deps (no dev extras)
RUN uv sync

ENV PATH="/app/.venv/bin:${PATH}"

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
