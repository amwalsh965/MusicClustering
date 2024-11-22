import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances_argmin_min
from .models import Song, Rating, Genre, User


# For clustering Un-rated Music
def cluster_unrated(genre):
    songs = Song.objects.all().values(
        "id", "popularity", "valence", "tempo", "danceability", "energy"
    )
    song_data = pd.DataFrame(songs).dropna()

    scaler = StandardScaler()
    scaled_song_data = scaler.fit_transform(
        song_data[["popularity", "valence", "tempo", "danceability", "energy"]]
    )

    kmeans = KMeans(n_clusters=10, random_state=42)
    kmeans.fit(scaled_song_data)

    song_data["cluster"] = kmeans.labels_

    for index, row in song_data.iterrows():
        Song.objects.filter(id=row["id"]).update(cluster=row["cluster"])


def cluster_all_unrated(num_genres):

    genres = {}
    for song in Song.objects.all():
        song: Song
        if song.genres.name in genres:
            genres[song.genres.name] += 1
        else:
            genres[song.genres.name] = 1

    sorted_genres = dict(sorted(genres.items(), key=lambda item: item[1], reverse=True))

    top_genres = []
    sorted_genre_keys = sorted_genres.keys
    for i in range(0, num_genres):
        top_genres.append(sorted_genre_keys[i])

    for top_genre in top_genres:
        cluster_all_unrated(top_genre)


# For clustering rated music
def get_top_genres(num_genres, ratings):
    songs = []
    for rating in ratings:
        songs.append(rating.song)
    genres = {}
    for song in songs:
        song: Song
        if song.genres.name in genres:
            genres[song.genres.name] += 1
        else:
            genres[song.genres.name] = 1

    sorted_genres = dict(sorted(genres.items(), key=lambda item: item[1], reverse=True))

    top_genres = []
    sorted_genre_keys = sorted_genres.keys
    for i in range(0, num_genres):
        top_genres.append(sorted_genre_keys[i])

    return top_genres


def get_song_features(user, genre, ratings):
    songs = []
    for rating in ratings:
        songs.append(rating.song)

    sorted_songs = []
    for song in songs:
        song: Song
        if song.genres.name is genre:
            sorted_songs.append(song)
    song_data = []

    for song in sorted_songs:
        song_data.append(
            [
                song.popularity,
                song.valence,
                song.tempo,
                song.danceability,
                song.energy,
                song.key,
                song.speechiness,
                song.acousticness,
                song.instrumentalness,
                song.liveness,
            ]
        )

    df = pd.DataFrame(
        song_data,
        columns=[
            "popularity",
            "valence",
            "tempo",
            "danceability",
            "energy",
            "key",
            "speechiness",
            "acousticness",
            "instrumentalness",
            "liveness",
        ],
    )

    return df


def preprocess_data(df):
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df)
    return scaled_data


def apply_kmeans(df, k=10):
    kmeans = KMeans(n_clusters=k, random_state=42)
    clusters = kmeans.fit_predict(df)
    return clusters, kmeans


def recommend_songs(user: User, genre):
    user_ratings = Rating.objects.filter(user=user)
    # Get the song features and assign clusters
    df = get_song_features(user, genre)
    scaled_data = preprocess_data(df)
    clusters, kmeans = apply_kmeans(scaled_data)

    # Find the closest cluster to the user's ratings (based on distance to cluster centroids)
    user_vector = [
        user_rating.rating for user_rating in user_ratings
    ]  # Create a vector from user ratings
    user_cluster = kmeans.predict([user_vector])[0]

    # Find all songs in the same cluster
    cluster_songs = Song.objects.exclude(rated_by=user.pk).filter(
        id__in=[i for i, cluster in enumerate(clusters) if cluster == user_cluster]
    )

    return cluster_songs
