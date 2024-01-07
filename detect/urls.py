from django.urls import path
from . import views

urlpatterns = [
    path('folder', views.folder_upload),
    path('image', views.check_image),
    path('link',views.check_image_url)
]