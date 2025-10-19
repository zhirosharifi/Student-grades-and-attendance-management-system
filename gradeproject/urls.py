from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # include app grades with namespace 'grades'
    path('', include(('grades.urls', 'grades'), namespace='grades')),
]
