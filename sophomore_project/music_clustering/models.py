from django.db import models


# Create your models here.
class User(models.Model):
    spotify_id = models.CharField(max_length=200, blank=False, null=False)
    spotify_display_name = models.CharField(max_length=200)


class Genre(models.Model):
    name = models.CharField(max_length=200, default="")


class Song(models.Model):
    track_id = models.CharField(max_length=200, default="", null=True, blank=True)
    title = models.CharField(max_length=200, default="")
    genres = models.ManyToManyField(Genre, blank=True)
    artist_name = models.CharField(max_length=200, default="")
    popularity = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    valence = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    tempo = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    danceability = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    energy = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    key = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    speechiness = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    acousticness = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    instrumentalness = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    liveness = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )

    def __str__(self):
        return f"{self.title} by {self.artist_name}"


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.song.title}: {self.user_rating}"
