
import streamlit as st
import html
import requests
import re
import pandas as pd

from hybrid import recommend_hybrid, load_model


# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="CINE PICK",
    page_icon="🎬",
    layout="wide"
)


# ---------------- SESSION STATE ----------------

if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

if "indian_watchlist" not in st.session_state:
    st.session_state.indian_watchlist = []

if "show_movie_details" not in st.session_state:
    st.session_state.show_movie_details = False

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

if "recommendation_error" not in st.session_state:
    st.session_state.recommendation_error = False

if "indian_movies" not in st.session_state:
    st.session_state.indian_movies = []

if "indian_language_name" not in st.session_state:
    st.session_state.indian_language_name = "Hindi"


# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #10002b, #240046, #3c096c);
    color: white;
}

h1, h2, h3 {
    color: white;
}

.movie-card {
    background-color: rgba(255,255,255,0.10);
    padding: 18px;
    border-radius: 15px;
    margin-bottom: 10px;
}

.movie-title {
    color: white;
    font-size: 21px;
    font-weight: bold;
}

.movie-score {
    color: #e0aaff;
    font-size: 16px;
    margin-top: 8px;
}

.stButton > button {
    border-radius: 12px;
    border: 1px solid #c77dff;
    background-color: rgba(157, 78, 221, 0.25);
    color: white;
    font-weight: bold;
    min-height: 45px;
}

