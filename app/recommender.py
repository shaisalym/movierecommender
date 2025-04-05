from sentence_transformers import SentenceTransformer, util
import pandas as pd
import torch
from app.tmdb import get_tmdb_details

# load dataset and model
movies_df = pd.read_csv('data/movies.csv')
model = SentenceTransformer('all-MiniLM-L6-v2')

# combine relevant fields into one searchable string
def build_search_text(row):
    return f"{row['title']} {row['overview']} {row['genre']} {row['cast']}"

movies_df['search_text'] = movies_df.apply(build_search_text, axis=1)
search_embeddings = model.encode(movies_df['search_text'].tolist(), convert_to_tensor=True)

# extract known actors from the dataset
all_casts = movies_df['cast'].dropna().tolist()
known_actors = set()

for cast in all_casts:
    for actor in cast.split(','):
        actor = actor.strip().lower()
        if actor:
            known_actors.add(actor)

# extract actor names from the user prompt
def extract_actors_from_prompt(prompt):
    prompt_lower = prompt.lower()
    found_actors = []

    for actor in known_actors:
        if actor in prompt_lower:
            found_actors.append(actor)
            continue

        # handle partial matches like "johnny" or "depp"
        actor_parts = actor.split()
        if any(part in prompt_lower for part in actor_parts):
            found_actors.append(actor)

    # remove duplicates
    return list(set(found_actors))


# extract genre and actor exclusions from the prompt
def extract_exclusions_from_prompt(prompt):
    prompt_lower = prompt.lower()
    excluded_genres = []
    excluded_actors = []

    common_genres = ["horror", "comedy", "drama", "animation", "action", "sci-fi", "fantasy", "thriller", "mystery", "romantic"]

    for genre in common_genres:
        if f"not {genre}" in prompt_lower or f"without {genre}" in prompt_lower:
            excluded_genres.append(genre)

    # exclude actors logic
    for actor in known_actors:
        if f"not {actor}" in prompt_lower or f"without {actor}" in prompt_lower:
            excluded_actors.append(actor)

    return excluded_genres, excluded_actors


# main recommendation function
def get_recommendations(prompt, top_k=5, similarity_threshold=0.3):
    prompt_embedding = model.encode(prompt, convert_to_tensor=True)
    similarities = util.pytorch_cos_sim(prompt_embedding, search_embeddings)[0]

    k = min(top_k * 2, len(similarities))
    top_results = torch.topk(similarities, k=k)

    found_actors = extract_actors_from_prompt(prompt)
    excluded_genres, excluded_actors = extract_exclusions_from_prompt(prompt)

    results = []
    for idx, score in zip(top_results.indices, top_results.values):
        if score.item() < similarity_threshold:
            continue

        row = movies_df.iloc[int(idx)]
        cast_lower = row['cast'].lower()
        genre_lower = row['genre'].lower()

        # actor inclusion filter
        if found_actors and not all(actor in cast_lower for actor in found_actors):
            continue

        # exclusion filters
        if any(excluded_genre in genre_lower for excluded_genre in excluded_genres):
            continue
        if any(excluded_actor in cast_lower for excluded_actor in excluded_actors):
            continue

        # get TMDb data
        details = get_tmdb_details(row['title']) or {}

        results.append({
            'title': row['title'],
            'overview': row['overview'],
            'genre': row['genre'],
            'cast': row['cast'],
            'year': row['year'],
            'score': round(score.item(), 3),
            'poster_url': details.get('poster_url'),
            'release_date': details.get('release_date'),
            'tmdb_link': details.get('tmdb_link')
        })

        if len(results) == top_k:
            break

    return results