# Generated by Django 5.1.4 on 2025-01-23 07:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('domain_id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('expiration_date', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='AhrefsData',
            fields=[
                ('domain', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='ahrefs_data', serialize=False, to='autobidder_app.domain')),
                ('domain_rating', models.IntegerField(default=0)),
                ('ahrefs_top', models.IntegerField(default=0)),
                ('backlinks', models.IntegerField(default=0)),
                ('ref_pages', models.IntegerField(default=0)),
                ('pages', models.IntegerField(default=0)),
                ('valid_pages', models.IntegerField(default=0)),
                ('text_links', models.IntegerField(default=0)),
                ('image_links', models.IntegerField(default=0)),
                ('nofollow_links', models.IntegerField(default=0)),
                ('ugc_links', models.IntegerField(default=0)),
                ('sponsored_links', models.IntegerField(default=0)),
                ('dofollow_links', models.IntegerField(default=0)),
                ('redirect_links', models.IntegerField(default=0)),
                ('canonical_links', models.IntegerField(default=0)),
                ('gov_links', models.IntegerField(default=0)),
                ('edu_links', models.IntegerField(default=0)),
                ('rss_links', models.IntegerField(default=0)),
                ('alternate_links', models.IntegerField(default=0)),
                ('html_pages', models.IntegerField(default=0)),
                ('internal_links', models.IntegerField(default=0)),
                ('external_links', models.IntegerField(default=0)),
                ('ref_domains', models.IntegerField(default=0)),
                ('ref_class_c', models.IntegerField(default=0)),
                ('ref_ips', models.IntegerField(default=0)),
                ('linked_root_domains', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Bet',
            fields=[
                ('domain', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='autobidder_app.domain')),
                ('max_bet', models.PositiveIntegerField()),
                ('expiration_date', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
