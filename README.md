🎬 AI Movie Recommender 🎬

An intelligent movie recommendation web app built with Flask and powered by TMDb API, fuzzy logic, and natural language prompts.

Type prompts like:
- "funny movie with sydney sweeney"
- "romantic movie without margot robbie"
- "similar to inception"
- "pirate movie not horror with johnny depp"

The system will output relevant movie suggestions with posters, ratings, and more.

---

FEATURES

- Natural Language Prompt Parsing
Fuzzy matching for genre, actor names, and keywords

- Actor Inclusion/Exclusion
It filters movies based on prompt, whether the prompt asks for movies with a certain actor or explicitly mention without an actor.

- Genre Detection
Filters out genres such as 'romantic', 'comedy', 'action', etc.

- Similar Movie Finder
It shows you similar movies when you type in prompts such as "i want a movie like interstellar"

- Fallback Logic
Tries simpler filters if the prompt is too narrow or niche

- Trending / Popular Tabs
Tabs that show movies that are trending in the current week, and movies that are currently popular

- Dark Mode UI
Done using Tailwind. No light mode because I am anti light mode.


---

SETUP INSTRUCTIONS

- Clone repo
git clone https://github.com/shaisalym/movierecommender.git
cd movie-recommender

- Install dependencies
pip install -r requirements.txt

- Create .env fule
TMDB_API_KEY=your_tmdb_api_key_here

You can get the API key from https://www.themoviedb.org

- Run
python3 run.py