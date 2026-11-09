
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load movie dataset
movies = pd.read_csv(
    "Dataset/movies.dat",
    sep="::",
    engine="python",
    encoding="latin-1",
    names=["movie_id", "title", "genres"]
)

# Convert genres into numerical values
tfidf = TfidfVectorizer()

tfidf_matrix = tfidf.fit_transform(movies["genres"])

# Calculate similarity between movies
similarity = cosine_similarity(tfidf_matrix)

# Recommendation function
def recommend_movies(movie_name):

    # Find the movie
    matches = movies[
        movies["title"].str.contains(
            movie_name, case=False, regex=False
        )
    ]

    if matches.empty:
        print("Movie not found!")
        return

    movie_index = matches.index[0]

    # Get similarity scores
    scores = list(enumerate(similarity[movie_index]))

    # Sort from most similar to least similar
    scores = sorted(
        scores, key=lambda x: x[1], reverse=True
    )

    # Display top 5 recommendations
    print("\nMovies similar to", movies.iloc[movie_index]["title"])

    for index, score in scores[1:6]:
        print(movies.iloc[index]["title"], "-", round(score, 3))


# Test the recommendation system
recommend_movies("Toy Story")
