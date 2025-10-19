from django.core.management.base import BaseCommand
from grades.models import Attendance, GradebookEntry

class Command(BaseCommand):
    help = 'Backfill date_jalali for Attendance and GradebookEntry records'

    def handle(self, *args, **options):
        a_qs = Attendance.objects.all()
        g_qs = GradebookEntry.objects.all()
        self.stdout.write(f'Processing {a_qs.count()} Attendance rows...')
        a_count = 0
        for a in a_qs:
            a.save()
            a_count += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {a_count} Attendance rows.'))

        self.stdout.write(f'Processing {g_qs.count()} GradebookEntry rows...')
        g_count = 0
        for g in g_qs:
            g.save()
            g_count += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {g_count} GradebookEntry rows.'))
