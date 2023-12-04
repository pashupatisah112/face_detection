from django.urls import path
from . import views

urlpatterns = [
    path('folder_upload', views.folder_upload),
    path('list', views.get_encodings)
]