.stButton > button:hover {
    background-color: #7b2cbf;
    border-color: #e0aaff;
    color: white;
}
</style>
""", unsafe_allow_html=True)


def normalize_movie_title(title):
    """Convert MovieLens trailing articles to natural titles for TMDB."""
    search_title = re.sub(r"\s*\(\d{4}\)$", "", title).strip()
    for article in ("The", "An", "A"):
        suffix = f", {article}"
        if search_title.endswith(suffix):
            return f"{article} {search_title[:-len(suffix)]}"
    return search_title


# ---------------- TMDB POSTER FUNCTION ----------------

@st.cache_data(ttl=86400)
def get_movie_poster(title):

    try:
        api_key = st.secrets["TMDB_API_KEY"]

        year_match = re.search(r"\((\d{4})\)$", title)
        year = year_match.group(1) if year_match else None

        search_title = normalize_movie_title(title)

        url = "https://api.themoviedb.org/3/search/movie"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json"
        }

        params = {"query": search_title}

        if year:
            params["year"] = year

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        if data.get("results"):
            for movie in data["results"]:
                poster_path = movie.get("poster_path")

                if poster_path:
                    return (
                        "https://image.tmdb.org/t/p/w500"
                        + poster_path
                    )

        return None

    except Exception as e:
        print("TMDB ERROR:", repr(e))
        return None


# ---------------- TMDB MOVIE DETAILS FUNCTION ----------------

@st.cache_data(ttl=86400)
def get_movie_details(title):

    try:
        api_key = st.secrets["TMDB_API_KEY"]

        year_match = re.search(r"\((\d{4})\)$", title)
        year = year_match.group(1) if year_match else None

        search_title = normalize_movie_title(title)

        url = "https://api.themoviedb.org/3/search/movie"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json"
        }

        params = {"query": search_title}

        if year:
            params["year"] = year

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()
        results = response.json().get("results", [])

        if results:
            movie = results[0]

            poster_path = movie.get("poster_path")

            poster = (
                "https://image.tmdb.org/t/p/w500" + poster_path
                if poster_path else None
            )

            return {
                "overview": movie.get("overview") or "Overview unavailable.",
                "release_date": movie.get("release_date") or "Unknown",
                "rating": movie.get("vote_average"),
                "poster": poster
            }

        return None

    except Exception as e:
        print("TMDB DETAILS ERROR:", repr(e))
        return None


# ---------------- INDIAN MOVIE FETCHING FUNCTION ----------------

@st.cache_data(ttl=3600)
def get_indian_movies(language="hi", page=1):

    try:
        api_key = st.secrets["TMDB_API_KEY"]

        url = "https://api.themoviedb.org/3/discover/movie"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json"
        }

        params = {
            "with_origin_country": "IN",
            "with_original_language": language,
            "sort_by": "popularity.desc",
            "page": page
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        return response.json().get("results", [])

    except Exception as e:
        print("INDIAN MOVIES ERROR:", repr(e))
        return []


# ---------------- LOAD MOVIELENS RATINGS ----------------

@st.cache_data
def load_movie_ratings():

    ratings = pd.read_csv(
        "Dataset/ratings.dat",
        sep="::",
        engine="python",
        names=["user_id", "movie_id", "rating", "timestamp"],
        encoding="latin-1"
    )

    rating_summary = ratings.groupby("movie_id").agg(
        average_rating=("rating", "mean"),
        rating_count=("rating", "count")
    ).reset_index()

    return rating_summary


# ---------------- BACKUP POSTERS ----------------

poster_urls = {
    "Toy Story 2 (1999)": "https://image.tmdb.org/t/p/w500/2MFIhZAW0CVlEQrFyqWAuUe2cb.jpg",
    "A Bug's Life (1998)": "https://image.tmdb.org/t/p/w500/A0ILjxI2jXw0v2qJqvQ8u4m7Z5.jpg",
    "Aladdin (1992)": "https://image.tmdb.org/t/p/w500/eLFfl7vS8dkeG1hKp5mwbm37V83.jpg",
    "Beauty and the Beast (1991)": "https://image.tmdb.org/t/p/w500/b9QJr2oblOu1grgOMUZF1xkUJdh.jpg",
    "Lion King, The (1994)": "https://image.tmdb.org/t/p/w500/sKCr78MXSLixwmZ8DyJLrpMsd15.jpg"
}


# ---------------- LOAD DATA ----------------

movies, _, _, _ = load_model()

rating_summary = load_movie_ratings()

movies = movies.merge(
    rating_summary,
    on="movie_id",
    how="left"
)

movies["average_rating"] = movies["average_rating"].fillna(0)
movies["rating_count"] = movies["rating_count"].fillna(0)

movies["year"] = pd.to_numeric(
    movies["title"].str.extract(r"\((\d{4})\)$")[0],
    errors="coerce"
)

movie_list = movies["title"].tolist()


# ---------------- HEADING ----------------

st.title("🎬 CINE PICK")

st.subheader("Your Personal Movie Recommendation System")

st.write(
    "Discover movies you might love using "
    "Content-Based Filtering and Collaborative Filtering."
)


# ---------------- ABOUT ----------------

with st.expander("ℹ️ About CINE PICK"):

    st.write("""
    CINE PICK is a movie recommendation system built using
    the MovieLens dataset and TMDB API.

    It combines two recommendation techniques:

    - Content-Based Filtering
    - Collaborative Filtering

    These are combined using a Hybrid Recommendation Model.

    You can also explore Indian cinema, compare movies,
    discover genres and create your own watchlists.
    """)


# ---------------- HOW IT WORKS ----------------

with st.expander("⚙️ How CINE PICK Works"):

    st.write("""
    **1. Content-Based Filtering**

    Finds movies similar to the movie you select using genres.

    **2. Collaborative Filtering**

    Uses patterns in user ratings to predict movie preferences.

    **3. Hybrid Recommendation**

    Combines both methods to generate recommendations.
    """)


# ---------------- MATH CONCEPTS ----------------

with st.expander("📚 Mathematical Concepts Used"):

    st.write("**Cosine Similarity**")

    st.latex(
        r"Similarity(A,B)=\frac{A\cdot B}{||A||\,||B||}"
    )

    st.write(
        "It measures how similar two movies are based on their genres."
    )

    st.write("**Singular Value Decomposition (SVD)**")

    st.latex(
        r"R \approx U\Sigma V^T"
    )

    st.write(
        "SVD reduces the rating matrix into smaller factors "
        "to identify hidden patterns in user preferences."
    )


# ---------------- SEARCH MOVIES ----------------

st.divider()

st.header("🔎 Search Movies")

st.write("Looking for a particular movie? Search for it here!")

search_query = st.text_input(
    "Enter a movie name:",
    placeholder="e.g. Toy Story, Titanic, Jurassic Park...",
    key="movie_search"
)

if search_query.strip():

    search_results = movies[
        movies["title"].str.contains(
            search_query.strip(),
            case=False,
            na=False,
            regex=False
        )
    ]

    if not search_results.empty:

        st.subheader("🎬 Search Results")

        st.caption(
            f"Found {len(search_results)} matching movies "
            "(showing up to 12)."
        )

        search_columns = st.columns(4)

        for index, (_, movie) in enumerate(search_results.head(12).iterrows()):

            title = str(movie["title"])

            with search_columns[index % 4]:

                poster = get_movie_poster(title)

                if not poster:
                    poster = poster_urls.get(title)

                if poster:
                    st.image(poster, use_container_width=True)
                else:
                    st.info("Poster unavailable")

                st.markdown(f"**{html.escape(title)}**")

    else:
        st.warning("No movies found. Try another movie title!")


# ---------------- BROWSE BY GENRE ----------------

st.divider()

st.header("🎭 Explore Your Movie Universe")

st.write(
    "Pick a genre and discover your next favourite movie!"
)

if "genres" in movies.columns:

    all_genres = sorted({
        genre
        for genre_list in movies["genres"].dropna()
        for genre in str(genre_list).split("|")
        if genre and genre != "(no genres listed)"
    })

    if all_genres:

        if "selected_genre" not in st.session_state:
            st.session_state.selected_genre = all_genres[0]

        genre_columns = st.columns(4)

        for index, genre in enumerate(all_genres):

            with genre_columns[index % 4]:

                if st.button(
                    genre,
                    key=f"genre_{genre}",
                    use_container_width=True
                ):
                    st.session_state.selected_genre = genre

        selected_genre = st.session_state.selected_genre

        st.markdown("---")

        st.subheader(f"🍿 Explore {selected_genre} Movies")

        genre_movies = movies[
            movies["genres"].fillna("").apply(
                lambda x: selected_genre in str(x).split("|")
            )
        ].sort_values("title")

        st.caption(f"{len(genre_movies)} movies available")

        genre_movies = genre_movies.head(12)

        columns = st.columns(4)

        for index, (_, movie) in enumerate(genre_movies.iterrows()):

            title = str(movie["title"])

            with columns[index % 4]:

                poster = get_movie_poster(title)

                if not poster:
                    poster = poster_urls.get(title)

                if poster:
                    st.image(poster, use_container_width=True)
                else:
                    st.info("Poster unavailable")

                st.markdown(f"**{html.escape(title)}**")

    else:
        st.warning("No genres found in the dataset.")

else:
    st.warning("Genre information is unavailable in the movie dataset.")


# ---------------- MOVIE FILTERS ----------------

st.divider()

st.header("🎛️ Discover Movies with Filters")

st.write(
    "Customize your movie discovery experience "
    "using genres, release years, and ratings!"
)

filter_columns = st.columns(2)

with filter_columns[0]:

    selected_filter_genres = st.multiselect(
        "🎭 Choose genres",
        all_genres,
        placeholder="Select one or more genres",
        key="filter_genres"
    )

with filter_columns[1]:

    sort_option = st.selectbox(
        "↕️ Sort movies by",
        [
            "Highest Rated",
            "Lowest Rated",
            "Newest First",
            "Oldest First",
            "Alphabetical (A-Z)",
            "Alphabetical (Z-A)"
        ],
        key="filter_sort"
    )

valid_years = movies["year"].dropna()

if not valid_years.empty:

    min_year = int(valid_years.min())
    max_year = int(valid_years.max())

    selected_years = st.slider(
        "📅 Select release year range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        key="filter_years"
    )

else:
    selected_years = (1900, 2026)

minimum_rating = st.slider(
    "⭐ Minimum average MovieLens rating",
    min_value=0.0,
    max_value=5.0,
    value=0.0,
    step=0.5,
    key="minimum_rating"
)

filtered_movies = movies.copy()

if selected_filter_genres:

    filtered_movies = filtered_movies[
        filtered_movies["genres"].fillna("").apply(
            lambda genres: any(
                genre in str(genres).split("|")
                for genre in selected_filter_genres
            )
        )
    ]

filtered_movies = filtered_movies[
    filtered_movies["year"].between(
        selected_years[0],
        selected_years[1]
    )
]

filtered_movies = filtered_movies[
    filtered_movies["average_rating"] >= minimum_rating
]

if sort_option == "Highest Rated":

    filtered_movies = filtered_movies.sort_values(
        ["average_rating", "rating_count"],
        ascending=[False, False]
    )

elif sort_option == "Lowest Rated":

    filtered_movies = filtered_movies[
        filtered_movies["rating_count"] > 0
    ].sort_values("average_rating", ascending=True)

elif sort_option == "Newest First":

    filtered_movies = filtered_movies.sort_values(
        "year",
        ascending=False,
        na_position="last"
    )

elif sort_option == "Oldest First":

    filtered_movies = filtered_movies.sort_values(
        "year",
        ascending=True,
        na_position="last"
    )

elif sort_option == "Alphabetical (A-Z)":

    filtered_movies = filtered_movies.sort_values(
        "title",
        ascending=True
    )

elif sort_option == "Alphabetical (Z-A)":

    filtered_movies = filtered_movies.sort_values(
        "title",
        ascending=False
    )

st.markdown("---")

st.subheader("🎬 Your Filtered Movies")

st.caption(
    f"Found {len(filtered_movies)} movies matching your filters."
)

if not filtered_movies.empty:

    display_movies = filtered_movies.head(16)

    st.caption(
        "Showing up to 16 results. Change your filters "
        "to explore more movies."
    )

    filter_movie_columns = st.columns(4)

    for index, (_, movie) in enumerate(display_movies.iterrows()):

        title = str(movie["title"])

        with filter_movie_columns[index % 4]:

            poster = get_movie_poster(title)

            if not poster:
                poster = poster_urls.get(title)

            if poster:
                st.image(poster, use_container_width=True)
            else:
                st.info("Poster unavailable")

            st.markdown(f"**{html.escape(title)}**")

            if pd.notna(movie["year"]):
                st.caption(f"📅 {int(movie['year'])}")

            if movie["rating_count"] > 0:
                st.write(
                    f"⭐ {movie['average_rating']:.2f}/5"
                )
                st.caption(
                    f"{int(movie['rating_count'])} user ratings"
                )
            else:
                st.caption("No user ratings available")

else:

    st.warning(
        "No movies match these filters. "
        "Try changing your selections!"
    )


# ---------------- INDIAN CINEMA EXPLORER ----------------

st.divider()

st.header("🇮🇳 Indian Cinema")

st.write(
    "Explore movies from different Indian film industries!"
)

indian_languages = {
    "Hindi": "hi",
    "Telugu": "te",
    "Tamil": "ta",
    "Malayalam": "ml",
    "Kannada": "kn",
    "Bengali": "bn",
    "Marathi": "mr",
    "Punjabi": "pa"
}

selected_language = st.selectbox(
    "🎞️ Choose a film industry:",
    list(indian_languages.keys()),
    key="indian_language"
)

if st.button("🍿 Explore Indian Movies"):

    language_code = indian_languages[selected_language]

    indian_movies = get_indian_movies(language_code)

    st.session_state.indian_movies = indian_movies
    st.session_state.indian_language_name = selected_language

if st.session_state.indian_movies:

    indian_movies = st.session_state.indian_movies

    st.subheader(
        f"🎬 Popular {st.session_state.indian_language_name} Movies"
    )

    indian_columns = st.columns(4)

    for index, movie in enumerate(indian_movies[:20]):

        with indian_columns[index % 4]:

            title = movie.get("title", "Unknown Title")
            movie_id = movie.get("id")
            poster_path = movie.get("poster_path")
            overview = movie.get("overview")
            rating = movie.get("vote_average")

            if poster_path:

                poster = (
                    "https://image.tmdb.org/t/p/w500"
                    + poster_path
                )

                st.image(poster, use_container_width=True)

            else:
                st.info("Poster unavailable")

            st.markdown(f"**{html.escape(title)}**")

            release_date = movie.get("release_date", "")

            if release_date:
                st.caption(f"📅 {release_date[:4]}")

            if rating:
                st.write(f"⭐ {rating:.1f}/10")

            if overview:

                with st.expander("Read overview"):
                    st.write(overview)

            if st.button(
                "⭐ Add to Watchlist",
                key=f"indian_watch_{movie_id}"
            ):

                existing_ids = [
                    item["id"]
                    for item in st.session_state.indian_watchlist
                ]

                if movie_id not in existing_ids:

                    st.session_state.indian_watchlist.append({
                        "id": movie_id,
                        "title": title,
                        "poster": poster_path,
                        "overview": overview or "Overview unavailable.",
                        "rating": rating
                    })

                    st.success("Added to your Indian movie watchlist!")

                else:
                    st.info("Already in your watchlist!")

else:

    st.info(
        "Choose a language and click Explore Indian Movies "
        "to discover Indian cinema!"
    )


# ---------------- INDIAN MOVIE WATCHLIST ----------------

st.divider()

st.header("⭐ My Indian Movie Watchlist")

st.write("Your saved Indian cinema collection!")
st.caption("Your watchlist is saved only until you refresh or close this session.")

if st.session_state.indian_watchlist:

    st.subheader(
        f"🎬 Saved Indian Movies "
        f"({len(st.session_state.indian_watchlist)})"
    )

    indian_watch_columns = st.columns(3)

    for index, movie in enumerate(st.session_state.indian_watchlist):

        with indian_watch_columns[index % 3]:

            if movie["poster"]:

                poster = (
                    "https://image.tmdb.org/t/p/w500"
                    + movie["poster"]
                )

                st.image(poster, use_container_width=True)

            else:
                st.info("Poster unavailable")

            st.markdown(f"**{html.escape(movie['title'])}**")

            if movie["rating"]:
                st.write(f"⭐ {movie['rating']:.1f}/10")

            with st.expander("Read overview"):
                st.write(movie["overview"])

            if st.button(
                "❌ Remove",
                key=f"remove_indian_{movie['id']}"
            ):

                st.session_state.indian_watchlist = [
                    item
                    for item in st.session_state.indian_watchlist
                    if item["id"] != movie["id"]
                ]

                st.rerun()

else:

    st.info(
        "Your Indian movie watchlist is empty. "
        "Explore Indian Cinema and add movies!"
    )


# ---------------- MOVIE DETAILS ----------------

st.divider()

st.header("🎞️ Movie Details")

st.write("Want to know more about a movie? Select one below!")

details_movie = st.selectbox(
    "Choose a movie to explore:",
    movie_list,
    key="details_movie"
)

if st.button("🔍 Show Movie Details"):
    st.session_state.show_movie_details = True

if st.session_state.show_movie_details:

    selected_details = movies[
        movies["title"] == details_movie
    ]

    if not selected_details.empty:

        movie_row = selected_details.iloc[0]
        details = get_movie_details(details_movie)

        detail_columns = st.columns([1, 2])

        with detail_columns[0]:

            poster = details.get("poster") if details else None

            if not poster:
                poster = get_movie_poster(details_movie)

            if not poster:
                poster = poster_urls.get(details_movie)

            if poster:
                st.image(poster, use_container_width=True)
            else:
                st.info("Poster unavailable")

        with detail_columns[1]:

            st.subheader(details_movie)

            year_match = re.search(r"\((\d{4})\)$", details_movie)

            if details and details.get("release_date") != "Unknown":
                release_year = details["release_date"][:4]
            elif year_match:
                release_year = year_match.group(1)
            else:
                release_year = "Unknown"

            st.write(f"📅 **Release Year:** {release_year}")

            genres = str(movie_row["genres"]).replace("|", ", ")
            st.write(f"🎭 **Genres:** {genres}")

            st.markdown("### 📝 Overview")

            if details:

                st.write(details["overview"])

                rating = details.get("rating")

                if rating is not None:
                    st.write(f"⭐ **TMDB Rating:** {rating:.1f}/10")

            else:
                st.info(
                    "Additional movie information is currently unavailable."
                )


# ---------------- MOVIE COMPARISON ----------------

st.divider()

st.header("🎬 Compare Two Movies")

st.write(
    "Can't decide which movie to watch? "
    "Compare two movies side by side!"
)

comparison_columns = st.columns(2)

with comparison_columns[0]:

    movie_one = st.selectbox(
        "Choose the first movie:",
        movie_list,
        key="compare_movie_one"
    )

with comparison_columns[1]:

    movie_two = st.selectbox(
        "Choose the second movie:",
        movie_list,
        index=1 if len(movie_list) > 1 else 0,
        key="compare_movie_two"
    )

if st.button("⚖️ Compare Movies"):
    st.session_state.comparison_movies = (movie_one, movie_two)

if st.session_state.get("comparison_movies"):
    compared_one, compared_two = st.session_state.comparison_movies

    if compared_one == compared_two:

        st.warning("Please select two different movies!")

    else:

        first_movie = movies[
            movies["title"] == compared_one
        ].iloc[0]

        second_movie = movies[
            movies["title"] == compared_two
        ].iloc[0]

        first_details = get_movie_details(compared_one)
        second_details = get_movie_details(compared_two)

        compare_columns = st.columns(2)

        comparison_data = [
            (compared_one, first_movie, first_details),
            (compared_two, second_movie, second_details)
        ]

        for index, (title, movie, details) in enumerate(comparison_data):

            with compare_columns[index]:

                st.subheader(title)

                poster = (
                    details.get("poster")
                    if details else None
                )

                if not poster:
                    poster = get_movie_poster(title)

                if not poster:
                    poster = poster_urls.get(title)

                if poster:
                    st.image(poster, use_container_width=True)
                else:
                    st.info("Poster unavailable")

                year = movie["year"]

                if pd.notna(year):
                    st.write(f"📅 **Release Year:** {int(year)}")
                else:
                    st.write("📅 **Release Year:** Unknown")

                genres = str(movie["genres"]).replace("|", ", ")

                st.write(f"🎭 **Genres:** {genres}")

                st.write(
                    f"⭐ **Average MovieLens Rating:** "
                    f"{movie['average_rating']:.2f}/5"
                )

                st.write(
                    f"👥 **Number of User Ratings:** "
                    f"{int(movie['rating_count'])}"
                )

                st.markdown("### 📝 Overview")

                if details:

                    st.write(details["overview"])

                    tmdb_rating = details.get("rating")

                    if tmdb_rating is not None:
                        st.write(
                            f"⭐ **TMDB Rating:** "
                            f"{tmdb_rating:.1f}/10"
                        )

                else:

                    st.info(
                        "Additional movie information is unavailable."
                    )

        st.success("Movie comparison completed!")


# ---------------- MY WATCHLIST ----------------

st.divider()

st.header("⭐ My Watchlist")

st.write("Save movies you want to watch later!")
st.caption("Your watchlist is saved only until you refresh or close this session.")

watchlist_movie = st.selectbox(
    "Choose a movie to add:",
    movie_list,
    key="watchlist_movie"
)

if st.button("➕ Add to Watchlist"):

    if watchlist_movie not in st.session_state.watchlist:

        st.session_state.watchlist.append(watchlist_movie)

        st.success(f"{watchlist_movie} added to your watchlist!")

    else:

        st.info("This movie is already in your watchlist!")


# ---------------- DISPLAY WATCHLIST ----------------

if st.session_state.watchlist:

    st.subheader(
        f"🎬 Your Saved Movies ({len(st.session_state.watchlist)})"
    )

    watchlist_columns = st.columns(3)

    for index, title in enumerate(st.session_state.watchlist):

        with watchlist_columns[index % 3]:

            poster = get_movie_poster(title)

            if not poster:
                poster = poster_urls.get(title)

            if poster:
                st.image(poster, use_container_width=True)
            else:
                st.info("Poster unavailable")

            st.markdown(f"**{html.escape(title)}**")

            if st.button(
                "❌ Remove",
                key=f"remove_watchlist_{index}"
            ):

                st.session_state.watchlist.remove(title)

                st.rerun()

else:

    st.info(
        "Your watchlist is empty. Add a movie to get started!"
    )


# ---------------- USER INPUT ----------------

st.divider()

st.subheader("🍿 Find Your Next Favourite Movie")

def clear_recommendations():
    st.session_state.recommendations = None
    st.session_state.recommendation_error = False


selected_movie = st.selectbox(
    "Choose a movie you like:",
    movie_list,
    key="recommendation_movie",
    on_change=clear_recommendations
)

user_id = st.number_input(
    "Enter User ID:",
    min_value=1,
    max_value=6040,
    value=1,
    step=1,
    key="recommendation_user_id",
    on_change=clear_recommendations
)


# ---------------- RECOMMENDATION BUTTON ----------------

if st.button("✨ Find My Recommendations"):

    try:

        recommendations = recommend_hybrid(
            selected_movie,
            int(user_id)
        )

        if (
            recommendations is not None
            and not recommendations.empty
            and "Movie" in recommendations.columns
            and "Hybrid Score" in recommendations.columns
        ):

            st.session_state.recommendations = recommendations
            st.session_state.recommendation_error = False

        else:

            st.session_state.recommendations = None
            st.session_state.recommendation_error = True

    except Exception as e:

        st.session_state.recommendations = None
        st.session_state.recommendation_error = True

        st.error(f"Recommendation error: {e}")


# ---------------- DISPLAY RECOMMENDATIONS ----------------

if st.session_state.recommendations is not None:

    st.success("Your movie recommendations are ready!")

    st.subheader("🎥 Movies Picked For You")

    recommendations = st.session_state.recommendations

    for _, movie in recommendations.iterrows():

        title = str(movie["Movie"])
        score = movie["Hybrid Score"]

        st.markdown(f"### 🎬 {html.escape(title)}")

        poster = get_movie_poster(title)

        if not poster:
            poster = poster_urls.get(title)

        if poster:
            st.image(poster, width=180)
        else:
            st.info(f"Poster unavailable for {html.escape(title)}")

        st.markdown(
            f"""
            <div class="movie-card">
                <div class="movie-title">
                    {html.escape(title)}
                </div>
                <div class="movie-score">
                    Hybrid Score: {score}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()


elif st.session_state.recommendation_error:

    st.error("Movie or User ID not found.")


# ---------------- FOOTER ----------------

st.divider()

st.caption("CINE PICK | Movie Recommendation System")

st.caption(
    "This product uses the TMDB API but is not endorsed or certified by TMDB."
)
