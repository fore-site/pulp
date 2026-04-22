# --- STAGE 1: Build Node.js assets ---
FROM node:18-alpine AS node-builder
WORKDIR /build

# Copy only package files first to leverage Docker cache
COPY theme/static_src/package*.json ./
RUN npm install

# Copy the rest of the theme source and build
COPY theme/static_src .
RUN npm run build

# --- STAGE 2: Final Django image ---
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project files
COPY . .

# Pull the copied assets from the node stage
COPY --from=node-builder /build/static/css ./theme/static/css

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Gunicorn runs on
EXPOSE 8000

# Start the application using Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]