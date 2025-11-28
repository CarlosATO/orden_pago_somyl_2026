# Multi-stage Dockerfile: build frontend with Node, run backend with Python + Gunicorn

# --- Builder: build the Vite React frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
# Install dependencies and build
COPY nuevo_proyecto/frontend/package.json ./
COPY nuevo_proyecto/frontend/package-lock.json ./
RUN npm ci --silent
COPY nuevo_proyecto/frontend/ ./
RUN npm run build

# --- Runtime: Python image to run Flask app with Gunicorn ---
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY nuevo_proyecto/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY nuevo_proyecto/backend/ ./backend

# Copy start script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Copy built frontend from builder into backend/static (so Flask or other server can serve it if needed)
COPY --from=frontend-builder /app/frontend/dist ./backend/frontend_dist

# Expose port
EXPOSE 5001

# Default command
CMD ["/bin/sh", "./start.sh"]
