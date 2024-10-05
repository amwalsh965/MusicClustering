from django.urls import path
from . import views
from .views import rate_songs, spotify_login, spotify_callback

urlpatterns = [
    path("", rate_songs, name="rate_songs"),
    path("spotify/login/", spotify_login, name="spotify_login"),
    path("spotify/callback/", spotify_callback, name="spotify_callback"),
]
