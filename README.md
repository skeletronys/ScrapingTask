
# AutoRia Scraper

## Опис

Це Django-додаток для автоматичного скрапінгу платформи [AutoRia](https://auto.ria.com/car/used/) по всіх сторінках з вживаними авто. 
Система щодня в заданий час збирає дані, зберігає у PostgreSQL, не допускає дублів, і автоматично створює резервні копії (дампи) бази у папці `dumps/`.

---

## Структура проекту

```
.
├── auto_ria_scraper/          # Django settings, celery.py
├── scraping_model/            # Ваш додаток, моделі, таски Celery
├── dumps/                     # Сюди зберігаються дампи БД
├── manage.py
├── requirements.txt
├── README.md
├── .env.sample                # Зразок файлу для налаштувань
```

---

## Встановлення і запуск

### 1. Клонування репозиторію

```bash
git clone https://github.com/yourusername/auto_ria_scraper.git
cd auto_ria_scraper
```

### 2. Встановлення залежностей

> Віртуальне середовище рекомендується

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

### 3. Налаштування .env

- Створи файл `.env` у корені проекту за прикладом `.env.sample` і заповни свої дані для БД, Redis та інших налаштувань.

**Приклад .env:**
```
DB_NAME=neondb
DB_USER=neondb_owner
DB_PASSWORD=your_password
DB_HOST=your_db_host
DB_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

SCRAPER_NUM_PAGES=5
SCRAPER_NUM_WORKERS=8
USE_SQLITE=False
```

---

### 4. Міграції

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 5. Запуск Redis

**Обов'язково!**  
Потрібно, щоб у тебе локально працював Redis (або зміни на свій хост у .env):

```bash
redis-server
```

---

### 6. Запуск Celery

**Worker:**
```bash
celery -A auto_ria_scraper worker --loglevel=info --pool=solo
```
**Beat (щоб працював розклад):**
```bash
celery -A auto_ria_scraper beat --loglevel=info
```
> Запускай обидва процеси **одночасно** (окремі консолі).

---

### 7. Ручний запуск скрейпінгу

У Django shell:
```python
from scraping_model.tasks import run_scraper_task
run_scraper_task.delay()
```

---

### 8. Ручний дамп БД

У Django shell:
```python
from scraping_model.tasks import dump_db_task
dump_db_task.delay()
```
**Або** почекай на запуск Celery Beat — дамп створиться автоматично згідно розкладу (12:00 щодня, змінюється у settings.py).

---

### 9. Де зберігаються дампи?

- Дампи автоматично потрапляють у папку `dumps/`
- Кожен дамп має унікальну дату й час у назві.

---

## Структура БД

Всі зібрані дані зберігаються у моделі `Car`:

- **url** (string)
- **title** (string)
- **price_usd** (number)
- **odometer** (number)
- **username** (string)
- **phone_number** (string)
- **image_url** (string)
- **images_count** (number)
- **car_number** (string)
- **car_vin** (string)
- **datetime_found** (datetime)

---

## Залежності

Усі потрібні залежності у `requirements.txt`, основні з них:
- Django
- Celery
- redis
- psycopg2-binary
- requests
- beautifulsoup4
- selenium
- python-dotenv
- environs
- jazzmin

---

## Логування

- Використовується стандартний print/logging (можна підключити логування у файл).
- Вся інформація про роботу тасків — у celery worker.

---

## Рекомендації

- **Папку `dumps/` додай до `.gitignore`** — не заливай дампи у репозиторій.
- `.env` — не заливай у публічний доступ! Лише `.env.sample`.

---
