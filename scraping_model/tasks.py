import os
from datetime import datetime
from celery import shared_task
from scraping_model.scraper_autoria import scrape_autoria

@shared_task
def run_scraper_task():
    scrape_autoria()

@shared_task
def dump_db_task():
    db_name = os.environ.get('DB_NAME')
    db_user = os.environ.get('DB_USER')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_pass = os.environ.get('DB_PASSWORD')

    dump_dir = os.path.join(os.getcwd(), 'dumps')
    os.makedirs(dump_dir, exist_ok=True)
    filename = f"dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    dump_path = os.path.join(dump_dir, filename)

    os.environ['PGPASSWORD'] = db_pass

    cmd = f'pg_dump -h {db_host} -U {db_user} -d {db_name} -p {db_port} > "{dump_path}"'
    print(f"[Celery] Running: {cmd}")
    exit_code = os.system(cmd)
    if exit_code == 0:
        print(f"[Celery] Dump saved to {dump_path}")
    else:
        print("[Celery] Dump failed!")

    return dump_path if exit_code == 0 else None