# AI Publisher Pro — Deployment Guide

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 22.04 / any Linux | Ubuntu 24.04 LTS |
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB | 50 GB |
| Docker | 24+ | Latest |
| Docker Compose | v2 | Latest |

## Quick Start (5 minutes)

```bash
# 1. Clone
git clone https://github.com/your-org/ai-publisher-pro.git
cd ai-publisher-pro

# 2. Configure
cp .env.production .env
nano .env   # Set API keys and SESSION_SECRET

# 3. Deploy
bash deploy.sh

# 4. Access
# Backend API:  http://your-server:3000
# Frontend UI:  http://your-server:3001
# API Docs:     http://your-server:3000/docs
```

## Configuration

### Required Settings

Edit `.env` and set these values:

| Variable | Description | How to get |
|----------|-------------|------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | https://console.anthropic.com/ |
| `OPENAI_API_KEY` | OpenAI GPT API key | https://platform.openai.com/api-keys |
| `SESSION_SECRET` | Random 64-char string | `python3 -c "import secrets; print(secrets.token_hex(32))"` |

You need **at least one** AI API key. The system auto-selects the available provider.

### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | 3000 | Backend API port |
| `FRONTEND_PORT` | 3001 | Frontend UI port |
| `PROVIDER` | anthropic | Default AI: anthropic/openai/google/deepseek |
| `MAX_CONCURRENT_JOBS` | 10 | Max simultaneous translation jobs |
| `BUDGET_LIMIT_DAILY_USD` | 0 (unlimited) | Daily AI spend cap |
| `MAX_UPLOAD_SIZE_MB` | 50 | Max file upload size |
| `SECURITY_MODE` | production | development/internal/production |

See `.env.production` for full list with comments.

## Daily Operations

### View Logs

```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail 100 backend
```

### Restart

```bash
docker compose restart          # Restart all
docker compose restart backend  # Backend only
```

### Stop

```bash
docker compose down             # Stop all
docker compose down -v          # Stop + remove volumes (DESTROYS DATA)
```

## Backup & Recovery

### Manual Backup

```bash
bash backup.sh
# Creates: backups/aipub_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Automated Daily Backup (crontab)

```bash
# Add to crontab: crontab -e
0 2 * * * cd /path/to/ai-publisher-pro && bash backup.sh >> /var/log/aipub-backup.log 2>&1
```

### Restore from Backup

```bash
# Stop services
docker compose down

# Extract backup
tar -xzf backups/aipub_backup_YYYYMMDD_HHMMSS.tar.gz -C /tmp/restore

# Copy data back
docker compose cp /tmp/restore/data backend:/app/data

# Restart
docker compose up -d
```

## Update to Latest Version

```bash
bash update.sh
# Automatically: backup → git pull → rebuild → restart → health check
```

## SSL with Nginx (Recommended for Production)

### Option 1: Use built-in nginx profile

```bash
# Place SSL certs
mkdir -p docker/nginx/ssl
cp fullchain.pem docker/nginx/ssl/
cp privkey.pem docker/nginx/ssl/

# Start with nginx
docker compose --profile ssl up -d
```

### Option 2: Let's Encrypt (free SSL)

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certs
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/

# Start with nginx
docker compose --profile ssl up -d

# Auto-renew (add to crontab)
0 0 1 * * certbot renew --quiet && docker compose restart nginx
```

### Firewall Setup

```bash
# Only expose port 443 (HTTPS) and 80 (redirect)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 3000/tcp   # Block direct backend access
sudo ufw deny 3001/tcp   # Block direct frontend access
sudo ufw enable
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker compose logs backend

# Common issues:
# - "SESSION_SECRET must be set" → Edit .env, set SESSION_SECRET
# - "No API keys configured" → Set at least one AI API key in .env
# - Port in use → Change BACKEND_PORT in .env
```

### Frontend can't connect to backend

```bash
# Check backend is healthy
curl http://localhost:3000/health

# Check frontend can reach backend
docker compose exec frontend wget -qO- http://backend:3000/health
```

### AI calls failing

```bash
# Check API keys are valid
curl http://localhost:3000/api/system/info

# Check provider status in logs
docker compose logs backend | grep "provider"
```

### Disk full

```bash
# Check disk usage
df -h
du -sh data/*

# Clean old jobs (keeps last 30 days by default)
docker compose exec backend python -c "
from api.aps_v2_service import get_v2_service
s = get_v2_service()
print(f'Cleared {s.clear_cache()} jobs')
"

# Clean Docker
docker system prune -f
```

### Health check

```bash
# Quick check
bash smoke-test.sh

# Detailed health
curl http://localhost:3000/api/health/detailed | python3 -m json.tool
```

## Security Checklist

Before exposing to the internet:

- [ ] Set `SECURITY_MODE=production` in `.env`
- [ ] Set strong `SESSION_SECRET` (64+ random chars)
- [ ] Set `SESSION_AUTH_ENABLED=true`
- [ ] Set `CSRF_ENABLED=true` and `CSRF_SECRET_KEY`
- [ ] Set `CORS_ORIGINS` to your domain
- [ ] Configure SSL (see above)
- [ ] Set up firewall (block direct 3000/3001 access)
- [ ] Set `BUDGET_LIMIT_DAILY_USD` to prevent runaway costs
- [ ] Set up automated backups (crontab)
- [ ] Set up log monitoring

## Architecture

```
                    ┌─────────────────┐
  Internet ────────>│  Nginx (SSL)    │ :443
                    │  (optional)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Frontend       │ :3001
                    │  (Next.js)      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Backend        │ :3000
                    │  (FastAPI)      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  SQLite DBs     │
                    │  (data volume)  │
                    └─────────────────┘
```
