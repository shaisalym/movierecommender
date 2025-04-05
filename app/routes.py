from flask import Blueprint, render_template, request
from app.tmdb import search_movies_by_prompt, get_trending_movies, get_popular_movies

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def index():
    recommendations = []
    query = ""

    if request.method == 'POST':
        query = request.form['prompt']
        # get recommendations based on the query
        recommendations = search_movies_by_prompt(query)

    # pass recommendations to the template for rendering
    return render_template('index.html', query=query, movies=recommendations, tab="Recommended")


@main.route('/trending', methods=['GET'])
def trending():
    trending_movies = get_trending_movies()
    return render_template('index.html', movies=trending_movies, tab="Trending")


@main.route('/popular', methods=['GET'])
def popular():
    popular_movies = get_popular_movies()
    return render_template('index.html', movies=popular_movies, tab="Popular")
