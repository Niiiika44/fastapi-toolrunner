# AutoRunning

Сервис загрузки и обработки тестовых данных блоков памяти ОС.
Пользователь загружает zip-файл тестового примера, сервис разбирает его в фоне, хранит и позволяет выгрузить интересующий набор данных.

**Стек:** Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Celery + RabbitMQ + Redis · MinIO/S3 · Docker

## Разработка

```bash
poetry install
cp .env.example .env && cp .env.docker.example .env.docker
docker compose up -d
```

```bash
poetry run pytest -q          # все тесты (нужен Docker)
poetry run pytest tests/unit -q
poetry run ruff check app/ tests/
```

## Фронтенд

SPA живёт в [`frontend/`] – React + TypeScript + Vite.

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173, бэкенд на :8000
```

Фронт ходит на относительный `/api`: в разработке путь проксирует Vite, в проде –
тот же nginx, что отдаёт статику. CORS поэтому не нужен.

## API

Документация – `/api/docs`, схема – `/api/openapi.json`.
Аутентификация: `POST /api/auth/login` возвращает JWT, дальше `Authorization: Bearer <токен>`.

Новый аккаунт получает роль `other` (только чтение). Роль, указанная при регистрации, становится **заявкой**; права выдаёт модератор через `POST /api/users/{id}/role-request/approve`.

## Аватарки

`GET /api/users/{id}/avatar` — **единственный эндпоинт без токена**: браузер не умеет слать
заголовки для `<img>`. С объектным хранилищем отвечает `302` на presigned-ссылку, с локальным
отдаёт байты. Несуществующий пользователь и пользователь без фото отвечают одинаково, чтобы по
открытому URL нельзя было проверять существование аккаунтов.

Ссылка на картинку приходит в поле `avatar_url` любого представления пользователя; `?v=` в ней
меняется при замене фото. Загрузка — `POST /api/users/{id}/avatar` (multipart, поле `file`),
удаление — `DELETE`. Формат определяется по сигнатуре файла, картинка перекодируется в
квадратный WebP.

## WebSocket: статус разбора

Единственная часть API, которой **нет в OpenAPI** – спецификация не описывает WebSocket.

```
wss://<host>/api/tests/{test_id}/status
```

**Авторизация**, два способа:

```
Authorization: Bearer <токен>                    # заголовок
Sec-WebSocket-Protocol: bearer, <токен>          # подпротокол, для браузерного API
```

Второй нужен потому, что браузерный `WebSocket` не позволяет задавать заголовки.

**События** — JSON-текст:

```json
{"event":"test.status","test_id":1,"status":"parsed","error_message":null,"ts":"..."}
{"event":"validation.status","test_id":1,"validation_id":3,"status":"completed","valid":true,"ts":"..."}
```

**Коды закрытия:**

| Код | Причина |
|---|---|
| 1000 | нормальное завершение |
| 1008 | нет токена или он недействителен |
| 1011 | внутренняя ошибка |
| 1013 | превышен лимит соединений на пользователя (`WS_MAX_CONNECTIONS_PER_USER`, по умолчанию 5) |
| 4401 | истёк срок действия токена |
| 4403 | недостаточно прав |
| 4404 | тест не найден |

Канал **молчит между событиями** – разбор может идти минутами. Прокси должен быть настроен на длинный `proxy_read_timeout`.
