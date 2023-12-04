from django.db import models

class ImageData(models.Model):
    face_encoding = models.BinaryField()
    image_file_name = models.TextField()
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    image_width = models.IntegerField()
    image_height = models.IntegerField()
    file_size = models.IntegerField()
    attributes = models.JSONField()
