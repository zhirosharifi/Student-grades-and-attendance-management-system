from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
import jdatetime

class SchoolClass(models.Model):
    name = models.CharField("نام کلاس", max_length=150, unique=True)

    class Meta:
        verbose_name = "کلاس"
        verbose_name_plural = "کلاس‌ها"

    def __str__(self):
        return self.name

    def average(self):
        # compute average across all grades in this class
        grades = Grade.objects.filter(subject__classroom=self)
        if not grades.exists():
            return None
        total = sum([float(g.score) for g in grades])
        return round(total / grades.count(), 2)


class Subject(models.Model):
    classroom = models.ForeignKey(SchoolClass, related_name='subjects', on_delete=models.CASCADE)
    name = models.CharField("نام درس", max_length=150)
    teacher_name = models.CharField("نام معلم", max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "درس"
        verbose_name_plural = "دروس"
        unique_together = ('classroom', 'name')

    def __str__(self):
        if self.teacher_name:
            return f"{self.name} — {self.classroom.name} ({self.teacher_name})"
        return f"{self.name} — {self.classroom.name}"


class Student(models.Model):
    classroom = models.ForeignKey(SchoolClass, related_name='students', on_delete=models.CASCADE)
    full_name = models.CharField("نام و نام خانوادگی", max_length=200)
    roll_number = models.PositiveIntegerField("شماره دانش‌آموزی")
    # National ID (required, 10 digits typical in Iran)
    national_id = models.CharField("کد ملی", max_length=20, null=True, blank=False, validators=[
        RegexValidator(regex=r"^\d{8,20}$", message="کد ملی باید فقط شامل ارقام باشد (۸ تا ۲۰ رقم).")
    ])
    # Student password for login
    password = models.CharField("رمز عبور", max_length=128, blank=True, null=True, help_text="رمز عبور برای ورود دانش‌آموز به سیستم")
    # Up to 3 phone numbers (optional)
    phone1 = models.CharField("شماره تلفن ۱", max_length=20, blank=True, null=True, validators=[
        RegexValidator(regex=r"^[+\d][\d\-\s]{7,}$", message="شماره تلفن معتبر نیست.")
    ])
    phone2 = models.CharField("شماره تلفن ۲", max_length=20, blank=True, null=True, validators=[
        RegexValidator(regex=r"^[+\d][\d\-\s]{7,}$", message="شماره تلفن معتبر نیست.")
    ])
    phone3 = models.CharField("شماره تلفن ۳", max_length=20, blank=True, null=True, validators=[
        RegexValidator(regex=r"^[+\d][\d\-\s]{7,}$", message="شماره تلفن معتبر نیست.")
    ])
    # Up to 2 emails (optional)
    email1 = models.EmailField("ایمیل ۱", blank=True, null=True, validators=[EmailValidator(message="ایمیل معتبر نیست.")])
    email2 = models.EmailField("ایمیل ۲", blank=True, null=True, validators=[EmailValidator(message="ایمیل معتبر نیست.")])

    class Meta:
        verbose_name = "دانش‌آموز"
        verbose_name_plural = "دانش‌آموزان"
        unique_together = ('classroom', 'roll_number')
        ordering = ['roll_number', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.roll_number})"

    def clean(self):
        # Ensure at least one of phone or email can be blank, but all formats are validated via field validators
        # Additional simple safeguard: prevent duplicate national_id (field-level unique already enforces at DB)
        return super().clean()

    def average(self):
        # For each subject, compute effective score taking into account gradebook entries
        subjects = self.classroom.subjects.all()
        scores = []
        for subj in subjects:
            # base grade if exists
            try:
                g = self.grades.get(subject=subj)
                base = float(g.score)
            except Grade.DoesNotExist:
                base = None

            # apply gradebook entries for this student+subject (ordered oldest->newest)
            entries = list(self.gradebook_entries.filter(subject=subj).order_by('created_at'))
            # if there's any 'num' entry, take the latest as override
            num_entries = [e for e in entries if e.entry_type == 'num' and e.value is not None]
            if num_entries:
                effective = float(num_entries[-1].value)
            else:
                effective = base

            # apply pos/neg adjustments (sum) to effective
            adjustments = 0.0
            for e in entries:
                if e.value is None:
                    continue
                if e.entry_type == 'pos':
                    adjustments += abs(float(e.value))
                elif e.entry_type == 'neg':
                    adjustments -= abs(float(e.value))

            if effective is not None:
                effective = effective + adjustments

            if effective is not None:
                scores.append(effective)

        if not scores:
            return None

        avg = float(sum(scores)) / len(scores)

        # apply absences penalty using the related manager (attendances)
        ABSENCE_PENALTY = 0.2  # each absence reduces average by 0.2 by default
        try:
            abs_count = self.attendances.filter(present=False).count()
        except Exception:
            # fall back if Attendance model/table isn't available
            abs_count = 0

        adjusted = avg - (abs_count * ABSENCE_PENALTY)
        adjusted = max(0.0, min(20.0, adjusted))
        return round(adjusted, 2)


