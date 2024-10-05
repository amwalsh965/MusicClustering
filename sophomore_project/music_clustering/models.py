from django.db import models


# Create your models here.
class User(models.Model):
    spotify_id = models.CharField(max_length=200, blank=False, null=False)
    spotify_display_name = models.CharField(max_length=200)


class Genre(models.Model):
    name = models.CharField(max_length=200, default="")


class Song(models.Model):
    title = models.CharField(max_length=200, default="")
    genre = models.ForeignKey(
        Genre, on_delete=models.CASCADE, default="", null=True, blank=True
    )
    artist_name = models.CharField(max_length=200, default="")
    valence = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    popularity = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True
    )
    tempo = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.title} by {self.artist_name}"


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.song.title}: {self.user_rating}"
