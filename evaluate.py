
import pandas as pd
import numpy as np

from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# 1. Load dataset
ratings = pd.read_csv(
    "Dataset/ratings.dat",
    sep="::",
    engine="python",
    names=["user_id", "movie_id", "rating", "timestamp"]
)

movies = pd.read_csv(
    "Dataset/movies.dat",
    sep="::",
    engine="python",
    encoding="latin-1",
    names=["movie_id", "title", "genres"]
)

# 2. Split dataset
train, test = train_test_split(
    ratings,
    test_size=0.2,
    random_state=42
)

# 3. Create ID mappings
user_ids = ratings["user_id"].unique()
movie_ids = movies["movie_id"].tolist()

user_map = {u: i for i, u in enumerate(user_ids)}
movie_map = {m: i for i, m in enumerate(movie_ids)}

# 4. Calculate each user's average rating
user_means = train.groupby("user_id")["rating"].mean()
global_mean = train["rating"].mean()

# 5. Subtract user averages from ratings
centered_ratings = train["rating"] - train["user_id"].map(user_means)

rows = train["user_id"].map(user_map)
cols = train["movie_id"].map(movie_map)

matrix = csr_matrix(
    (centered_ratings, (rows, cols)),
    shape=(len(user_ids), len(movie_ids))
)
interaction_matrix = csr_matrix(
    (np.ones(len(train)), (rows, cols)),
    shape=(len(user_ids), len(movie_ids))
)

# 6. Apply SVD
svd = TruncatedSVD(
    n_components=20,
    random_state=42
)

user_factors = svd.fit_transform(matrix)
predictions = user_factors @ svd.components_

# 7. Calculate predicted ratings
actual = test["rating"].to_numpy()

predicted = np.array([
    user_means.get(u, global_mean) +
    predictions[user_map[u], movie_map[m]]
    for u, m in zip(test["user_id"], test["movie_id"])
])

# Keep predictions within the 1–5 rating scale
predicted = np.clip(predicted, 1, 5)

# 8. Calculate RMSE
rmse = np.sqrt(mean_squared_error(actual, predicted))

print("IMPROVED EVALUATION RESULTS")
print("----------------------------")
print("RMSE:", round(rmse, 3))

# 9. Calculate Precision@5
precisions = []

for user in user_ids:

    user_index = user_map[user]

    watched = interaction_matrix[user_index].toarray().ravel() > 0

    scores = predictions[user_index].copy()
    scores[watched] = -np.inf

    top5 = set(np.argsort(scores)[::-1][:5])

    relevant = test[
        (test["user_id"] == user) &
        (test["rating"] >= 4)
    ]["movie_id"].map(movie_map).dropna()

    relevant = set(relevant.astype(int))

    if len(relevant) > 0:
        hits = len(top5.intersection(relevant))
        precisions.append(hits / 5)

precision_at_5 = np.mean(precisions)

print("Precision@5:", round(precision_at_5, 3))
print("Users evaluated:", len(precisions))