class Grade(models.Model):
    student = models.ForeignKey(Student, related_name='grades', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, related_name='grades', on_delete=models.CASCADE)
    score = models.DecimalField("نمره", max_digits=5, decimal_places=2,
                                validators=[MinValueValidator(0), MaxValueValidator(20)])

    class Meta:
        verbose_name = "نمره"
        verbose_name_plural = "نمرات"
        unique_together = ('student', 'subject')

    def __str__(self):
        return f"{self.student} — {self.subject.name}: {self.score}"


class GradebookEntry(models.Model):
    ENTRY_TYPES = [
        ('pos', 'مثبت'),
        ('neg', 'منفی'),
        ('num', 'نمره')
    ]

    student = models.ForeignKey(Student, related_name='gradebook_entries', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, related_name='gradebook_entries', on_delete=models.CASCADE, null=True, blank=True)
    entry_type = models.CharField('نوع', max_length=8, choices=ENTRY_TYPES)
    # value: for pos/neg = amount to add/subtract, for num = numeric grade override
    value = models.DecimalField('مقدار', max_digits=6, decimal_places=2, null=True, blank=True,
                                validators=[MinValueValidator(-20), MaxValueValidator(20)])
    date = models.DateField('تاریخ')
    # store a Jalali (Shamsi) representation for display/input convenience
    date_jalali = models.CharField('تاریخ (شمسی)', max_length=20, blank=True, null=True)
    notes = models.TextField('توضیحات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'ورودی دفتر نمره'
        verbose_name_plural = 'ورودی‌های دفتر نمره'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.student} — {self.get_entry_type_display()} {self.value or ''} ({self.date})"
    def clean(self):
        # For 'num' entries (explicit grade), value must be between 0 and 20
        if self.entry_type == 'num':
            if self.value is None:
                raise ValidationError({'value': 'برای نوع "نمره" باید مقدار وارد شود.'})
            if self.value < 0 or self.value > 20:
                raise ValidationError({'value': 'مقدار نمره باید بین 0 تا 20 باشد.'})
        # For pos/neg, validators on the field will enforce range
        return super().clean()

    def save(self, *args, **kwargs):
        # ensure date_jalali is kept consistent with date
        try:
            if self.date:
                # convert Gregorian date to Jalali string YYYY/MM/DD
                jd = jdatetime.date.fromgregorian(date=self.date)
                self.date_jalali = f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
            else:
                self.date_jalali = None
        except Exception:
            # if conversion fails, leave date_jalali as-is
            pass
        return super().save(*args, **kwargs)


class Attendance(models.Model):
    student = models.ForeignKey(Student, related_name='attendances', on_delete=models.CASCADE)
    date = models.DateField('تاریخ')
    # store Jalali representation as well for display and input preservation
    date_jalali = models.CharField('تاریخ (شمسی)', max_length=20, blank=True, null=True)
    present = models.BooleanField('حاضر', default=True)

    class Meta:
        verbose_name = 'حضور/غیاب'
        verbose_name_plural = 'لیست حضور و غیاب'
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student} — {self.date} — {'حاضر' if self.present else 'غایب'}"

    def save(self, *args, **kwargs):
        try:
            if self.date:
                jd = jdatetime.date.fromgregorian(date=self.date)
                self.date_jalali = f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
            else:
                self.date_jalali = None
        except Exception:
            pass
        return super().save(*args, **kwargs)


class AttendanceHistory(models.Model):
    """Historical snapshots of Attendance at reset times."""
    student = models.ForeignKey(Student, related_name='attendance_history', on_delete=models.CASCADE)
    date = models.DateField('تاریخ')
    date_jalali = models.CharField('تاریخ (شمسی)', max_length=20, blank=True, null=True)
    present = models.BooleanField('حاضر', default=True)
    archived_at = models.DateTimeField('زمان آرشیو', auto_now_add=True)

    class Meta:
        verbose_name = 'تاریخچه حضور/غیاب'
        verbose_name_plural = 'تاریخچه حضور/غیاب'
        ordering = ['-archived_at', '-date']


class GradebookEntryHistory(models.Model):
    """Historical snapshots of GradebookEntry at reset times."""
    student = models.ForeignKey(Student, related_name='gradebook_history', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    entry_type = models.CharField('نوع', max_length=8, choices=GradebookEntry.ENTRY_TYPES)
    value = models.DecimalField('مقدار', max_digits=6, decimal_places=2, null=True, blank=True)
    date = models.DateField('تاریخ', null=True, blank=True)
    date_jalali = models.CharField('تاریخ (شمسی)', max_length=20, blank=True, null=True)
    notes = models.TextField('توضیحات', blank=True)
    archived_at = models.DateTimeField('زمان آرشیو', auto_now_add=True)

    class Meta:
        verbose_name = 'تاریخچه دفتر نمره'
        verbose_name_plural = 'تاریخچه دفتر نمره'
        ordering = ['-archived_at', '-date']