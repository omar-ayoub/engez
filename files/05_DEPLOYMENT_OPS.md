# Deployment & Operations — VPS Production Setup

## Target Infrastructure

- **VPS Provider:** Your existing VPS
- **OS:** Ubuntu 24.04 LTS
- **Architecture:** Single-server Docker Compose (scales to multi-server later)
- **Domain:** Your domain with Cloudflare DNS (recommended for DDoS + CDN)

---

## Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal
    # No port exposure — only accessible within Docker network

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    restart: always
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      R2_ACCOUNT_ID: ${R2_ACCOUNT_ID}
      R2_ACCESS_KEY: ${R2_ACCESS_KEY}
      R2_SECRET_KEY: ${R2_SECRET_KEY}
      R2_BUCKET: ${R2_BUCKET}
      R2_PUBLIC_URL: ${R2_PUBLIC_URL}
      VAPID_PRIVATE_KEY: ${VAPID_PRIVATE_KEY}
      VAPID_PUBLIC_KEY: ${VAPID_PUBLIC_KEY}
      VAPID_CLAIMS_EMAIL: ${VAPID_CLAIMS_EMAIL}
      ENVIRONMENT: production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - internal
    # Uvicorn with multiple workers for production
    command: >
      uvicorn app.main:app
      --host 0.0.0.0
      --port 8000
      --workers 4
      --log-level info
      --access-log

  nginx:
    image: nginx:1.27-alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/var/www/frontend:ro
      - certbot_certs:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
    depends_on:
      - api
    networks:
      - internal
      - external

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_certs:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  pgdata:
  redisdata:
  certbot_certs:
  certbot_www:

networks:
  internal:
    driver: bridge
  external:
    driver: bridge
```

---

## Production Backend Dockerfile

Create `backend/Dockerfile.prod`:

```dockerfile
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 libzbar-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

COPY . .

# Security: non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 15M; # Receipt images + voice recordings

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript
               application/wasm image/svg+xml;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-XSS-Protection "0" always;

    include /etc/nginx/conf.d/*.conf;
}
```

Create `nginx/conf.d/app.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Frontend (PWA static files)
    location / {
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;

        # Cache static assets aggressively (PWA controls freshness via service worker)
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Service worker must not be cached
        location = /sw.js {
            expires -1;
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }

        # Manifest must not be aggressively cached
        location = /manifest.webmanifest {
            expires 1h;
        }
    }

    # API proxy
    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for future real-time features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for AI processing (voice + receipt)
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

---

## VPS Initial Setup Script

```bash
#!/bin/bash
# Run on fresh Ubuntu 24.04 VPS

set -euo pipefail

# 1. System updates
apt update && apt upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# 3. Install Docker Compose plugin
apt install -y docker-compose-plugin

# 4. Firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (redirect to HTTPS)
ufw allow 443/tcp   # HTTPS
ufw --force enable

# 5. Fail2ban for SSH protection
apt install -y fail2ban
systemctl enable fail2ban

# 6. Create app directory
mkdir -p /opt/masrouf
cd /opt/masrouf

# 7. Clone repository (or scp files)
# git clone your-repo .

# 8. Create .env file
cat > .env << 'ENVEOF'
POSTGRES_DB=masrouf
POSTGRES_USER=masrouf
POSTGRES_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
REDIS_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
SECRET_KEY=CHANGE_THIS_64_CHAR_RANDOM_STRING
OPENAI_API_KEY=sk-your-key
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY=your-access-key
R2_SECRET_KEY=your-secret-key
R2_BUCKET=masrouf-receipts
R2_PUBLIC_URL=https://receipts.your-domain.com
VAPID_PRIVATE_KEY=your-vapid-private
VAPID_PUBLIC_KEY=your-vapid-public
VAPID_CLAIMS_EMAIL=admin@your-domain.com
ENVEOF

chmod 600 .env

# 9. Build and start
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 10. SSL certificate
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d your-domain.com --email admin@your-domain.com --agree-tos

# 11. Reload nginx to use certs
docker compose -f docker-compose.prod.yml restart nginx

# 12. Run migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## Deployment Workflow (From Windows Dev Machine)

```powershell
# 1. Build frontend
cd frontend
pnpm build  # Output in frontend/dist/

# 2. Deploy to VPS (using rsync or scp)
scp -r frontend/dist/ user@your-vps:/opt/masrouf/frontend/dist/
scp -r backend/ user@your-vps:/opt/masrouf/backend/

# 3. SSH into VPS and rebuild
ssh user@your-vps
cd /opt/masrouf
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## Database Backup (Cron Job on VPS)

```bash
# Add to crontab -e
0 3 * * * docker exec masrouf-postgres-1 pg_dump -U masrouf masrouf | gzip > /opt/backups/masrouf_$(date +\%Y\%m\%d).sql.gz

# Retain 30 days
0 4 * * * find /opt/backups -name "masrouf_*.sql.gz" -mtime +30 -delete
```

---

## Monitoring Checklist

- [ ] Docker containers auto-restart on failure (`restart: always`)
- [ ] PostgreSQL healthchecks prevent API from starting before DB is ready
- [ ] Certbot auto-renews SSL certificates every 12 hours
- [ ] Fail2ban protects SSH from brute force
- [ ] UFW firewall only allows ports 22, 80, 443
- [ ] `.env` file has restrictive permissions (600)
- [ ] Database backups run daily at 3 AM
- [ ] Nginx client_max_body_size allows receipt uploads (15MB)
- [ ] API proxy timeout handles AI processing (60s)
- [ ] Service worker file is never cached by Nginx
