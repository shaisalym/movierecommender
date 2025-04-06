import os
import requests
import re
from dotenv import load_dotenv
from rapidfuzz import process, fuzz

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# --- genres ---
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
    prompt_lower = prompt.lower()
    # get the list of genre names from the fetched genre map
    genre_names = list(GENRE_MAP.keys())
    # use fuzzy matching to find any genre that matches the prompt
    matches = process.extract(prompt_lower, genre_names, scorer=fuzz.partial_ratio, score_cutoff=80)
    # matches is a list of tuples: (matched_genre, score, index)
    for match in matches:
        matched_genre = match[0]
        # check if the prompt explicitly excludes this genre
        if f"not {matched_genre}" in prompt_lower or f"without {matched_genre}" in prompt_lower:
            excluded.append(GENRE_MAP[matched_genre])
        else:
            included.append(GENRE_MAP[matched_genre])
    return included, excluded

# --- keywords ---
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
    prompt_lower = prompt.lower()
    for word, keyword_term in KEYWORD_MAP.items():
        if word in prompt_lower:
            url = f"{TMDB_BASE_URL}/search/keyword"
            params = {"api_key": TMDB_API_KEY, "query": keyword_term}
            res = requests.get(url, params=params).json()
            if res.get("results"):
                keyword_ids.append(res["results"][0]["id"])
    return keyword_ids

# --- actors ---
def get_actor_id(name):
    if not name or len(name) < 3:
        return None
    try:
        url = f"{TMDB_BASE_URL}/search/person"
        params = {"api_key": TMDB_API_KEY, "query": name}
        res = requests.get(url, params=params).json()
        if res.get("results"):
            return res["results"][0]["id"]
    except Exception as e:
        print(f"error fetching actor id for {name}: {e}")
    return None

def extract_included_actor_names(prompt):
    prompt_lower = prompt.lower()
    words = prompt_lower.split()
    possible_names = []
    # generate every consecutive two-word pair, skipping obvious words
    for i in range(len(words) - 1):
        # if the previous word is "not" or "without", skip this pair
        if i > 0 and words[i-1] in {"not", "without"}:
            continue
        first, second = words[i], words[i+1]
        skip_words = {"movie", "film", "not", "without", "horror", "funny", "pirate", "comedy", "with", "and"}
        if first in skip_words or second in skip_words:
            continue
        candidate = f"{first} {second}"
        possible_names.append(candidate)
    matched_names = []
    for name in possible_names:
        actor_id = get_actor_id(name)
        print(f"🎭 actor lookup for '{name}': {actor_id}")
        if actor_id:
            matched_names.append(name)
    return list(set(matched_names))

def extract_excluded_actor_names(prompt):
    prompt_lower = prompt.lower()
    # use regex to capture two-word sequences after 'not' or 'without'
    matches = re.findall(r"(?:not|without)\s+([a-z]+\s+[a-z]+)", prompt_lower)
    return list(set(match.strip() for match in matches))

def extract_actor_names(prompt):
    included = extract_included_actor_names(prompt)
    excluded = extract_excluded_actor_names(prompt)
    print("excluded actor names:", excluded)
    # remove any included actor that exactly matches an excluded name
    final_included = [actor for actor in set(included) if actor.strip() not in {x.strip() for x in excluded}]
    return final_included, list(set(excluded))

# --- helper to get movie cast ---
def get_movie_cast(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits"
    params = {"api_key": TMDB_API_KEY}
    res = requests.get(url, params=params).json()
    cast_list = []
    for member in res.get("cast", []):
        cast_list.append(member.get("name", "").lower())
    return cast_list

# --- similar movie search ---
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
            "cast": "n/a",
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count")
        })
    return final

# --- main function ---
def search_movies_by_prompt(prompt, max_results=6):
    included_genres, excluded_genres = extract_genres(prompt)
    keyword_ids = extract_keywords(prompt)
    actor_names, excluded_actor_names = extract_actor_names(prompt)
    actor_ids = []
    for name in actor_names:
        actor_id = get_actor_id(name)
        if actor_id:
            actor_ids.append(actor_id)
    if "like " in prompt.lower() or "similar to " in prompt.lower():
        return search_similar_to_movie(prompt, max_results)
    # debug output
    print("\n📥 prompt:", prompt)
    print("included genres:", included_genres)
    print("excluded genres:", excluded_genres)
    print("keyword ids:", keyword_ids)
    print("actor names:", actor_names)
    print("excluded actor names:", excluded_actor_names)
    print("actor ids:", actor_ids)
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
    print("🎬 results returned:", len(movies))
    # apply actor exclusion filter by checking movie cast
    if excluded_actor_names:
        filtered_movies = []
        for movie in movies:
            cast = get_movie_cast(movie["id"])
            # skip movie if any excluded actor appears in the cast (exact match)
            if any(ex_actor in cast for ex_actor in excluded_actor_names):
                continue
            filtered_movies.append(movie)
        movies = filtered_movies
        print("🎬 results after actor exclusion filter:", len(movies))
    # fallback logic
    if not movies and (excluded_genres or keyword_ids or actor_ids):
        print("⚠️ fallback: retrying with simpler filters")
        fallback_params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "popularity.desc",
            "with_cast": ",".join(map(str, actor_ids)) if actor_ids else None,
            "with_genres": ",".join(map(str, included_genres)) if included_genres else None
        }
        res = requests.get(url, params={k: v for k, v in fallback_params.items() if v})
        movies = res.json().get("results", []) if res.status_code == 200 else []
        print("🔁 fallback results:", len(movies))
    results = []
    for movie in movies[:max_results]:
        results.append({
            "title": movie.get("title"),
            "overview": movie.get("overview", ""),
            "release_date": movie.get("release_date", ""),
            "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "tmdb_link": f"https://www.themoviedb.org/movie/{movie['id']}",
            "genre": ", ".join([k for k, v in GENRE_MAP.items() if v in included_genres]),
            "cast": ", ".join(actor_names) if actor_names else "n/a",
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count")
        })
    return results

# --- trending movies ---
def get_trending_movies():
    url = f"{TMDB_BASE_URL}/trending/movie/week"
    params = {"api_key": TMDB_API_KEY}
    res = requests.get(url, params=params).json()
    movies = res.get("results", [])
    for movie in movies:
        movie["poster_url"] = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None
    return movies

# --- popular movies ---
def get_popular_movies():
    url = f"{TMDB_BASE_URL}/movie/popular"
    params = {"api_key": TMDB_API_KEY}
    res = requests.get(url, params=params).json()
    movies = res.get("results", [])
    for movie in movies:
        movie["poster_url"] = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None
    return movies