import os
import requests
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# --- GENRES ---

def fetch_genre_map():
    url = f"{TMDB_BASE_URL}/genre/movie/list"
    params = {"api_key": TMDB_API_KEY}
    response = requests.get(url, params=params)
    genre_map = {}

    if response.status_code == 200:
        for genre in response.json().get("genres", []):
            genre_map[genre["name"].lower()] = genre["id"]

    return genre_map

GENRE_MAP = fetch_genre_map()

def extract_genres(prompt):
    included, excluded = [], []
    prompt = prompt.lower()

    for name, gid in GENRE_MAP.items():
        if f"not {name}" in prompt or f"without {name}" in prompt:
            excluded.append(gid)
        elif name in prompt:
            included.append(gid)

    return included, excluded

# --- KEYWORDS ---

KEYWORD_MAP = {
    "pirate": "pirates",
    "space": "space",
    "robot": "robot",
    "superhero": "superhero",
    "spy": "spy",
    "underwater": "underwater"
}

def extract_keywords(prompt):
    keyword_ids = []
    prompt = prompt.lower()

    for word, keyword_term in KEYWORD_MAP.items():
        if word in prompt:
            url = f"{TMDB_BASE_URL}/search/keyword"
            params = {"api_key": TMDB_API_KEY, "query": keyword_term}
            res = requests.get(url, params=params).json()
            if res.get("results"):
                keyword_ids.append(res["results"][0]["id"])

    return keyword_ids

# --- ACTORS ---

def get_actor_id(name):
    if not name or len(name) < 3:
        return None

    url = f"{TMDB_BASE_URL}/search/person"
    params = {"api_key": TMDB_API_KEY, "query": name}
    res = requests.get(url, params=params).json()
    if res.get("results"):
        return res["results"][0]["id"]
    return None

def extract_actor_names(prompt):
    words = prompt.lower().split()
    possible_names = []

    for i in range(len(words) - 1):
        first, second = words[i], words[i + 1]

        # skip obvious non-name phrases
        skip_words = {"movie", "film", "not", "horror", "funny", "pirate", "comedy", "with", "and"}
        if first in skip_words or second in skip_words:
            continue

        name = f"{first} {second}"
        possible_names.append(name)

    matched_names = []
    for name in possible_names:
        actor_id = get_actor_id(name)
        print(f"🎭 Actor lookup for '{name}': {actor_id}")
        if actor_id:
            matched_names.append(name)

    return list(set(matched_names))


# --- SIMILAR MOVIE SEARCH ---

def search_similar_to_movie(prompt, max_results=6):
    lowered = prompt.lower()
    if "like " in lowered:
        title = lowered.split("like ")[-1]
    elif "similar to " in lowered:
        title = lowered.split("similar to ")[-1]
    else:
        return []

    url = f"{TMDB_BASE_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}
    res = requests.get(url, params=params).json()
    results = res.get("results")
    if not results:
        return []

    movie_id = results[0]["id"]

    url = f"{TMDB_BASE_URL}/movie/{movie_id}/similar"
    params = {"api_key": TMDB_API_KEY}
    res = requests.get(url, params=params).json()
    similar_movies = res.get("results", [])[:max_results]

    final = []
    for movie in similar_movies:
        final.append({
            "title": movie.get("title"),
            "overview": movie.get("overview", ""),
            "release_date": movie.get("release_date", ""),
            "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "tmdb_link": f"https://www.themoviedb.org/movie/{movie['id']}",
            "genre": "",
            "cast": "N/A",
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count")
        })

    return final

# --- MAIN FUNCTION ---

def search_movies_by_prompt(prompt, max_results=6):
    included_genres, excluded_genres = extract_genres(prompt)
    keyword_ids = extract_keywords(prompt)
    actor_names = extract_actor_names(prompt)

    actor_ids = []
    for name in actor_names:
        actor_id = get_actor_id(name)
        if actor_id:
            actor_ids.append(actor_id)

    if "like " in prompt.lower() or "similar to " in prompt.lower():
        return search_similar_to_movie(prompt, max_results)

    # debug output
    print("\n📥 Prompt:", prompt)
    print("Included genres:", included_genres)
    print("Excluded genres:", excluded_genres)
    print("Keyword IDs:", keyword_ids)
    print("Actor names:", actor_names)
    print("Actor IDs:", actor_ids)

    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "popularity.desc",
        "with_genres": ",".join(map(str, included_genres)) if included_genres else None,
        "without_genres": ",".join(map(str, excluded_genres)) if excluded_genres else None,
        "with_keywords": ",".join(map(str, keyword_ids)) if keyword_ids else None,
        "with_cast": ",".join(map(str, actor_ids)) if actor_ids else None
    }

    res = requests.get(url, params={k: v for k, v in params.items() if v})
    results_json = res.json() if res.status_code == 200 else {}
    movies = results_json.get("results", [])

    print("🎬 Results returned:", len(movies))

    # fallback logic
    if not movies and (excluded_genres or keyword_ids or actor_ids):
        print("⚠️ Fallback: retrying with simpler filters")
        fallback_params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "popularity.desc",
            "with_cast": ",".join(map(str, actor_ids)) if actor_ids else None,
            "with_genres": ",".join(map(str, included_genres)) if included_genres else None
        }
        res = requests.get(url, params={k: v for k, v in fallback_params.items() if v})
        movies = res.json().get("results", []) if res.status_code == 200 else []
        print("🔁 Fallback results:", len(movies))

    results = []
    for movie in movies[:max_results]:
        results.append({
            "title": movie.get("title"),
            "overview": movie.get("overview", ""),
            "release_date": movie.get("release_date", ""),
            "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "tmdb_link": f"https://www.themoviedb.org/movie/{movie['id']}",
            "genre": ", ".join([k for k, v in GENRE_MAP.items() if v in included_genres]),
            "cast": ", ".join(actor_names) if actor_names else "N/A",
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count")
        })

    return results

# fetch trending movies (weekly)
def get_trending_movies():
    url = f"{TMDB_BASE_URL}/trending/movie/week"
    params = {"api_key": TMDB_API_KEY}
    res = requests.get(url, params=params).json()

    # poster_url
    movies = res.get("results", [])
    for movie in movies:
        movie["poster_url"] = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None

    return movies

# fetch popular movies
def get_popular_movies():
    url = f"{TMDB_BASE_URL}/movie/popular"
    params = {"api_key": TMDB_API_KEY}
    res = requests.get(url, params=params).json()

    # poster_url
    movies = res.get("results", [])
    for movie in movies:
        movie["poster_url"] = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None

    return movies