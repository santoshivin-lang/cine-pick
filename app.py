
import streamlit as st
import html
import requests
import re

from hybrid import recommend_hybrid, load_model


# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="CINE PICK",
    page_icon="🎬",
    layout="wide"
)


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
</style>
""", unsafe_allow_html=True)


# ---------------- TMDB POSTER FUNCTION ----------------

@st.cache_data(ttl=86400)
def get_movie_poster(title):

    try:
        api_key = st.secrets["TMDB_API_KEY"]

        year_match = re.search(r"\((\d{4})\)$", title)
        year = year_match.group(1) if year_match else None

        search_title = re.sub(r"\s*\(\d{4}\)$", "", title)

        if ", The" in search_title:
            search_title = "The " + search_title.replace(", The", "")
        elif ", A" in search_title:
            search_title = "A " + search_title.replace(", A", "")
        elif ", An" in search_title:
            search_title = "An " + search_title.replace(", An", "")

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
    the MovieLens dataset.

    It combines two recommendation techniques:

    - Content-Based Filtering
    - Collaborative Filtering

    These are combined using a Hybrid Recommendation Model.
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


# ---------------- BROWSE BY GENRE ----------------

st.divider()

st.header("🎭 Browse Movies by Genre")

st.write(
    "Explore movies from your favourite categories!"
)

if "genres" in movies.columns:

    # Extract all available genres from the dataset
    all_genres = sorted({
        genre
        for genre_list in movies["genres"].dropna()
        for genre in str(genre_list).split("|")
        if genre and genre != "(no genres listed)"
    })

    selected_genre = st.selectbox(
        "Choose a genre:",
        all_genres,
        key="genre_selector"
    )

    # Filter movies belonging to the selected genre
    genre_movies = movies[
        movies["genres"].fillna("").apply(
            lambda x: selected_genre in str(x).split("|")
        )
    ].sort_values("title")

    st.subheader(f"🍿 {selected_genre} Movies")

    st.write(
        f"Found {len(genre_movies)} movies in this genre."
    )

    # Display the first 12 movies
    genre_movies = genre_movies.head(12)

    # Display movies in three columns
    columns = st.columns(3)

    for index, (_, movie) in enumerate(genre_movies.iterrows()):

        title = str(movie["title"])

        with columns[index % 3]:

            poster = get_movie_poster(title)

            if not poster:
                poster = poster_urls.get(title)

            if poster:
                st.image(poster, use_container_width=True)
            else:
                st.info("Poster unavailable")

            st.markdown(
                f"**{html.escape(title)}**"
            )

else:

    st.warning(
        "Genre information is unavailable in the movie dataset."
    )


# ---------------- USER INPUT ----------------

st.divider()

st.subheader("🍿 Find Your Next Favourite Movie")

movie_list = movies["title"].tolist()

selected_movie = st.selectbox(
    "Choose a movie you like:",
    movie_list,
    key="recommendation_movie"
)

user_id = st.number_input(
    "Enter User ID:",
    min_value=1,
    max_value=6040,
    value=1,
    step=1
)


# ---------------- SESSION STATE ----------------

if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

if "recommendation_error" not in st.session_state:
    st.session_state.recommendation_error = False


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

        st.markdown(
            f"### 🎬 {html.escape(title)}"
        )

        poster = get_movie_poster(title)

        if not poster:
            poster = poster_urls.get(title)

        if poster:

            st.image(
                poster,
                width=180
            )

        else:

            st.info(
                f"Poster unavailable for {html.escape(title)}"
            )

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

st.caption(
    "CINE PICK | Movie Recommendation System"
)

st.caption(
    "This product uses the TMDB API but is not endorsed or certified by TMDB."
)
