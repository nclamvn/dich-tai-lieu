# Docker Deployment Guide

## Quick Start

### Development
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build

# Access application
open http://localhost:3001/ui
```

### Production
```bash
# Create .env file with API keys
cp .env.example .env
# Edit .env with your API keys

# Start production environment
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| app | 3001 | Main FastAPI application |
| redis | 6379 | Rate limiting & caching |
| nginx | 80/443 | Reverse proxy (production) |

## Environment Variables

Create a `.env` file with:

```env
# Required API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional API Keys
DEEPSEEK_API_KEY=
GOOGLE_API_KEY=
MATHPIX_APP_ID=
MATHPIX_APP_KEY=

# Application Settings
PORT=3001
RATE_LIMIT=60/minute
JWT_SECRET_KEY=your-secret-key-here

# Redis
REDIS_URL=redis://redis:6379/0
```

## Production Deployment

### With SSL (Recommended)
1. Place SSL certificates in `docker/nginx/ssl/`:
   - `fullchain.pem`
   - `privkey.pem`

2. Start with production profile:
```bash
docker-compose --profile production up -d
```

### Without SSL (Development only)
```bash
docker-compose up -d app redis
```

## Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service]

# Restart a service
docker-compose restart app

# Scale workers
docker-compose up -d --scale app=3

# Clean up
docker-compose down -v --rmi all
```

## Volumes

| Volume | Description |
|--------|-------------|
| app_data | SQLite databases (jobs, users) |
| app_outputs | Generated documents |
| app_logs | Application logs |
| redis_data | Redis persistence |

## Health Checks

```bash
# Check app health
curl http://localhost:3001/health

# Check Redis
docker-compose exec redis redis-cli ping
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs app

# Check for port conflicts
lsof -i :3001
```

### Permission issues
```bash
# Fix data directory permissions
docker-compose exec app chown -R appuser:appuser /app/data
```

### Memory issues
```bash
# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G
```
