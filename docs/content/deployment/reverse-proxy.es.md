---
title: Reverse Proxy (HTTPS)
weight: 6
---

Vectora no termina TLS por sí mismo — en producción, pon un reverse proxy al frente.

## Nginx (ejemplo mínimo)

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

        # requerido para el streaming SSE del chat y el WebSocket de la terminal
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

Puntos importantes: **desactiva el buffering** (`proxy_buffering off`) para que no rompa el streaming SSE del chat, y configura la actualización de conexión para el WebSocket de la terminal.

## Traefik / Caddy

Cualquier proxy que soporte WebSocket + SSE sin buffer funciona igual — el requisito es idéntico: pasar `Upgrade`/`Connection` y no bufferizar las respuestas de streaming.

## Cookies

Las cookies de sesión (`httpOnly`, `SameSite=Lax`) reciben la flag `Secure` automáticamente cuando Vectora detecta que está detrás de TLS.
