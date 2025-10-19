from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import SchoolClass, Student, Subject, Grade

class ClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ['name']
        labels = {'name': 'نام کلاس'}
        widgets = {'name': forms.TextInput(attrs={'class':'form-control','placeholder':'مثال: کلاس هشتم الف'})}

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'roll_number', 'national_id', 'password', 'phone1', 'phone2', 'phone3', 'email1', 'email2']
        labels = {
            'full_name': 'نام و نام خانوادگی',
            'roll_number': 'شماره دانش‌آموزی',
            'national_id': 'کد ملی',
            'password': 'رمز عبور',
            'phone1': 'شماره تلفن ۱',
            'phone2': 'شماره تلفن ۲',
            'phone3': 'شماره تلفن ۳',
            'email1': 'ایمیل ۱',
            'email2': 'ایمیل ۲',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class':'form-control','placeholder':'نام و نام خانوادگی'}),
            'roll_number': forms.NumberInput(attrs={'class':'form-control','placeholder':'مثال: 12'}),
            'national_id': forms.TextInput(attrs={'class':'form-control','placeholder':'مثال: 0012345678'}),
            'password': forms.PasswordInput(attrs={'class':'form-control','placeholder':'رمز عبور دانش‌آموز'}),
            'phone1': forms.TextInput(attrs={'class':'form-control','placeholder':'+98912XXXXXXX'}),
            'phone2': forms.TextInput(attrs={'class':'form-control','placeholder':'+98912XXXXXXX'}),
            'phone3': forms.TextInput(attrs={'class':'form-control','placeholder':'+98912XXXXXXX'}),
            'email1': forms.EmailInput(attrs={'class':'form-control','placeholder':'example@mail.com'}),
            'email2': forms.EmailInput(attrs={'class':'form-control','placeholder':'example@mail.com'}),
        }

class StudentEditForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'roll_number', 'national_id', 'password', 'phone1', 'phone2', 'phone3', 'email1', 'email2']
        labels = StudentForm.Meta.labels
        widgets = StudentForm.Meta.widgets

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'teacher_name']
        labels = {'name': 'نام درس'}
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control','placeholder':'مثال: ریاضی'}),
            'teacher_name': forms.TextInput(attrs={'class':'form-control','placeholder':'نام معلم (اختیاری)'}),
        }

# Dynamic grade form — created in views based on subjects
class GradeForm(forms.Form):
    def __init__(self, *args, subjects=None, **kwargs):
        super().__init__(*args, **kwargs)
        subjects = subjects or []
        for subj in subjects:
            name = f"subject_{subj.id}"
            self.fields[name] = forms.DecimalField(
                required=False,
                max_digits=5,
                decimal_places=2,
                label=subj.name,
                min_value=0,
                max_value=20,
                validators=[MinValueValidator(0), MaxValueValidator(20)],
                widget=forms.NumberInput(attrs={'class':'form-control','step':'0.01','min':'0','max':'20'})
            )


from .models import GradebookEntry, Subject, Student
import jdatetime
from datetime import date as _date


class GradebookEntryForm(forms.ModelForm):
    # override the model DateField so we can accept Jalali strings and parse them in clean_date
    date = forms.CharField(label='تاریخ', widget=forms.TextInput(attrs={'class':'form-control persian-date','placeholder':'YYYY/MM/DD'}), required=False)
    class Meta:
        model = GradebookEntry
        fields = ['subject', 'entry_type', 'value', 'date', 'notes']
        labels = {
            'subject': 'درس',
            'date': 'تاریخ'
        }
        widgets = {
            'subject': forms.Select(attrs={'class':'form-control'}),
            'entry_type': forms.Select(attrs={'class':'form-control'}),
            'value': forms.NumberInput(attrs={'class':'form-control','step':'0.01','min':'-20','max':'20'}),
            # show native date input as fallback; JS may replace it with persian datepicker
            'date': forms.TextInput(attrs={'class':'form-control persian-date','placeholder':'YYYY/MM/DD'}),
            'notes': forms.Textarea(attrs={'class':'form-control','rows':2}),
        }

    def __init__(self, *args, subjects=None, **kwargs):
        super().__init__(*args, **kwargs)
        if subjects is not None:
            self.fields['subject'].queryset = subjects

    def clean_date(self):
        val = self.cleaned_data.get('date')
        if not val:
            return None
        try:
            # ISO YYYY-MM-DD
            if '-' in val:
                parts = val.split('-')
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                return _date(y, m, d)
            # Jalali YYYY/MM/DD
            if '/' in val:
                parts = val.split('/')
                jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                gd = jdatetime.date(jy, jm, jd).togregorian()
                return _date(gd.year, gd.month, gd.day)
        except Exception:
            raise forms.ValidationError('فرمت تاریخ معتبر نیست (مانند 1404/07/25 یا 2025-10-17).')
        raise forms.ValidationError('فرمت تاریخ نامشخص است.')


class AttendanceDateForm(forms.Form):
    """Simple form to pick a date for marking attendance."""
    # Accept Jalali date strings (e.g. 1404/07/25) or ISO YYYY-MM-DD; convert to Python date
    date = forms.CharField(label='تاریخ', widget=forms.TextInput(attrs={'class':'form-control persian-date','placeholder':'YYYY/MM/DD'}), required=True)

    def clean_date(self):
        val = self.cleaned_data.get('date')
        if not val:
            raise forms.ValidationError('تاریخ معتبر نیست.')
        # allow ISO format YYYY-MM-DD
        try:
            if '-' in val:
                parts = val.split('-')
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                return _date(y, m, d)
            # allow Jalali format YYYY/MM/DD
            if '/' in val:
                parts = val.split('/')
                jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                gd = jdatetime.date(jy, jm, jd).togregorian()
                return _date(gd.year, gd.month, gd.day)
        except Exception:
            raise forms.ValidationError('فرمت تاریخ معتبر نیست (مانند 1404/07/25 یا 2025-10-17).')
        raise forms.ValidationError('فرمت تاریخ نامشخص است.')


class StudentLoginForm(forms.Form):
    """Form for student login using national_id and password"""
    national_id = forms.CharField(
        label='کد ملی',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'کد ملی خود را وارد کنید'
        })
    )
    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور خود را وارد کنید'
        })
    )