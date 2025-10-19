from django.contrib import admin
from .models import SchoolClass, Subject, Student, Grade, GradebookEntry

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'classroom')
    list_filter = ('classroom',)
    search_fields = ('name',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'roll_number', 'classroom')
    list_filter = ('classroom',)
    search_fields = ('full_name', 'roll_number')
    list_display_links = ('full_name',)
    inlines = []

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'score')
    list_filter = ('subject', 'student__classroom')
    search_fields = ('student__full_name', 'subject__name')


@admin.register(GradebookEntry)
class GradebookEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'entry_type', 'value', 'date', 'created_at')
    list_filter = ('entry_type', 'date', 'student__classroom')
    search_fields = ('student__full_name', 'notes')
