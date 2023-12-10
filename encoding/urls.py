from django.urls import path
from . import views

urlpatterns = [
    path('folder_upload', views.folder_upload),
    path('list', views.get_encodings),
    path('check', views.check_image),
    path('truncate',views.truncate_image_data),
    path('run-cron',views.cron_job)
]