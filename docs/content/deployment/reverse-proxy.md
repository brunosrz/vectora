---
title: Reverse Proxy (HTTPS)
weight: 6
---

O Vectora não termina TLS sozinho — em produção, coloque um reverse proxy na frente.

## Nginx (exemplo mínimo)

```nginx
server {
    listen 443 ssl;
    server_name vectora.seudominio.com;

    ssl_certificate     /etc/letsencrypt/live/vectora.seudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vectora.seudominio.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # necessário pro streaming SSE do chat e do terminal (WebSocket)
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

Pontos importantes: **desabilitar buffering** (`proxy_buffering off`) pra não quebrar o streaming SSE do chat, e configurar upgrade de conexão pro WebSocket do terminal.

## Traefik / Caddy

Qualquer proxy que suporte WebSocket + SSE sem buffer funciona igual — o requisito é o mesmo: repassar `Upgrade`/`Connection` e não bufferizar respostas de streaming.

## Cookies

Cookies de sessão (`httpOnly`, `SameSite=Lax`) recebem a flag `Secure` automaticamente quando o Vectora detecta que está atrás de TLS.
