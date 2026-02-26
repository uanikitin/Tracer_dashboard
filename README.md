# Tracer Dashboard

Система учёта отбора проб с Telegram-ботом и веб-дашбордом.

## Обзор

Tracer Dashboard — это модульное приложение для:
- Создания событий "Отбор проб" через Telegram-бота или Mini App
- Ведения справочников участков и скважин
- Отображения данных на веб-дашборде с картой и таблицами
- Уведомлений в Telegram-группу

## Архитектура

```
app/
├── main.py              # FastAPI entry point
├── core/                # Config, security, logging
├── db/                  # SQLAlchemy models, session
├── services/            # Business logic
├── api/v1/              # REST API routers
├── telegram_bot/        # aiogram handlers
└── web/                 # Jinja2 templates, static
    ├── templates/
    └── static/
alembic/                 # Database migrations
tests/                   # Pytest tests
docker/                  # Docker configs
```

## Технологии

- **Python 3.11+**
- **FastAPI** — web framework + API
- **aiogram 3** — Telegram bot + Mini App
- **SQLAlchemy 2.x (async)** — ORM
- **PostgreSQL** — база данных (Render)
- **Alembic** — миграции
- **Jinja2 + Leaflet.js** — веб-интерфейс

### Решения по архитектуре

1. **Async SQLAlchemy** — выбран для лучшей интеграции с FastAPI и aiogram, оба из которых async.
2. **Jinja2 вместо SPA** — простой старт без сложности React/Vue, достаточно для MVP.
3. **JWT + Telegram initData** — двойная авторизация: JWT для web, initData для Mini App.

## Быстрый старт

### 1. Клонирование и настройка

```bash
cd Tracer_dashboard

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .venv\Scripts\activate  # Windows

# Установить зависимости
pip install -e ".[dev]"
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактировать .env
```

Обязательные переменные:
- `DATABASE_URL` — PostgreSQL connection string
- `BOT_TOKEN` — Telegram bot token от @BotFather
- `TELEGRAM_GROUP_CHAT_ID` — ID группы для уведомлений
- `SECRET_KEY` — секретный ключ для JWT

### 3. Создание бота в Telegram

1. Перейдите к @BotFather
2. Создайте нового бота: `/newbot`
3. Сохраните токен в `.env` как `BOT_TOKEN`
4. Настройте Mini App: `/newapp` → выберите бота → укажите URL

### 4. База данных

#### Локально с Docker:

```bash
docker-compose up -d db
```

#### Миграции:

```bash
# Применить миграции
alembic upgrade head

# Создать новую миграцию (после изменения моделей)
alembic revision --autogenerate -m "description"
```

### 5. Запуск

#### Локально:

```bash
# Режим разработки
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Docker:

```bash
docker-compose up --build
```

Приложение будет доступно по адресу: http://localhost:8000

## API Endpoints

### Авторизация
- `POST /api/v1/auth/telegram` — авторизация через Telegram initData
- `GET /api/v1/auth/me` — информация о текущем пользователе

### Участки
- `GET /api/v1/sites` — список участков
- `GET /api/v1/sites/{id}` — детали участка
- `POST /api/v1/sites` — создать участок (admin)
- `POST /api/v1/sites/webapp` — создать из Mini App

### Скважины
- `GET /api/v1/wells` — список скважин
- `GET /api/v1/wells?site_id=1` — скважины участка
- `POST /api/v1/wells` — создать скважину (admin)
- `POST /api/v1/wells/webapp` — создать из Mini App

### Пробы
- `GET /api/v1/sampling` — список событий с фильтрами
- `POST /api/v1/sampling` — создать событие
- `POST /api/v1/sampling/webapp` — создать из Mini App

## Web Dashboard

- `/` — главная страница
- `/map` — карта скважин (Leaflet.js)
- `/sites` — список участков
- `/sites/{id}` — детали участка
- `/samples` — таблица проб с фильтрами

## Telegram Bot

### Команды
- `/start` — начало работы, регистрация
- `/sample` — начать отбор пробы
- `/sites` — список участков
- `/wells` — список скважин
- `/help` — справка

### Mini App
Кнопка "Отбор пробы" открывает пошаговую форму:
1. Выбор/создание участка
2. Выбор/создание скважины
3. Состояние скважины
4. GPS координаты
5. Тип пробы
6. Объём и примечание
7. Подтверждение

## Деплой на Render

### 1. Создать PostgreSQL

1. Dashboard → New → PostgreSQL
2. Сохранить Internal Database URL

### 2. Создать Web Service

1. Dashboard → New → Web Service
2. Connect repository
3. Settings:
   - Runtime: Python 3
   - Build Command: `pip install .`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3. Переменные окружения

```
DATABASE_URL=<Internal Database URL>
BOT_TOKEN=<your_bot_token>
TELEGRAM_GROUP_CHAT_ID=<group_id>
SECRET_KEY=<random_secret>
APP_ENV=production
APP_URL=https://your-app.onrender.com
WEBAPP_URL=https://your-app.onrender.com/webapp
USE_WEBHOOK=true
TELEGRAM_WEBHOOK_URL=https://your-app.onrender.com/api/v1/telegram/webhook
```

### 4. Миграции

При первом деплое или изменении схемы:

```bash
# Локально с production DATABASE_URL
alembic upgrade head
```

Или добавить в Build Command:
```
pip install . && alembic upgrade head
```

## Тестирование

```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Только определённый файл
pytest tests/test_services.py -v
```

## RBAC (Роли)

- **USER** — создание событий, просмотр данных
- **ADMIN** — управление справочниками (участки, скважины), удаление событий

Первый админ назначается вручную в БД:
```sql
UPDATE users SET role = 'admin' WHERE telegram_id = 123456789;
```

## Расширение

### Добавление нового модуля

1. Создать модели в `app/db/models.py`
2. Создать миграцию: `alembic revision --autogenerate -m "add feature"`
3. Создать сервис в `app/services/`
4. Создать API роутер в `app/api/v1/`
5. Подключить роутер в `app/api/v1/__init__.py`
6. Добавить страницы в `app/web/templates/pages/`

### Добавление Telegram команды

1. Создать handler в `app/telegram_bot/handlers/`
2. Подключить роутер в `app/telegram_bot/bot.py`

## Лицензия

MIT
