from django.urls import path
from . import views

urlpatterns = [
    path('list', views.get_encodings),
    path('truncate',views.truncate_image_data),
    path('run-cron',views.cron_job)
]