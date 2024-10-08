# Generated by Django 5.1.1 on 2024-10-05 18:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spotify_id', models.CharField(max_length=200)),
                ('spotify_display_name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Song',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('track_id', models.CharField(blank=True, default='', max_length=200, null=True)),
                ('title', models.CharField(default='', max_length=200)),
                ('artist_name', models.CharField(default='', max_length=200)),
                ('popularity', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('valence', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('tempo', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('danceability', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('energy', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('key', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('speechiness', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('acousticness', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('instrumentalness', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('liveness', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('genres', models.ManyToManyField(blank=True, to='music_clustering.genre')),
            ],
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(default=5)),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='music_clustering.song')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='music_clustering.user')),
            ],
        ),
    ]
