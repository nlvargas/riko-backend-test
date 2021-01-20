# Generated by Django 3.0.8 on 2021-01-13 17:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_order_chargeid'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurant',
            name='totalDelays',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='isBanned',
            field=models.BooleanField(default=False),
        ),
    ]