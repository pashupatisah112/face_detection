from django.urls import path
from . import views

urlpatterns = [
    path('folder', views.folder_upload),
    path('image', views.handle_image),
]