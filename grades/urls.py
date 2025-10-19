from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'grades'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # صفحه اصلی پس از لاگین
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='grades:login'), name='logout'),

    path('class/add/', views.add_class, name='add_class'),
    path('class/<int:class_id>/', views.class_detail, name='class_detail'),
    path('class/<int:class_id>/student/add/', views.add_student, name='add_student'),
    path('class/<int:class_id>/subject/add/', views.add_subject, name='add_subject'),
    path('class/<int:class_id>/subjects/', views.manage_subjects, name='manage_subjects'),
    path('class/<int:class_id>/attendance/', views.mark_attendance, name='mark_attendance'),
    path('class/<int:class_id>/delete/', views.delete_class, name='delete_class'),
    path('student/<int:student_id>/grades/', views.student_grades, name='student_grades'),
    path('student/<int:student_id>/delete/', views.delete_student, name='delete_student'),
    path('student/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('student/<int:student_id>/gradebook/', views.gradebook, name='gradebook'),
    path('gradebook/entry/<int:entry_id>/delete/', views.delete_gradebook_entry, name='delete_gradebook_entry'),
    path('gradebook/entry/<int:entry_id>/edit/', views.edit_gradebook_entry, name='edit_gradebook_entry'),
    # attendance per-entry delete and resets
    path('attendance/<int:student_id>/<str:date>/delete/', views.delete_attendance_entry, name='delete_attendance_entry'),
    path('class/<int:class_id>/attendance/reset/', views.reset_attendance, name='reset_attendance'),
    path('class/<int:class_id>/gradebook/reset/', views.reset_gradebook, name='reset_gradebook'),
    # histories
    path('attendance/history/', views.attendance_history, name='attendance_history'),
    path('gradebook/history/', views.gradebook_history, name='gradebook_history'),
    path('attendance/history/clear/', views.clear_attendance_history, name='clear_attendance_history'),
    path('gradebook/history/clear/', views.clear_gradebook_history, name='clear_gradebook_history'),
    
    # Student login and dashboard
    path('student/login/', views.student_login_view, name='student_login'),
    path('student/logout/', views.student_logout_view, name='student_logout'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
]
