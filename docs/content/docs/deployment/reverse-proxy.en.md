---
title: Reverse Proxy (HTTPS)
weight: 6
---

Vectora doesn't terminate TLS on its own — in production, put a reverse proxy in front of it.

## Nginx (minimal example)

```nginx
server {
    listen 443 ssl;
    server_name vectora.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/vectora.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vectora.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # required for the chat's SSE streaming and the terminal's WebSocket
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }

    location /vectora.terminal.v1/ws {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Important points: **disable buffering** (`proxy_buffering off`) so it doesn't break the chat's SSE streaming, and configure connection upgrade for the terminal's WebSocket.

## Traefik / Caddy

Any proxy that supports WebSocket + unbuffered SSE works the same way — the requirement is identical: pass through `Upgrade`/`Connection` and don't buffer streaming responses.

## Cookies

Session cookies (`httpOnly`, `SameSite=Lax`) get the `Secure` flag automatically when Vectora detects it's behind TLS.
