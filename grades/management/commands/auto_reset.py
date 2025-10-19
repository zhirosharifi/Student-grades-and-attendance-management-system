from django.core.management.base import BaseCommand
from django.utils import timezone
from grades.models import Attendance, AttendanceHistory, GradebookEntry, GradebookEntryHistory


class Command(BaseCommand):
    help = 'Archive attendance and gradebook entries and reset them (intended to run every 12 hours).'

    def add_arguments(self, parser):
        parser.add_argument('--class-id', type=int, default=None, help='Limit reset to a single class id')
        parser.add_argument('--attendance-only', action='store_true', help='Only reset attendance')
        parser.add_argument('--gradebook-only', action='store_true', help='Only reset gradebook entries')

    def handle(self, *args, **options):
        class_id = options.get('class_id')
        attendance_only = options.get('attendance_only')
        gradebook_only = options.get('gradebook_only')

        now = timezone.now()

        if not gradebook_only:
            qs = Attendance.objects.all()
            if class_id:
                qs = qs.filter(student__classroom_id=class_id)
            items = list(qs)
            AttendanceHistory.objects.bulk_create([
                AttendanceHistory(
                    student=i.student,
                    date=i.date,
                    date_jalali=i.date_jalali,
                    present=i.present,
                ) for i in items
            ])
            qs.delete()
            self.stdout.write(self.style.SUCCESS(f"Attendance reset archived at {now} (count={len(items)})"))

        if not attendance_only:
            qs2 = GradebookEntry.objects.all()
            if class_id:
                qs2 = qs2.filter(student__classroom_id=class_id)
            items2 = list(qs2)
            GradebookEntryHistory.objects.bulk_create([
                GradebookEntryHistory(
                    student=i.student,
                    subject=i.subject,
                    entry_type=i.entry_type,
                    value=i.value,
                    date=i.date,
                    date_jalali=i.date_jalali,
                    notes=i.notes,
                ) for i in items2
            ])
            qs2.delete()
            self.stdout.write(self.style.SUCCESS(f"Gradebook reset archived at {now} (count={len(items2)})"))


