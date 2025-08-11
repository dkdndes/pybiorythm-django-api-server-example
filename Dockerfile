FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY . .

# Run migrations and collect static files
RUN uv run python manage.py migrate
RUN uv run python manage.py collectstatic --noinput

# Expose port for ASGI server
EXPOSE 8001

# Run with Daphne ASGI server
CMD ["uv", "run", "daphne", "biorhythm_api.asgi:application", "-p", "8001", "-b", "0.0.0.0"]