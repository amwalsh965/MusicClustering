import time
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Song, Rating, User
from .forms import RatingForm

import spotipy
import requests
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings


def index(request):
    return HttpResponse("Hello, world!")


def skip_song(request, access_token):
    skip_url = "https://api.spotify.com/v1/me/player/next"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.post(skip_url, headers=headers)

    if response.status_code == 204 or response.status_code == 200:

        time.sleep(1)

        current_song_url = "https://api.spotify.com/v1/me/player/currently-playing"
        song_response = requests.get(current_song_url, headers=headers)

        if song_response.status_code == 200:
            return song_response.json()

    return None


def rate_songs(request):
    access_token = request.session.get("token_info").get("access_token")
    current_song_info = get_current_song(request)

    if request.method == "POST":
        song_id = request.POST.get("song")
        user_rating = request.POST.get("rating")

        if song_id and user_rating:
            print(song_id)
            song = Song.objects.get(pk=song_id)

            Rating.objects.create(
                user=User.objects.get(
                    spotify_id=request.session.get("spotify_user_id")
                ),
                song=song,
                rating=user_rating,
            )

            current_song_info = skip_song(request, access_token)

            if current_song_info:
                artist = ", ".join(
                    [artist["name"] for artist in current_song_info["item"]["artists"]]
                )

                popularity = current_song_info["item"]["popularity"]

                song, created = Song.objects.get_or_create(
                    title=current_song_info["item"]["name"],
                    popularity=popularity,
                    artist_name=artist,
                )

                current_song_info = {
                    "song": song,
                    "track_name": current_song_info["item"]["name"],
                    "artist_name": artist,
                }

            else:
                return redirect("thank_you")

    print(current_song_info)

    return render(
        request,
        "../templates/rate_song.html",
        {
            "current_song_info": current_song_info,
        },
    )


sp_oauth = SpotifyOAuth(
    client_id=settings.SPOTIFY_CLIENT_ID,
    client_secret=settings.SPOTIFY_CLIENT_SECRET,
    redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    scope="user-modify-playback-state user-read-currently-playing user-read-playback-state",
)


def spotify_login(request):
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


def spotify_callback(request):
    code = request.GET.get("code")
    token_info = sp_oauth.get_access_token(code)

    request.session["token_info"] = token_info

    sp = spotipy.Spotify(auth=token_info["access_token"])

    spotify_user = sp.current_user()
    spotify_user_id = spotify_user["id"]
    spotify_display_name = spotify_user.get("display_name", spotify_user_id)

    user, created = User.objects.get_or_create(
        spotify_id=spotify_user_id, spotify_display_name=spotify_display_name
    )

    request.session["spotify_user_id"] = spotify_user_id

    return redirect("rate_songs")


def get_current_song(request):
    token_info = request.session.get("token_info")

    if token_info:
        sp = spotipy.Spotify(auth=token_info["access_token"])

        current_track = sp.current_user_playing_track()

        if current_track and current_track["is_playing"]:
            track_name = current_track["item"]["name"]
            artist_name = ", ".join(
                [artist["name"] for artist in current_track["item"]["artists"]]
            )

            popularity = current_track["item"]["popularity"]

            # Check if the song already exists in the database
            song, created = Song.objects.get_or_create(
                title=track_name,
                popularity=popularity,
                artist_name=artist_name,
            )

            return {
                "song": song,
                "track_name": track_name,
                "artist_name": artist_name,
            }

    return None
