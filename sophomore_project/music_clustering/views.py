import json
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

from itertools import islice


def home(request):
    return render(request, "../templates/home.html")


def song_recommendation(request):
    return render(request, "../templates/song_recommendations.html")


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

    print(response.status_code)
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
        # TODO need to disable the submit button when there is no song
        data = json.loads(request.body)
        # data = request.POST
        song_id = data.get("song")
        user_rating = data.get("rating")

        if song_id and user_rating:
            try:
                song = Song.objects.get(pk=song_id)
            except Song.DoesNotExist:
                current_song_info = get_current_song(request)
                song = current_song_info.get("song")

            user = User.objects.get(spotify_id=request.session.get("spotify_user_id"))

            Rating.objects.create(
                user=user,
                song=song,
                rating=user_rating,
            )

            song.rated_by.add(user.pk)

            skip_song(request, access_token)
            current_song_info = get_current_song(request)

            if current_song_info:
                song = Song.objects.get(track_id=current_song_info["track_id"])

                print(f"img_src: {song.img_src}")
                print(song.artist_name)

                current_song_info = {
                    "song": song,
                    "track_name": song.title,
                    "artist_name": song.artist_name,
                    "img_src": song.img_src,
                }

            else:
                return redirect("thank_you")

    return render(
        request,
        "../templates/SongChoice.html",
        {
            "current_song_info": current_song_info,
        },
    )


