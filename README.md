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

## API

Документация – `/api/docs`, схема – `/api/openapi.json`.
Аутентификация: `POST /api/auth/login` возвращает JWT, дальше `Authorization: Bearer <токен>`.

Новый аккаунт получает роль `other` (только чтение). Роль, указанная при регистрации, становится **заявкой**; права выдаёт модератор через `POST /api/users/{id}/role-request/approve`.

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
