import time
from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from .models import Song, Rating, User, Genre
from .forms import RatingForm

import spotipy
import requests
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings

from django.contrib.auth.decorators import login_required


def index(request):
    return HttpResponse("Hello, world!")


def serialize_song(song: Song):
    return {
        "track_name": song.title,
        "artist_name": song.artist_name,
        "tempo": song.tempo,
        "valence": song.valence,
        "genres": [genre.name for genre in song.genres.all()],  # Serialize genres
    }


def skip_song(request, access_token):
    skip_url = "https://api.spotify.com/v1/me/player/next"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.post(skip_url, headers=headers)

    if response.status_code == 204 or response.status_code == 200:

        # time.sleep(1)

        current_song_url = "https://api.spotify.com/v1/me/player/currently-playing"
        song_response = requests.get(current_song_url, headers=headers)

        if song_response.status_code == 200:
            return song_response.json()

    return None


def rate_songs(request):
    access_token = request.session.get("token_info").get("access_token")
    current_song_info = get_current_song(request)

    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and request.method == "GET"
    ):
        if current_song_info:
            current_song_info["song"] = serialize_song(current_song_info["song"])
            return JsonResponse(current_song_info)
        else:
            data = {"title": None, "artist": None, "tempo": None, "valence": None}
            return JsonResponse(data)

    if request.method == "POST":
        song_id = request.POST.get("song")
        user_rating = request.POST.get("rating")

        if song_id and user_rating:
            try:
                song = Song.objects.get(pk=song_id)
            except Song.DoesNotExist:
                current_song_info = get_current_song(request)
                song = current_song_info.get("song")

            Rating.objects.create(
                user=User.objects.get(
                    spotify_id=request.session.get("spotify_user_id")
                ),
                song=song,
                rating=user_rating,
            )

            skip_song(request, access_token)
            current_song_info = get_current_song(request)

            if current_song_info:
                song = Song.objects.get(track_id=current_song_info["track_id"])

                current_song_info = {
                    "song": song,
                    "track_name": song.title,
                    "artist_name": song.artist_name,
                }

            else:
                return redirect("thank_you")

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

            songs = Song.objects.filter(track_id=current_track["item"]["id"]).count()
            if songs > 1:
                songs = Song.objects.filter(track_id=current_track["items"]["id"])
                for song in songs:
                    song.delete()

            try:
                song = Song.objects.get(track_id=current_track["item"]["id"])
                return {
                    "song": song,
                    "track_name": song.title,
                    "artist_name": song.artist_name,
                    "track_id": song.track_id,
                }
            except Song.DoesNotExist as e:
                track_name = current_track["item"]["name"]
                artist = ", ".join(
                    [artist["name"] for artist in current_track["item"]["artists"]]
                )

                popularity = current_track["item"]["popularity"]
                track_id = current_track["item"]["id"]
                features = get_features(request)
                genre_pks = []
                for item in features.get("genres"):
                    genre, created = Genre.objects.get_or_create(name=item)
                    genre_pks.append(genre.pk)
                song = Song.objects.create(track_id=track_id)

                song.title = track_name
                song.popularity = popularity
                song.artist_name = artist
                song.track_id = track_id
                song.valence = features.get("valence")
                song.tempo = features.get("tempo")
                song.danceability = features.get("danceability")
                song.energy = features.get("energy")
                song.key = features.get("key")
                song.speechiness = features.get("speechiness")
                song.acousticness = features.get("acousticness")
                song.instrumentalness = features.get("instrumentalness")
                song.liveness = features.get("liveness")

                song.save()

                song.genres.add(*genre_pks)

                return {
                    "song": song,
                    "track_name": song.title,
                    "artist_name": song.artist_name,
                    "track_id": song.track_id,
                }

    return None


def get_features(request):
    access_token = request.session.get("token_info").get("access_token")

    token_info = request.session.get("token_info")

    if token_info:
        sp = spotipy.Spotify(auth=token_info["access_token"])

        current_track = sp.current_user_playing_track()

        track_id = current_track["item"]["id"]

        headers = {"Authorization": f"Bearer {access_token}"}

        audio_features_url = f"https://api.spotify.com/v1/audio-features/{track_id}"
        audio_response = requests.get(audio_features_url, headers=headers)

        if audio_response.status_code == 200:
            audio_features = audio_response.json()
            tempo = audio_features.get("tempo")
            valence = audio_features.get("valence")
            danceability = audio_features.get("danceability")
            energy = audio_features.get("energy")
            key = audio_features.get("key")
            speechiness = audio_features.get("speechiness")
            acousticness = audio_features.get("acousticness")
            instrumentalness = audio_features.get("instrumentalness")
            liveness = audio_features.get("liveness")

            track_info_url = f"https://api.spotify.com/v1/tracks/{track_id}"
            track_info_response = requests.get(track_info_url, headers=headers)

            if track_info_response.status_code == 200:
                track_info = track_info_response.json()
                artist_id = track_info["artists"][0]["id"]

                artist_info_url = f"https://api.spotify.com/v1/artists/{artist_id}"
                artist_response = requests.get(artist_info_url, headers=headers)

                if artist_response.status_code == 200:
                    artist_info = artist_response.json()
                    genres = artist_info.get("genres")

                return {
                    "valence": valence,
                    "tempo": tempo,
                    "danceability": danceability,
                    "energy": energy,
                    "key": key,
                    "speechiness": speechiness,
                    "acousticness": acousticness,
                    "instrumentalness": instrumentalness,
                    "liveness": liveness,
                    "genres": genres,
                }
