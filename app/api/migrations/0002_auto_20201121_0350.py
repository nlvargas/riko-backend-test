# Generated by Django 3.0.8 on 2020-11-21 03:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='orderID',
            field=models.CharField(editable=False, max_length=50, primary_key=True, serialize=False),
        ),
    ]
