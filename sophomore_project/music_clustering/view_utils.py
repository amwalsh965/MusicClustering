from .models import Song, Genre
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pandas as pd
from django.db import transaction


# Preclusters songs for k-means clustering by genre
def precluster_songs_by_genre(top_genres, n_clusters=10):
    for genre in top_genres:
        print(f"Clustering songs for genre: {genre}")

        # Fetch songs for the genre
        songs = Song.objects.filter(genres=Genre.objects.get(name=genre)).values(
            "id", "popularity", "valence", "tempo", "danceability", "energy"
        )
        song_data = pd.DataFrame(songs).dropna()

        # Skip clustering if there aren't enough songs
        if len(song_data) < n_clusters:
            print(f"Not enough songs to cluster for genre: {genre}")
            continue

        # Scale the features
        scaler = StandardScaler()
        scaled_song_data = scaler.fit_transform(
            song_data[["popularity", "valence", "tempo", "danceability", "energy"]]
        )

        # Apply KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        song_data["cluster"] = kmeans.fit_predict(scaled_song_data)

        # Update the database with cluster labels
        for index, row in song_data.iterrows():
            Song.objects.filter(id=row["id"]).update(cluster=row["cluster"])


# Recommends a set number of songs to a user based on genre_name
def recommend_songs_by_genre(user, genre_name, num_songs):
    from .models import Song, Rating
    import numpy as np

    # Fetch user's rated songs for the specified genre
    user_ratings = Rating.objects.filter(user=user, song__genres__name=genre_name)
    if not user_ratings.exists():
        print(f"No ratings found for user in genre: {genre_name}")
        return []

    # Compute the user's preference vector for the genre
    user_vector = np.mean(
        [
            [
                rating.song.popularity,
                rating.song.valence,
                rating.song.tempo,
                rating.song.danceability,
                rating.song.energy,
            ]
            for rating in user_ratings
        ],
        axis=0,
    )

    # Fetch pre-clustered songs for the genre, excluding already rated ones
    genre_songs = Song.objects.filter(genres__name=genre_name).exclude(rated_by=user)
    if not genre_songs.exists():
        print(f"No unrated songs available for genre: {genre_name}")
        return []

    # Group songs by cluster
    clusters = {}
    for song in genre_songs:
        cluster_id = song.cluster
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(song)

    # Compute the distance from the user's preference vector to each cluster's centroid
    cluster_centroids = {}
    for cluster_id, songs in clusters.items():

        centroid = np.mean(
            [
                [
                    song.popularity,
                    song.valence,
                    song.tempo,
                    song.danceability,
                    song.energy,
                ]
                for song in songs
            ],
            axis=0,
        )
        cluster_centroids[cluster_id] = centroid

    # Find the closest cluster
    closest_cluster = min(
        cluster_centroids.keys(),
        key=lambda cluster_id: np.linalg.norm(
            cluster_centroids[cluster_id] - user_vector
        ),
    )

    # Recommend songs from the closest cluster
    recommended_songs = clusters[closest_cluster]
    if num_songs == 1:
        return recommended_songs[0]
    return recommended_songs[:num_songs]


# Gets the top genres in the database by number
def get_top_genres_general(num_genres=30):
    batch_size = 10000
    genres = {}
    print("Sorting Genres")
    num = 0

    with transaction.atomic():  # Ensure safe batch processing
        songs = Song.objects.prefetch_related("genres")
        for batch_start in range(0, songs.count(), batch_size):
            batch = songs[batch_start : batch_start + batch_size]
            for song in batch:
                num += 1
                print(f"Processing song {num}")
                for genre in song.genres.all():
                    if genre.name in genres:
                        genres[genre.name] += 1
                    else:
                        genres[genre.name] = 1

    sorted_genres = dict(sorted(genres.items(), key=lambda item: item[1], reverse=True))
    top_genres = list(sorted_genres.keys())
    cluster_genres = []
    print("Top Genres:", top_genres)
    for i in range(0, num_genres):
        cluster_genres.append(top_genres[i])

    return cluster_genres


# Returns a users top_genres based on number of songs rated
def get_top_genres_user(user, num_genres):
    batch_size = 10000
    genres = {}
    print("Sorting Genres")
    num = 0

    with transaction.atomic():  # Ensure safe batch processing
        songs = Song.objects.filter(rated_by=user).prefetch_related("genres")
        for batch_start in range(0, songs.count(), batch_size):
            batch = songs[batch_start : batch_start + batch_size]
            for song in batch:
                num += 1
                print(f"Processing song {num}")
                for genre in song.genres.all():
                    if genre.name in genres:
                        genres[genre.name] += 1
                    else:
                        genres[genre.name] = 1

    sorted_genres = dict(sorted(genres.items(), key=lambda item: item[1], reverse=True))
    top_genres = list(sorted_genres.keys())
    cluster_genres = []
    print("Top Genres:", top_genres)
    if len(top_genres) < num_genres:
        return top_genres
    return top_genres[:num_genres]
