import os
import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Creates a dump of the database into the dumps folder'

    def handle(self, *args, **options):
        now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        project_root = settings.BASE_DIR
        dumps_dir = os.path.join(project_root, 'dumps')
        os.makedirs(dumps_dir, exist_ok=True)
        out_file = os.path.join(dumps_dir, f'dump_{now}.json')
        os.system(f'python manage.py dumpdata --natural-primary --natural-foreign --indent 2 > "{out_file}"')
        self.stdout.write(self.style.SUCCESS(f'Dump created: {out_file}'))
