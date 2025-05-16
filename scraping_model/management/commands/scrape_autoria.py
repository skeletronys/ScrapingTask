from django.core.management.base import BaseCommand
from scraping_model.scraper_autoria import scrape_autoria


class Command(BaseCommand):
    help = "Scrape AutoRia"

    def handle(self, *args, **kwargs):
        scrape_autoria()
        self.stdout.write(self.style.SUCCESS("Scraping done!"))
