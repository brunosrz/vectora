# HTTPS no Vectora — acesso remoto com Secure Context

Acessar o chat web por IP (`http://100.x.x.x:8080` via Tailscale, ou
`http://192.168.x.x` na LAN) funciona, mas o browser **não** considera a
origem um _Secure Context_: APIs como `crypto.randomUUID`, clipboard
assíncrono e service worker (PWA) ficam indisponíveis ou degradadas.
Há três formas de servir o Vectora em HTTPS, da mais simples à mais
"produção".

## Opção 1 — `tailscale serve` (zero configuração, recomendada p/ Tailscale)

O Tailscale faz o TLS por você, com certificado Let's Encrypt automático
para o nome da máquina na tailnet (`https://<maquina>.<tailnet>.ts.net`):

```powershell
# uma vez (precisa de HTTPS habilitado no admin console da tailnet):
tailscale serve --bg 8080
```

Pronto: `https://<maquina>.<tailnet>.ts.net` proxyia para
`http://localhost:8080` com certificado válido em qualquer dispositivo da
tailnet. Nenhuma mudança no Vectora. Para desligar: `tailscale serve --bg off`.

## Opção 2 — TLS nativo do Vectora (`--ssl-certfile`/`--ssl-keyfile`)

O servidor web aceita certificado e chave PEM e sobe direto em `https://`:

```powershell
vectora server web --ssl-certfile C:\certs\fullchain.pem --ssl-keyfile C:\certs\key.pem
```

Ou via ambiente (`~/.vectora/.env`):

```ini
SSL_CERTFILE=C:\certs\fullchain.pem
SSL_KEYFILE=C:\certs\key.pem
```

De onde tirar o certificado:

- **Tailscale** — `tailscale cert <maquina>.<tailnet>.ts.net` gera
  `<nome>.crt` + `<nome>.key` (Let's Encrypt via DNS-01, sem expor porta).
  Acesse pelo nome ts.net, não pelo IP — certificado é por hostname.
- **mkcert** — para LAN/dev: `mkcert -install && mkcert 192.168.0.10 localhost`
  gera um certificado confiado nas máquinas onde a CA do mkcert for instalada.
- **Let's Encrypt/certbot** — para domínio público com portas 80/443
  alcançáveis (deploy em VPS).

## Opção 3 — Reverse proxy (Caddy/Traefik/nginx)

Para deploys Docker, o `Caddy` renova Let's Encrypt sozinho com 2 linhas:

```caddyfile
vectora.seudominio.com {
    reverse_proxy localhost:8080
}
```

(Traefik no docker-compose tem o mesmo efeito via labels.)

## Observações

- O certificado vale para o **hostname**, não para o IP — depois de
  configurar, acesse `https://<nome>` (ts.net, domínio ou nome do mkcert).
- O fallback `safeRandomUUID` do chat cobre `crypto.randomUUID` em contexto
  inseguro, mas PWA/clipboard/notificações continuam precisando de HTTPS.
