# Gomoku Online — Telegram Mini App

Онлайн мультиплеер Gomoku (5 в ряд) на 19×19 доске.

## Структура

```
gomoku/
├── index.html   — фронтенд (single-file, Telegram WebApp SDK)
├── server.py    — Python WebSocket сервер
└── README.md
```

## Локальный запуск

```bash
# 1. Установи зависимость
pip install websockets

# 2. Запусти сервер
python server.py
# → ws://localhost:8765

# 3. Открой index.html в браузере
# (или раздай через любой HTTP-сервер)
python -m http.server 3000
# → http://localhost:3000/index.html
```

В `index.html` WebSocket URL задаётся переменной:
```js
const WS_URL = 'ws://localhost:8765';
```

## Деплой на Fly.io

### 1. Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install websockets
COPY server.py .
EXPOSE 8765
CMD ["python", "server.py"]
```

### 2. fly.toml

```toml
app = "gomoku-miss41"
primary_region = "ams"

[build]

[http_service]
  internal_port = 8765
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[services]]
  protocol = "tcp"
  internal_port = 8765

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.ports]]
    port = 80
    handlers = ["http"]
```

### 3. Деплой

```bash
fly launch --name gomoku-miss41
fly deploy
```

### 4. Фронтенд — обнови WS_URL

```js
const WS_URL = 'wss://gomoku-miss41.fly.dev';
```

`index.html` можно захостить на GitHub Pages, Cloudflare Pages, или прямо в Telegram Mini App через BotFather → Web App URL.

## Telegram Mini App

1. BotFather → `/newapp` (или `/setmenubutton`)
2. URL: `https://your-pages-domain.com/gomoku/index.html`
3. WebSocket: `wss://gomoku-miss41.fly.dev`
