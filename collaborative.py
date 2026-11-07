
import pandas as pd
import numpy as np

from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

# Load ratings dataset
ratings = pd.read_csv(
    "Dataset/ratings.dat",
    sep="::",
    engine="python",
    names=["user_id", "movie_id", "rating", "timestamp"]
)

# Load movie dataset
movies = pd.read_csv(
    "Dataset/movies.dat",
    sep="::",
    engine="python",
    encoding="latin-1",
    names=["movie_id", "title", "genres"]
)

# Create user and movie indexes
user_ids = ratings["user_id"].unique()
movie_ids = movies["movie_id"].tolist()

user_to_index = {
    user: i for i, user in enumerate(user_ids)
}

movie_to_index = {
    movie: i for i, movie in enumerate(movie_ids)
}

# Create a user-movie rating matrix
rows = ratings["user_id"].map(user_to_index)
cols = ratings["movie_id"].map(movie_to_index)

matrix = csr_matrix(
    (ratings["rating"], (rows, cols)),
    shape=(len(user_ids), len(movie_ids))
)

# Apply SVD
svd = TruncatedSVD(
    n_components=20,
    random_state=42
)

user_factors = svd.fit_transform(matrix)

# Estimate missing ratings
predicted_ratings = user_factors @ svd.components_

# Select a demo user
demo_user = 1
user_index = user_to_index[demo_user]

# Find movies already watched by this user
watched = matrix[user_index].toarray().ravel() > 0

# Rank recommended movies
scores = predicted_ratings[user_index].copy()
scores[watched] = -1

top_movies = np.argsort(scores)[::-1][:5]

print("\nRecommended movies for User", demo_user)

for index in top_movies:
    movie_id = movie_ids[index]

    title = movies.loc[
        movies["movie_id"] == movie_id, "title"
    ].iloc[0]

    print(title, "-", round(scores[index], 2))
