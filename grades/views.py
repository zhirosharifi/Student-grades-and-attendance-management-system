from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SchoolClass, Student, Subject, Grade, Attendance
from .forms import ClassForm, StudentForm, SubjectForm, GradeForm
from .forms import GradebookEntryForm, AttendanceDateForm, StudentLoginForm
from .models import GradebookEntry
from .forms import StudentEditForm
from .models import AttendanceHistory, GradebookEntryHistory
from django.db.models import Q
from django.contrib.sessions.models import Session

# Configurable maximum number of initial subjects when first adding students to a class
MAX_INITIAL_SUBJECTS = 13

def login_view(request):
    if request.user.is_authenticated:
        return redirect('grades:dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('grades:dashboard')
        else:
            error = "نام کاربری یا رمز عبور اشتباه است."
    return render(request, 'grades/login.html', {'error': error})

@login_required
def dashboard(request):
    classes = SchoolClass.objects.all().order_by('name')
    return render(request, 'grades/dashboard.html', {'classes': classes})

@login_required
def add_class(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            sc = form.save()
            messages.success(request, f'کلاس "{sc.name}" ساخته شد.')
            return redirect('grades:class_detail', class_id=sc.id)
    else:
        form = ClassForm()
    return render(request, 'grades/add_class.html', {'form': form})

@login_required
def class_detail(request, class_id):
    sc = get_object_or_404(SchoolClass, id=class_id)
    students = sc.students.all().order_by('roll_number', 'full_name')
    subjects = sc.subjects.all().order_by('id')

    # محاسبه معدل هر دانش‌آموز (server-side) و جمع/معدل کلاس
    student_averages = {}
    class_total = 0.0
    class_grade_count = 0

    for s in students:
        avg = s.average()
        student_averages[s.id] = avg
        # اضافه کردن به آمار کلاس
        grades = s.grades.all()
        for g in grades:
            class_total += float(g.score)
            class_grade_count += 1

    class_avg = round(class_total / class_grade_count, 2) if class_grade_count else None
    class_total = round(class_total, 2)
    # attendance records for this class (recent first)
    attendances = Attendance.objects.filter(student__classroom=sc).order_by('-date', '-id')[:200]

    return render(request, 'grades/class_detail.html', {
        'class': sc,
        'students': students,
        'subjects': subjects,
        'student_averages': student_averages,
        'class_total': class_total,
        'class_avg': class_avg,
        'attendances': attendances,
    })

@login_required
def add_student(request, class_id):
    sc = get_object_or_404(SchoolClass, id=class_id)
    if request.method == 'POST':
        form = StudentForm(request.POST)
        initial_subjects = request.POST.get('initial_subjects', '').strip()
        if form.is_valid():
            student = form.save(commit=False)
            student.classroom = sc
            student.save()

            # اگر کلاس دروسی نداشت و معلم رشته ای از دروس را وارد کرد، آن دروس را بساز
            if sc.subjects.count() == 0 and initial_subjects:
                # extract names and enforce a maximum number of subjects
                names = [n.strip() for n in initial_subjects.split(',') if n.strip()]
                if len(names) > MAX_INITIAL_SUBJECTS:
                    # roll back student creation and show an error
                    student.delete()
                    messages.error(request, f'تعداد دروس نمی‌تواند بیش از {MAX_INITIAL_SUBJECTS} باشد.')
                    return redirect('grades:add_student', class_id=sc.id)

                for name in names:
                    Subject.objects.create(classroom=sc, name=name)
            messages.success(request, f'دانش‌آموز "{student.full_name}" اضافه شد.')
            return redirect('grades:class_detail', class_id=sc.id)
    else:
        form = StudentForm()
    return render(request, 'grades/add_student.html', {'form': form, 'class': sc})

@login_required
def add_subject(request, class_id):
    sc = get_object_or_404(SchoolClass, id=class_id)
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subj = form.save(commit=False)
            subj.classroom = sc
            subj.save()
            messages.success(request, f'درس "{subj.name}" اضافه شد.')
            return redirect('grades:class_detail', class_id=sc.id)
    else:
        form = SubjectForm()
    return render(request, 'grades/add_subject.html', {'form': form, 'class': sc})


@login_required
def manage_subjects(request, class_id):
    sc = get_object_or_404(SchoolClass, id=class_id)
    subjects = sc.subjects.all().order_by('id')

    # Use SubjectForm for adding or renaming
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            form = SubjectForm(request.POST)
            if form.is_valid():
                subj = form.save(commit=False)
                subj.classroom = sc
                try:
                    subj.save()
                    messages.success(request, f'درس "{subj.name}" اضافه شد.')
                except Exception as e:
                    messages.error(request, 'خطا در افزودن درس: ' + str(e))
                return redirect('grades:manage_subjects', class_id=sc.id)
        elif action == 'rename':
            subj_id = request.POST.get('subject_id')
            new_name = request.POST.get('new_name', '').strip()
            new_teacher = request.POST.get('new_teacher', '').strip()
            subj = get_object_or_404(Subject, id=subj_id, classroom=sc)
            if new_name:
                subj.name = new_name
            if new_teacher:
                subj.teacher_name = new_teacher
                try:
                    subj.save()
                    messages.success(request, 'نام درس به‌روزرسانی شد.')
                except Exception as e:
                    messages.error(request, 'خطا در ویرایش: ' + str(e))
            return redirect('grades:manage_subjects', class_id=sc.id)
        elif action == 'delete':
            subj_id = request.POST.get('subject_id')
            subj = get_object_or_404(Subject, id=subj_id, classroom=sc)
            subj.delete()
            messages.success(request, 'درس حذف شد.')
            return redirect('grades:manage_subjects', class_id=sc.id)

    else:
        form = SubjectForm()

    return render(request, 'grades/manage_subjects.html', {
        'class': sc,
        'subjects': subjects,
        'form': form,
    })


@login_required
def mark_attendance(request, class_id):
    sc = get_object_or_404(SchoolClass, id=class_id)
    students = sc.students.all().order_by('roll_number', 'full_name')
    if request.method == 'POST':
        form = AttendanceDateForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            for stu in students:
                present = request.POST.get(f'present_{stu.id}') == 'on'
                Attendance.objects.update_or_create(student=stu, date=date, defaults={'present': present})
            messages.success(request, 'حضور/غیاب ذخیره شد.')
            return redirect('grades:class_detail', class_id=sc.id)
    else:
        import datetime
        today = datetime.date.today()
        # convert today's date to Jalali string for display in the form
        try:
            import jdatetime
            jd = jdatetime.date.fromgregorian(date=today)
            today_j = f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
        except Exception:
            today_j = today.isoformat()
        form = AttendanceDateForm(initial={'date': today_j})

    existing_map = {}
    if request.GET.get('date'):
        try:
            from datetime import datetime as _dt
            sel = _dt.fromisoformat(request.GET.get('date')).date()
            atts = Attendance.objects.filter(student__classroom=sc, date=sel)
            existing_map = {a.student_id: a.present for a in atts}
            # set initial to Jalali representation when available
            try:
                import jdatetime
                jd = jdatetime.date.fromgregorian(date=sel)
                sel_j = f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
            except Exception:
                sel_j = sel.isoformat()
            form = AttendanceDateForm(initial={'date': sel_j})
        except Exception:
            existing_map = {}

    return render(request, 'grades/mark_attendance.html', {
        'class': sc,
        'students': students,
        'form': form,
        'existing_map': existing_map,
    })


@login_required
def delete_class(request, class_id):
    sc = get_object_or_404(SchoolClass, id=class_id)
    if request.method == 'POST':
        sc.delete()
        messages.success(request, f'کلاس "{sc.name}" حذف شد.')
    return redirect('grades:dashboard')

@login_required
def student_grades(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    sc = student.classroom
    subjects = sc.subjects.all().order_by('id')

    # ساخت رکورد نمره برای موضوعاتی که هنوز نمره ندارند، در save انجام خواهد شد در POST
    if request.method == 'POST':
        form = GradeForm(request.POST, subjects=subjects)
        if form.is_valid():
            for subj in subjects:
                key = f"subject_{subj.id}"
                val = form.cleaned_data.get(key)
                if val is None or val == '':
                    continue
                grade_obj, created = Grade.objects.update_or_create(
                    student=student, subject=subj,
                    defaults={'score': val}
                )
            messages.success(request, 'نمرات ذخیره شد.')
            return redirect('grades:class_detail', class_id=sc.id)
    else:
        # مقداردهی اولیه از نمرات قبلی
        initial = {}
        for g in student.grades.all():
            initial[f"subject_{g.subject.id}"] = float(g.score)
        form = GradeForm(initial=initial, subjects=subjects)

    return render(request, 'grades/edit_scores.html', {
        'student': student,
        'class': sc,
        'form': form,
        'subjects': subjects,
        'student_avg': student.average()
    })


@login_required
def delete_student(request, student_id):
    # only allow POST to delete
    student = get_object_or_404(Student, id=student_id)
    class_id = student.classroom.id
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'دانش‌آموز حذف شد.')
        return redirect('grades:class_detail', class_id=class_id)
    # If GET or other, redirect back
    return redirect('grades:class_detail', class_id=class_id)


@login_required
def gradebook(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    entries = student.gradebook_entries.all()
    subjects = student.classroom.subjects.all()

    if request.method == 'POST':
        form = GradebookEntryForm(request.POST, subjects=subjects)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.student = student
            try:
                entry.full_clean()
                entry.save()
                messages.success(request, 'ورودی دفتر نمره اضافه شد.')
                return redirect('grades:gradebook', student_id=student.id)
            except Exception as e:
                messages.error(request, f'خطا در ذخیره ورودی: {e}')
                # fallthrough to re-render form with error messages
        else:
            # form invalid: fall through to render page with form (so errors show)
            messages.error(request, 'فرم معتبر نیست. لطفاً خطاها را بررسی کنید.')
    else:
        # prefer to prefill date with today's Jalali date for new entries
        try:
            import datetime, jdatetime
            today = datetime.date.today()
            jd = jdatetime.date.fromgregorian(date=today)
            today_j = f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
        except Exception:
            today_j = None
        form = GradebookEntryForm(subjects=subjects, initial={'date': today_j})

    return render(request, 'grades/gradebook.html', {
        'student': student,
        'entries': entries,
        'form': form,
        'class': student.classroom,
        'subjects': subjects,
    })


@login_required
def delete_gradebook_entry(request, entry_id):
    entry = get_object_or_404(GradebookEntry, id=entry_id)
    class_id = entry.student.classroom.id
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'ورودی حذف شد.')
    return redirect('grades:class_detail', class_id=class_id)


@login_required
def edit_gradebook_entry(request, entry_id):
    entry = get_object_or_404(GradebookEntry, id=entry_id)
    student = entry.student
    subjects = student.classroom.subjects.all()
    if request.method == 'POST':
        form = GradebookEntryForm(request.POST, instance=entry, subjects=subjects)
        if form.is_valid():
            try:
                entry = form.save(commit=False)
                entry.full_clean()
                entry.save()
                messages.success(request, 'ورودی به‌روزرسانی شد.')
                return redirect('grades:gradebook', student_id=student.id)
            except Exception as e:
                messages.error(request, f'خطا: {e}')
    else:
        # populate initial 'date' using entry.date_jalali if available
        init = {}
        if entry.date_jalali:
            init['date'] = entry.date_jalali
        else:
            init['date'] = entry.date.isoformat() if entry.date else None
        form = GradebookEntryForm(instance=entry, subjects=subjects, initial=init)

    return render(request, 'grades/edit_gradebook_entry.html', {
        'form': form,
        'entry': entry,
        'student': student,
        'class': student.classroom,
    })


@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    sc = student.classroom
    if request.method == 'POST':
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'اطلاعات دانش‌آموز به‌روزرسانی شد.')
            return redirect('grades:class_detail', class_id=sc.id)
    else:
        form = StudentEditForm(instance=student)
    return render(request, 'grades/edit_student.html', {
        'form': form,
        'student': student,
        'class': sc,
    })


@login_required
def delete_attendance_entry(request, student_id, date):
    # Delete a specific attendance of a student for a given date (ISO format)
    from datetime import datetime as _dt
    sc_id = None
    try:
        d = _dt.fromisoformat(date).date()
        att = get_object_or_404(Attendance, student_id=student_id, date=d)
        sc_id = att.student.classroom_id
        if request.method == 'POST':
            att.delete()
            messages.success(request, 'حضور/غیاب حذف شد.')
    except Exception:
        messages.error(request, 'تاریخ نامعتبر است.')
    if sc_id is None:
        try:
            s = Student.objects.get(id=student_id)
            sc_id = s.classroom_id
        except Student.DoesNotExist:
            return redirect('grades:dashboard')
    return redirect('grades:class_detail', class_id=sc_id)


@login_required
def reset_attendance(request, class_id):
    # Archive all attendance for class and then delete them
    sc = get_object_or_404(SchoolClass, id=class_id)
    atts = Attendance.objects.filter(student__classroom=sc)
    # archive
    bulk = [AttendanceHistory(student=a.student, date=a.date, date_jalali=a.date_jalali, present=a.present) for a in atts]
    AttendanceHistory.objects.bulk_create(bulk)
    # delete
    atts.delete()
    messages.success(request, 'حضور/غیاب ریست شد و به تاریخچه منتقل شد.')
    return redirect('grades:class_detail', class_id=sc.id)


@login_required
def reset_gradebook(request, class_id):
    sc = get_object_or_404(SchoolClass, id=class_id)
    entries = GradebookEntry.objects.filter(student__classroom=sc)
    bulk = [
        GradebookEntryHistory(
            student=e.student,
            subject=e.subject,
            entry_type=e.entry_type,
            value=e.value,
            date=e.date,
            date_jalali=e.date_jalali,
            notes=e.notes,
        ) for e in entries
    ]
    GradebookEntryHistory.objects.bulk_create(bulk)
    entries.delete()
    messages.success(request, 'دفتر نمره ریست شد و به تاریخچه منتقل شد.')
    return redirect('grades:class_detail', class_id=sc.id)


@login_required
def attendance_history(request):
    qs = AttendanceHistory.objects.select_related('student').all()
    q = request.GET.get('q', '').strip()
    present = request.GET.get('present')
    if q:
        qs = qs.filter(Q(student__full_name__icontains=q) | Q(student__national_id__icontains=q))
    if present in ['0', '1']:
        qs = qs.filter(present=(present == '1'))
    qs = qs.order_by('-archived_at')[:1000]
    return render(request, 'grades/attendance_history.html', {'items': qs})


@login_required
def gradebook_history(request):
    qs = GradebookEntryHistory.objects.select_related('student', 'subject').all()
    q = request.GET.get('q', '').strip()
    entry_type = request.GET.get('entry_type', '').strip()
    if q:
        qs = qs.filter(Q(student__full_name__icontains=q) | Q(subject__name__icontains=q))
    if entry_type in ['pos', 'neg', 'num']:
        qs = qs.filter(entry_type=entry_type)
    qs = qs.order_by('-archived_at')[:1000]
    return render(request, 'grades/gradebook_history.html', {'items': qs})


@login_required
def clear_attendance_history(request):
    if request.method == 'POST':
        AttendanceHistory.objects.all().delete()
        messages.success(request, 'تمام تاریخچه حضور/غیاب حذف شد.')
    return redirect('grades:attendance_history')


@login_required
def clear_gradebook_history(request):
    if request.method == 'POST':
        GradebookEntryHistory.objects.all().delete()
        messages.success(request, 'تمام تاریخچه دفتر نمره حذف شد.')
    return redirect('grades:gradebook_history')


def student_login_view(request):
    """Student login view using national_id and password"""
    if request.session.get('student_id'):
        return redirect('grades:student_dashboard')
    
    error = None
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            national_id = form.cleaned_data['national_id']
            password = form.cleaned_data['password']
            
            try:
                student = Student.objects.get(national_id=national_id, password=password)
                request.session['student_id'] = student.id
                request.session['student_name'] = student.full_name
                return redirect('grades:student_dashboard')
            except Student.DoesNotExist:
                error = "کد ملی یا رمز عبور اشتباه است."
    else:
        form = StudentLoginForm()
    
    return render(request, 'grades/student_login.html', {'form': form, 'error': error})


def student_logout_view(request):
    """Student logout view"""
    if 'student_id' in request.session:
        del request.session['student_id']
    if 'student_name' in request.session:
        del request.session['student_name']
    return redirect('grades:student_login')


def student_dashboard(request):
    """Student dashboard showing grades, gradebook entries, and attendance"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('grades:student_login')
    
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return redirect('grades:student_login')
    
    # Get student's grades
    grades = student.grades.all()
    
    # Get student's gradebook entries
    gradebook_entries = student.gradebook_entries.all().order_by('-date', '-created_at')
    
    # Get student's attendance records
    attendances = student.attendances.all().order_by('-date')
    
    # Calculate student average
    student_average = student.average()
    
    # Get subjects for this student's class
    subjects = student.classroom.subjects.all()
    
    return render(request, 'grades/student_dashboard.html', {
        'student': student,
        'grades': grades,
        'gradebook_entries': gradebook_entries,
        'attendances': attendances,
        'student_average': student_average,
        'subjects': subjects,
    })
