# Generated by Django 3.0.8 on 2020-12-08 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_notification_isdeleted'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('delivered', 'delivered'), ('on-the-way', 'on-the-way'), ('delayed', 'delayed'), ('pending', 'pending'), ('ready-to-pick-up', 'ready-to-pick-up'), ('confirmed', 'confirmed'), ('rejected', 'rejected'), ('rated', 'rated')], default='pending', max_length=25),
        ),
    ]
