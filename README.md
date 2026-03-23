# Tidal uptime

Сервис проверяет список Tidal API-эндпоинтов раз в 5 минут и отдает текущий снимок в JSON.
Каждый прогон сохраняется в SQLite.
При необходимости шлет алерты в Discord webhook и email-подписчикам.

Проверки для каждого URL:

1. `GET /` - endpoint должен вернуть JSON с `version`
2. `GET /search/?s=the weeknd` - endpoint должен вернуть непустой `data.items`
3. `GET /track/` - endpoint должен вернуть непустые `data.manifestHash` и `data.manifest`. Проверка идет по списку `track id`: `134858527`, `125155092`, `204567804`, с максимум 2 retry на другой `id`

Если проходит шаг 1, URL попадает в `api`.

Если проходит шаг 3, URL попадает в `streaming`. Для `/track/` сервис пробует до 3 разных `track id` и засчитывает первый успешный ответ.

Если URL падает на `search`, `track` или любой другой проверке, он попадает в `down` со статусом и краткой причиной. Один и тот же URL может одновременно быть в `api` и в `down`, если базовый API жив, но поиск или треки сломаны.

## Запуск через Docker

```bash
docker compose up --build -d
```

После запуска доступны:

- `http://localhost:8000/` - HTML dashboard
- `http://localhost:8000/status.json`

Из дашборда можно:

- добавлять новые API instances
- редактировать существующие URL
- удалять instances
- подписываться на email-алерты по конкретному API даже без авторизации
- из админки смотреть список всех email-подписок и удалять их

## Переменные окружения

- `CHECK_INTERVAL_SECONDS=300`
- `REQUEST_TIMEOUT_SECONDS=6`
- `DATABASE_PATH=data/uptime.db`
- `STATUS_PAGE_WINDOW_HOURS=8`
- `MAX_TRACK_RETRIES=2`
- `ADMIN_PASSWORD=change-me`
- `AUTH_COOKIE_SECRET=change-this-cookie-secret`
- `AUTH_COOKIE_MAX_AGE_SECONDS=604800`
- `APP_HOST=0.0.0.0`
- `APP_PORT=8000`
- `USER_AGENT=...`
- `SEARCH_QUERY=the weeknd`
- `DISCORD_WEBHOOK_URL=...`
- `DISCORD_ALERTS_ENABLED=true`
- `DISCORD_ALERT_USERNAME=Tidal Uptime`
- `DISCORD_ALERT_FAILURE_STREAK=2`
- `DISCORD_ALERT_RECOVERY_ENABLED=true`
- `DISCORD_ALERT_RECOVERY_STREAK=1`
- `DISCORD_ALERT_TRIGGER_STATES=outage,degraded`
- `DISCORD_ALERT_TRIGGER_PROBES=api,search,track`
- `EMAIL_ALERTS_ENABLED=true`

SMTP-настройки вынесены в отдельный файл `.smtp.toml`.

Список проверочных треков сейчас зашит в коде в [app/settings.py](c:\Users\dmitry\Desktop\tidal uptime\app\settings.py): `134858527`, `125155092`, `204567804`.

## Discord alerts

Алерт отправляется только если заполнен `DISCORD_WEBHOOK_URL` и включен `DISCORD_ALERTS_ENABLED=true`.
Для каждого endpoint alert отправляется только один раз за инцидент. Следующий alert по этому endpoint возможен только после восстановления.

Гибкая настройка:

- `DISCORD_ALERT_FAILURE_STREAK` - через сколько подряд неуспешных прогонов слать первый alert
- `DISCORD_ALERT_RECOVERY_ENABLED` - слать ли recovery после восстановления
- `DISCORD_ALERT_RECOVERY_STREAK` - сколько успешных прогонов подряд ждать перед recovery
- `DISCORD_ALERT_TRIGGER_STATES` - состояния для алертов: `outage`, `degraded`
- `DISCORD_ALERT_TRIGGER_PROBES` - какие именно проверки учитывать: `api`, `search`, `track`

Примеры:

- Только когда полностью умер API после 3 неудачных пингов подряд:
  `DISCORD_ALERT_TRIGGER_STATES=outage`
  `DISCORD_ALERT_TRIGGER_PROBES=api`
  `DISCORD_ALERT_FAILURE_STREAK=3`
- Когда важен любой деград, но без recovery:
  `DISCORD_ALERT_TRIGGER_STATES=outage,degraded`
  `DISCORD_ALERT_TRIGGER_PROBES=api,search,track`
  `DISCORD_ALERT_RECOVERY_ENABLED=false`

## Email subscriptions

На каждой карточке endpoint есть кнопка-колокольчик. Через нее любой пользователь может оставить email-подписку на алерты по конкретному API.

Подписка получает те же типы событий, которые разрешены для самого endpoint:

- `outage`
- `degraded`
- `recovery`

То есть если у endpoint выключены, например, `degraded` или `recovery`, по email они тоже не будут отправляться.

Чтобы email-алерты работали, нужно заполнить SMTP-настройки:

- основной флаг `EMAIL_ALERTS_ENABLED=true` остается в `.env`
- SMTP-параметры лежат в `.smtp.toml`
- поддерживаются `SMTP_FROM_NAME`, `SMTP_REPLY_TO` и `SMTP_MESSAGE_STREAM_HEADER`
- `SMTP_USE_STARTTLS=true` для обычного SMTP с STARTTLS
- `SMTP_USE_SSL=true` если нужен SMTPS сразу по TLS

Пример `.smtp.toml` для Postmark:

```toml
smtp_host = "smtp-broadcasts.postmarkapp.com"
smtp_port = 587
smtp_username = "..."
smtp_password = "..."
smtp_from_name = "Spotisaver"
smtp_from_email = "hi@spotisaver.online"
smtp_reply_to = "hi@spotisaver.online"
smtp_message_stream_header = "X-PM-Message-Stream: broadcast"
smtp_use_starttls = true
smtp_use_ssl = false
smtp_timeout_seconds = 10
```

Список всех подписок доступен только после авторизации в отдельном popup `Subscriptions`, там же можно удалить любую подписку.

Шкала на дашборде по умолчанию показывает последние `8` часов. Количество колонок рассчитывается автоматически из `STATUS_PAGE_WINDOW_HOURS` и `CHECK_INTERVAL_SECONDS`.

SQLite-файл по умолчанию создается в `data/uptime.db`. В `docker-compose.yml` эта папка примонтирована как `./data:/app/data`, так что история переживает перезапуски контейнера.

## Хранение

- SQLite работает в режиме `WAL`
- детальный статус хранится только для последнего прогона
- история uptime хранится компактно: по `endpoint_id + poll_run_id + state`, без дублирования длинных URL и ошибок в каждой historical записи
- старые прогоны автоматически подрезаются по `HISTORY_RETENTION_RUNS`
- состояние алертов хранится отдельно, чтобы после рестарта контейнера не слать лишние дубли
- email-подписки хранятся в SQLite и удаляются автоматически, если сам endpoint удален
