# Generated by Django 4.2.14 on 2024-08-28 14:31

import courses.validators.custom_url_validators
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0015_enrollment_certificate_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='about_me',
            field=models.TextField(blank=True, help_text='You can put any information about yourself here', null=True, verbose_name='About me'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='github_url',
            field=models.URLField(blank=True, null=True, validators=[django.core.validators.URLValidator(), courses.validators.custom_url_validators.validate_url_200], verbose_name='GitHub URL'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='linkedin_url',
            field=models.URLField(blank=True, null=True, validators=[django.core.validators.URLValidator(), courses.validators.custom_url_validators.validate_url_200], verbose_name='LinkedIn URL'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='personal_website_url',
            field=models.URLField(blank=True, null=True, validators=[django.core.validators.URLValidator(), courses.validators.custom_url_validators.validate_url_200], verbose_name='Personal website URL'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='certificate_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Name for the certificate'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='display_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Leaderboard name'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='about_me',
            field=models.TextField(blank=True, help_text='Any information about you', null=True, verbose_name='About me'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='certificate_name',
            field=models.CharField(blank=True, help_text='Your actual name that will appear on your certificate', max_length=255, null=True, verbose_name='Certificate name'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='display_name',
            field=models.CharField(blank=True, help_text='Name on the leaderboard', max_length=255, verbose_name='Leaderboard name'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='github_url',
            field=models.URLField(blank=True, null=True, validators=[django.core.validators.URLValidator()], verbose_name='GitHub URL'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='linkedin_url',
            field=models.URLField(blank=True, null=True, validators=[django.core.validators.URLValidator()], verbose_name='LinkedIn URL'),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='personal_website_url',
            field=models.URLField(blank=True, null=True, validators=[django.core.validators.URLValidator()], verbose_name='Personal website URL'),
        ),
    ]
