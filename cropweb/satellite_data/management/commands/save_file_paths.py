# management/commands/save_file_paths.py
from django.core.management.base import BaseCommand
from ...utils import save_file_paths_to_db

class Command(BaseCommand):
    help = "Save file paths to the database."

    def handle(self, *args, **kwargs):
        save_file_paths_to_db()
        self.stdout.write(self.style.SUCCESS("File paths saved to the database."))
