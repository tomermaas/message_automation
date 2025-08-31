# syntax=docker/dockerfile:1

# Build frontend assets
FROM node:18 AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Final image
FROM python:3.11-slim
WORKDIR /app

# Avoid buffering and configure headless defaults
ENV PYTHONUNBUFFERED=1 \
    HEADLESS=true \
    KIDUM_USERNAME=dummy \
    KIDUM_PASSWORD=dummy

# Install Python dependencies and Playwright browsers
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

# Copy application code and built frontend
COPY app ./app
COPY automation ./automation
COPY ui ./ui
COPY --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 8765
CMD ["python", "-m", "app.main"]
