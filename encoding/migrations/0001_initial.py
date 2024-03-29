# Generated by Django 4.2.1 on 2023-12-04 05:07

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ImageData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('face_encoding', models.BinaryField()),
                ('image_file_name', models.TextField()),
                ('created_at', models.DateTimeField()),
                ('modified_at', models.DateTimeField()),
                ('image_width', models.IntegerField()),
                ('image_height', models.IntegerField()),
                ('file_size', models.IntegerField()),
                ('attributes', models.JSONField()),
            ],
        ),
    ]
