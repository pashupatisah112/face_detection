# Generated by Django 4.2.1 on 2023-12-04 09:08

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('encoding', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imagedata',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='imagedata',
            name='modified_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
