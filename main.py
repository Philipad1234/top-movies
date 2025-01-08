from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
from details import *

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''

app = Flask(__name__)
bootstrap = Bootstrap5(app)
app.config['SECRET_KEY'] = SECRET_KEY


# CREATE DB
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///movies.db"
db = SQLAlchemy(model_class=Base)
db.init_app(app)

MOVIE_DB_URL = "https://api.themoviedb.org/3/search/movie"
API_KEY = API_KEY
MOVIE_DB_IMG_URL = 'https://image.tmdb.org/t/p/original/'


# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Float, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    movies = (db.session.execute(db.select(Movie).order_by(Movie.rating)).scalars().all())[::-1]
    for movie in movies:
        ranking_to_update = db.session.execute(db.select(Movie).where(Movie.rating == movie.rating)).scalar()
        ranking_to_update.ranking = movies.index(movie) + 1

    return render_template("index.html", movies=movies)


class EditForm(FlaskForm):
    rating = StringField(label='Your Rating out of 10 e.g. 7.5', validators=[DataRequired()])
    review = StringField(label='Your Review', validators=[DataRequired()])
    submit = SubmitField(label='Done')


class AddForm(FlaskForm):
    title = StringField(label='Movie Title', validators=[DataRequired()])
    submit = SubmitField(label='Add Movie')


@app.route("/update", methods=['GET', 'POST'])
def update():
    form = EditForm()
    movie_id = request.args.get('id')
    if form.validate_on_submit():
        new_rating = float(form.rating.data)
        new_review = form.review.data
        movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
        movie_to_update.rating = new_rating
        movie_to_update.review = new_review
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('edit.html', form=form)


@app.route("/delete")
def delete():
    movie_id = request.args.get('id')
    movie_to_delete = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/add", methods=['GET', 'POST'])
def add():
    form = AddForm()
    if form.validate_on_submit():
        movie_title = form.title.data
        params = {
            "api_key": API_KEY,
            "query": movie_title
        }

        headers = {
            "accept": "application/json",
            "Authorization": BEARER_TOKEN
        }

        response = requests.get(url=MOVIE_DB_URL, params=params, headers=headers).json()
        movie_list = response["results"]

        return render_template('select.html', movies=movie_list)
    return render_template('add.html', form=form)


@app.route('/find')
def find_movie():
    headers = {
        "accept": "application/json",
        "Authorization": BEARER_TOKEN
        }

    movie_id = request.args.get('id')
    response = requests.get(url=f"https://api.themoviedb.org/3/movie/{movie_id}", headers=headers).json()
    new_movie = Movie(
        title=response["original_title"],
        description=response["overview"],
        img_url=f"{MOVIE_DB_IMG_URL}{response['poster_path']}",
        year=response["release_date"][:4]
    )

    db.session.add(new_movie)
    db.session.commit()

    return redirect(url_for('update', id=new_movie.id))


if __name__ == '__main__':
    app.run(debug=True)
