
import pandas as pd

# Read movie information
movies = pd.read_csv(
    "Dataset/movies.dat",
    sep="::",
    engine="python",
    encoding="latin-1",
    names=["movie_id", "title", "genres"]
)

# Read user ratings
ratings = pd.read_csv(
    "Dataset/ratings.dat",
    sep="::",
    engine="python",
    names=["user_id", "movie_id", "rating", "timestamp"]
)

# Read user information
users = pd.read_csv(
    "Dataset/users.dat",
    sep="::",
    engine="python",
    names=["user_id", "gender", "age", "occupation", "zip_code"]
)

print("DATASET LOADED SUCCESSFULLY!")

print("\nMovies:")
print(movies.head())

print("\nRatings:")
print(ratings.head())

print("\nUsers:")
print(users.head())

print("\nTotal movies:", len(movies))
print("Total ratings:", len(ratings))
print("Total users:", len(users))
