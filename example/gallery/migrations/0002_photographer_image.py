# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-07 10:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='photographer',
            name='image',
            field=models.ImageField(default='', upload_to='', verbose_name='image'),
            preserve_default=False,
        ),
    ]
