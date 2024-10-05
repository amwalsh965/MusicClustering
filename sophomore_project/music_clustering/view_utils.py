from models import Song, Rating, User
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Sample data: Rows represent users, columns represent genre preferences (ratings from 1 to 10)
user_data = np.array(
    [
        [8, 2, 5, 6, 7],  # User 1: Prefers pop, dislikes metal, average for others
        [7, 3, 6, 8, 6],  # User 2: Likes pop and rock
        [1, 9, 2, 1, 2],  # User 3: Dislikes pop, prefers metal
        [2, 10, 1, 2, 1],  # User 4: Heavy metal fan
        [6, 3, 7, 6, 5],  # User 5: Balanced tastes
    ]
)

# Assume we want to cluster users into 2 groups (you can adjust the number of clusters)
num_clusters = 2

# Normalize the data to ensure all genres are weighted equally
scaler = StandardScaler()
scaled_data = scaler.fit_transform(user_data)

# Apply K-means clustering
kmeans = KMeans(n_clusters=num_clusters, random_state=0)
kmeans.fit(scaled_data)

# Get the cluster assignments for each user
user_clusters = kmeans.labels_

# Define some example songs that belong to different genres (same order as genres in user data)
songs = {
    "pop": ["Song A", "Song B", "Song C"],
    "metal": ["Song D", "Song E", "Song F"],
    "jazz": ["Song G", "Song H", "Song I"],
    "rock": ["Song J", "Song K", "Song L"],
    "hip-hop": ["Song M", "Song N", "Song O"],
}


# Recommend songs to a new user based on their cluster
def recommend_songs(new_user_ratings):
    # Normalize new user input
    scaled_new_user = scaler.transform([new_user_ratings])

    # Predict the cluster for the new user
    cluster = kmeans.predict(scaled_new_user)[0]

    print(f"New user assigned to cluster: {cluster}")

    # Based on the cluster, recommend top songs from the most preferred genre
    # For simplicity, we recommend songs from the user's top-rated genres
    top_genre_index = np.argmax(new_user_ratings)
    genre_list = list(songs.keys())
    recommended_genre = genre_list[top_genre_index]

    print(f"Based on your preferences, we recommend these {recommended_genre} songs:")
    for song in songs[recommended_genre]:
        print(f"- {song}")


# Example: New user rating input
new_user = [7, 3, 6, 8, 5]  # New user likes pop, rock, and hip-hop
recommend_songs(new_user)


def rate_song():
    pass


def spotify(user_name, track_name):
    try:
        song = Song.objects.get(title=track_name)
    except Song.DoesNotExist as e:
        song = Song.objects.create(title=track_name)

    user = User.objects.get(user_name=user_name)
