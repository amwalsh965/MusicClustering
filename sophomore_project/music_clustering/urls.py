from django.urls import path
from . import views
from .views import (
    rate_songs,
    spotify_login,
    spotify_callback,
    home,
    song_recommendation,
    get_song_recommendations,
    add_playlist_songs,
)

urlpatterns = [
    path("rate_songs/", rate_songs, name="rate_songs"),
    path("rate_songs_relog/", spotify_login, name="rate_songs_relog"),
    path("", spotify_login, name="spotify_login"),
    path("spotify/callback/", spotify_callback, name="spotify_callback"),
    path("home/", home, name="home"),
    path("song_recommendation", song_recommendation, name="song_recommendation"),
    path(
        "get_song_recommendations",
        get_song_recommendations,
        name="get_song_recommendations",
    ),
    path("add_songs", add_playlist_songs, name="add_songs"),
]