sp_oauth = SpotifyOAuth(
    client_id=settings.SPOTIFY_CLIENT_ID,
    client_secret=settings.SPOTIFY_CLIENT_SECRET,
    redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    scope="user-modify-playback-state user-read-currently-playing user-read-playback-state playlist-read-private",
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

            song = add_song(current_track, request, "item")

            if song is not None:
                return {
                    "song": song,
                    "track_name": song.title,
                    "artist_name": song.artist_name,
                    "track_id": song.track_id,
                    "img_src": song.img_src,
                }

    return None


def add_song(current_track, request, word):
    songs = Song.objects.filter(track_id=current_track[str(word)]["id"]).count()
    if songs > 1:
        songs = Song.objects.filter(track_id=current_track[str(word)]["id"])
        for song in songs:
            song.delete()

    try:
        song = Song.objects.get(track_id=current_track[str(word)]["id"])
        return song

    except Song.DoesNotExist as e:
        track_name = current_track[str(word)]["name"]
        artist = ", ".join(
            [artist["name"] for artist in current_track[str(word)]["artists"]]
        )

        popularity = current_track[str(word)]["popularity"]
        track_id = current_track[str(word)]["id"]
        img_src = current_track[str(word)]["album"]["images"][1]["url"]
        features = get_features(current_track, request, word)
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
        song.img_src = img_src

        song.save()

        song.genres.add(*genre_pks)

        return song


def add_all_playlist_songs(playlist_id, request):
    access_token = request.session.get("token_info").get("access_token")
    if not access_token:
        print("Invalid token info.")
        return None

    headers = {"Authorization": f"Bearer {access_token}"}
    song_ids = []
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    params = {"limit": 100}  # Fetch up to 100 items per request

    while url:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            print(f"Rate limited. Retry after {retry_after} seconds.")
            time.sleep(retry_after)
            continue

        if response.status_code != 200:
            print(f"Failed to fetch tracks. Status code: {response.status_code}")
            return None

        data = response.json()
        items = data.get("items", [])
        for item in items:
            track = item.get("track")
            if track:
                song_ids.append(track)

        # Check for next page
        url = data.get("next")  # Spotify provides the next page URL

    return song_ids


def get_features(current_track, request, word, wait_time=0):
    time.sleep(wait_time)
    print(f"sleeping for {wait_time} seconds")
    input("press")
    access_token = request.session.get("token_info").get("access_token")

    token_info = request.session.get("token_info")

    if token_info:
        track_id = current_track[str(word)]["id"]

        headers = {"Authorization": f"Bearer {access_token}"}
        print(track_id)

        audio_features_url = f"https://api.spotify.com/v1/audio-features/{track_id}"
        audio_response = requests.get(audio_features_url, headers=headers)

        if audio_response.status_code == 429:
            retry_after = int(audio_response.headers.get("Retry-After", 1))
            print(f"Rate limited. Retry after {retry_after} seconds.")
            print(audio_response.headers)
            get_features(current_track, request, word, retry_after)

        elif audio_response.status_code == 200:
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

            if track_info_response.status_code == 429:
                retry_after = int(audio_response.headers.get("Retry-After", 1))
                print(f"Rate limited. Retry after {retry_after} seconds.")
                print(audio_response.headers)
                get_features(current_track, request, word, retry_after)

            elif track_info_response.status_code == 200:
                track_info = track_info_response.json()
                artist_id = track_info["artists"][0]["id"]

                artist_info_url = f"https://api.spotify.com/v1/artists/{artist_id}"
                artist_response = requests.get(artist_info_url, headers=headers)

                if artist_response.status_code == 429:
                    retry_after = int(audio_response.headers.get("Retry-After", 1))
                    print(f"Rate limited. Retry after {retry_after} seconds.")
                    print(audio_response.headers)
                    get_features(current_track, request, word, retry_after)

                elif artist_response.status_code == 200:
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


def chunked_iterable(iterable, size):
    """Helper function to split an iterable into chunks of a specific size."""
    it = iter(iterable)
    while chunk := list(islice(it, size)):
        yield chunk


def get_features_batch(tracks, request):
    access_token = request.session.get("token_info").get("access_token")
    token_info = request.session.get("token_info")

    if not token_info:
        print("Invalid token info.")
        return None

    headers = {"Authorization": f"Bearer {access_token}"}

    track_list = []
    track_ids = []
    for track in tracks:
        try:
            Song.objects.get(track_id=track["id"])
        except Song.MultipleObjectsReturned:
            songs = Song.objects.filter(track_id=track["id"]).all()
            for song in songs:
                song.delete
            if track["artists"] is not None and track is not None:
                track_list.append(track)
                track_ids.append(track["id"])
        except Song.DoesNotExist:
            if track["id"] is not None and track["artists"] is not None:
                track_list.append(track)
                track_ids.append(track["id"])
            else:
                print("track id is None")

    # 1. Batch request for audio features
    features_list = []
    for track_ids_chunk in chunked_iterable(
        track_ids, 100
    ):  # Audio features support up to 100 IDs per request
        audio_features_url = (
            f"https://api.spotify.com/v1/audio-features?ids={','.join(track_ids_chunk)}"
        )
        audio_response = requests.get(audio_features_url, headers=headers)

        if audio_response.status_code == 429:
            retry_after = int(audio_response.headers.get("Retry-After", 1))
            print(f"Rate limited. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            input("press")
            continue  # Retry after waiting

        if audio_response.status_code != 200:
            print("Failed to fetch audio features.")
            return None

        audio_features_data = audio_response.json().get("audio_features", [])
        features_list.extend(audio_features_data)

    # 2. Batch request for track info
    track_info_data = []
    for track_ids_chunk in chunked_iterable(
        track_ids, 20
    ):  # Tracks endpoint supports up to 20 IDs per request
        track_info_url = (
            f"https://api.spotify.com/v1/tracks?ids={','.join(track_ids_chunk)}"
        )
        track_info_response = requests.get(track_info_url, headers=headers)

        if audio_response.status_code == 429:
            retry_after = int(audio_response.headers.get("Retry-After", 1))
            print(f"Rate limited. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            input("press")
            continue  # Retry after waiting

        if track_info_response.status_code != 200:
            print("Failed to fetch track info.")
            return None

        track_info_data.extend(track_info_response.json().get("tracks", []))

    # 3. Extract artist IDs
    artist_ids = {
        track["artists"][0]["id"] for track in track_info_data if (track is not None)
    }

    # 4. Batch request for artist genres
    artist_genres = {}
    for artist_ids_chunk in chunked_iterable(
        artist_ids, 20
    ):  # Artists endpoint supports up to 20 IDs per request
        artist_info_url = (
            f"https://api.spotify.com/v1/artists?ids={','.join(artist_ids_chunk)}"
        )
        artist_response = requests.get(artist_info_url, headers=headers)

        if audio_response.status_code == 429:
            retry_after = int(audio_response.headers.get("Retry-After", 1))
            print(f"Rate limited. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            input("press")
            continue  # Retry after waiting

        if artist_response.status_code != 200:
            print("Failed to fetch artist info.")
            return None

        for artist in artist_response.json().get("artists", []):
            artist_genres[artist["id"]] = artist.get("genres", [])

    # 5. Combine the data
    for audio_features, track in zip(features_list, track_info_data):
        if not audio_features or not track:
            continue

        artist_id = track["artists"][0]["id"]
        genres = artist_genres.get(artist_id, [])

        track_name = track["name"]
        artist = ", ".join([artist["name"] for artist in track["artists"]])

        popularity = track["popularity"]
        track_id = track["id"]
        img_src = ""
        try:
            img_src = track["album"]["images"][1]["url"]
        except IndexError:
            img_src = ""

        genre_pks = []

        for item in genres:
            genre, created = Genre.objects.get_or_create(name=item)
            genre_pks.append(genre.pk)

        song = Song.objects.create(
            title=track_name,
            popularity=popularity,
            artist_name=artist,
            track_id=track_id,
            valence=audio_features.get("valence"),
            tempo=audio_features.get("tempo"),
            danceability=audio_features.get("danceability"),
            energy=audio_features.get("energy"),
            key=audio_features.get("key"),
            speechiness=audio_features.get("speechiness"),
            acousticness=audio_features.get("acousticness"),
            instrumentalness=audio_features.get("instrumentalness"),
            liveness=audio_features.get("liveness"),
            img_src=img_src,
        )

        song.genres.add(*genre_pks)
        track_print = track["id"]
        print(f"finished creating song {track_print}")


def add_playlist_songs(request):
    print("starting")
    songs = Song.objects.all()
    counter = 0
    for song in songs:
        counter += 1
        print(f"song {counter}")
        try:
            Song.objects.get(track_id=song.track_id)
        except Song.MultipleObjectsReturned:
            id_songs = Song.objects.filter(track_id=song.track_id)
            for song_id in id_songs:
                if Song.objects.filter(track_id=song_id.track_id).count() > 1:
                    song_id.delete()
                    print("Deleting Duplicate")
                else:
                    songs = Song.objects.all()

    """playlist_urls = [
    ]

    for playlist in playlist_urls:
        print(f"looking at playlist: {playlist}")
        track_list = add_all_playlist_songs(playlist, request)
        print(len(track_list))
        get_features_batch(track_list, request)"""
