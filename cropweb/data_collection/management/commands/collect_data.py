# management/commands/collect_data.py
from django.core.management.base import BaseCommand
from ...data_collector import collect_data

class Command(BaseCommand):
    help = "Run the data collection script."

    def handle(self, *args, **kwargs):
        if collect_data():
            self.stdout.write(self.style.SUCCESS("Data collection completed successfully."))
        else:
            self.stdout.write(self.style.ERROR("Data collection failed."))

