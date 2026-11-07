
import pandas as pd
import numpy as np
import streamlit as st

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import csr_matrix


# 1. LOAD MODEL
@st.cache_resource
def load_model():

    movies = pd.read_csv(
        "Dataset/movies.dat",
        sep="::",
        engine="python",
        encoding="latin-1",
        names=["movie_id", "title", "genres"]
    )

    ratings = pd.read_csv(
        "Dataset/ratings.dat",
        sep="::",
        engine="python",
        names=["user_id", "movie_id", "rating", "timestamp"]
    )

    # 2. CONTENT-BASED FILTERING
    tfidf = TfidfVectorizer()

    tfidf_matrix = tfidf.fit_transform(movies["genres"])

    content_similarity = cosine_similarity(tfidf_matrix)

    # 3. COLLABORATIVE FILTERING

    user_ids = ratings["user_id"].unique()
    movie_ids = movies["movie_id"].tolist()

    user_to_index = {
        user: i for i, user in enumerate(user_ids)
    }

    movie_to_index = {
        movie: i for i, movie in enumerate(movie_ids)
    }

    rows = ratings["user_id"].map(user_to_index)
    cols = ratings["movie_id"].map(movie_to_index)

    # Calculate each user's average rating
    user_means = ratings.groupby("user_id")["rating"].mean()

    # Centre ratings around each user's average
    centered_ratings = (
        ratings["rating"] -
        ratings["user_id"].map(user_means)
    )

    # Create the rating matrix
    rating_matrix = csr_matrix(
        (centered_ratings, (rows, cols)),
        shape=(len(user_ids), len(movie_ids))
    )

    # 4. APPLY SVD
    svd = TruncatedSVD(
        n_components=20,
        random_state=42
    )

    user_factors = svd.fit_transform(rating_matrix)

    predicted_ratings = user_factors @ svd.components_

    # Add each user's average rating back
    user_mean_values = np.array([
        user_means.get(user, ratings["rating"].mean())
        for user in user_ids
    ])

    predicted_ratings += user_mean_values[:, np.newaxis]

    return (
        movies,
        content_similarity,
        predicted_ratings,
        user_to_index
    )


# 5. NORMALIZE SCORES
def normalize(scores):

    minimum = scores.min()
    maximum = scores.max()

    if maximum == minimum:
        return np.zeros_like(scores)

    return (scores - minimum) / (maximum - minimum)


# 6. HYBRID RECOMMENDATION
def recommend_hybrid(movie_name, user_id=1):

    movies, content_similarity, predicted_ratings, user_to_index = load_model()

    matches = movies[
        movies["title"].str.contains(
            movie_name,
            case=False,
            regex=False
        )
    ]

    if matches.empty:
        return None

    if user_id not in user_to_index:
        return None

    movie_index = matches.index[0]
    user_index = user_to_index[user_id]

    # Content-based scores
    content_scores = normalize(
        content_similarity[movie_index].copy()
    )

    # Collaborative scores
    collab_scores = normalize(
        predicted_ratings[user_index].copy()
    )

    # Combine both scores
    hybrid_scores = (
        0.5 * content_scores +
        0.5 * collab_scores
    )

    # Exclude the selected movie
    hybrid_scores[movie_index] = -1

    # Select the top 5 movies
    top_movies = np.argsort(hybrid_scores)[::-1][:5]

    results = []

    for index in top_movies:

        results.append({
            "Movie": movies.iloc[index]["title"],
            "Hybrid Score": round(
                float(hybrid_scores[index]), 3
            )
        })

    return pd.DataFrame(results)
