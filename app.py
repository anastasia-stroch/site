from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    my_items = db.relationship('MyItem', backref='this_user', lazy=True)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class MyItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(100), default='Неизвестно')
    description = db.Column(db.Text, default='')
    imdb_rating = db.Column(db.String(20), default='Нет рейтинга')
    year = db.Column(db.String(10), default='')
    how_its_going = db.Column(db.String(50), default='plan')
    my_rating = db.Column(db.Integer, nullable=True)
    user_who_owns = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_when_created = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_this_user(user_id):
    return User.query.get(int(user_id))


def search_movies_omdb(query):
    try:
        search_url = f"http://www.omdbapi.com/?s={query}&apikey=8d5e6f1b"

        response = requests.get(search_url)

        if response.status_code == 200:
            data = response.json()

            if data.get('Response') == 'True':
                movies = []
                for movie in data.get('Search', [])[:10]:
                    movies.append({
                        'imdbID': movie.get('imdbID'),
                        'title': movie.get('Title'),
                        'year': movie.get('Year'),
                        'type': movie.get('Type')
                    })
                return movies
            else:
                print(f"OMDb ошибка: {data.get('Error')}")
                return []
        else:
            print(f"HTTP ошибка: {response.status_code}")
            return []

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []


def get_movie_details_omdb(imdb_id):
    try:
        details_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey=8d5e6f1b&plot=full"
        response = requests.get(details_url)

        if response.status_code == 200:
            data = response.json()

            if data.get('Response') == 'True':
                return {
                    'title': data.get('Title', 'Неизвестно'),
                    'genre': data.get('Genre', 'Неизвестно'),
                    'description': data.get('Plot', 'Описание не найдено')[:500],
                    'rating': data.get('imdbRating', 'Нет рейтинга'),
                    'year': data.get('Year', '')
                }

        return None

    except Exception as e:
        print(f"Ошибка получения деталей: {e}")
        return None


@app.route('/')
@login_required
def index():
    all_my_items = MyItem.query.filter_by(user_who_owns=current_user.id).order_by(MyItem.date_when_created.desc()).all()
    return render_template('index.html', items=all_my_items)


@app.route('/search_movies')
def search_movies():
    query = request.args.get('query', '')
    if len(query) < 2:
        return jsonify([])

    movies = search_movies_omdb(query)
    return jsonify(movies)


@app.route('/get_movie_details')
def get_movie_details_route():
    imdb_id = request.args.get('id', '')
    if not imdb_id:
        return jsonify({'error': 'No ID provided'}), 400

    details = get_movie_details_omdb(imdb_id)
    if details:
        return jsonify(details)
    return jsonify({'error': 'Not found'}), 404


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username_from_form = request.form.get('username')
        email_from_form = request.form.get('email')
        password_from_form = request.form.get('password')
        confirm_password_from_form = request.form.get('confirm_password')

        if not username_from_form or not email_from_form or not password_from_form:
            flash('Заполни все поля!', 'danger')
            return redirect(url_for('register'))

        if password_from_form != confirm_password_from_form:
            flash('Пароли не совпадают!', 'danger')
            return redirect(url_for('register'))

        user_with_same_email = User.query.filter_by(email=email_from_form).first()
        if user_with_same_email:
            flash('Такой email уже есть в системе', 'danger')
            return redirect(url_for('register'))

        user_with_same_username = User.query.filter_by(username=username_from_form).first()
        if user_with_same_username:
            flash('Такое имя уже занято', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password_from_form, method='pbkdf2:sha256')
        new_user = User(username=username_from_form, email=email_from_form, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Ты зарегистрировался! Теперь войди', 'success')
            return redirect(url_for('login'))
        except:
            flash('Что-то пошло не так', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email_from_form = request.form.get('email')
        password_from_form = request.form.get('password')
        remember_me = request.form.get('remember')

        my_user = User.query.filter_by(email=email_from_form).first()

        if my_user:
            password_is_correct = check_password_hash(my_user.password, password_from_form)
            if password_is_correct:
                if remember_me:
                    login_user(my_user, remember=True)
                else:
                    login_user(my_user, remember=False)
                flash('Привет, ' + my_user.username + '!', 'success')
                next_page_that_user_wanted = request.args.get('next')
                if next_page_that_user_wanted:
                    return redirect(next_page_that_user_wanted)
                else:
                    return redirect(url_for('index'))
            else:
                flash('Неверный пароль', 'danger')
        else:
            flash('Пользователь с таким email не найден', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ты вышел из аккаунта', 'info')
    return redirect(url_for('login'))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        selected_id = request.form.get('selected_id')

        if not selected_id:
            flash('Выбери фильм из списка!', 'danger')
            return redirect(url_for('add_item'))

        movie_data = get_movie_details_omdb(selected_id)

        if movie_data:
            new_item = MyItem(
                name=movie_data['title'],
                genre=movie_data['genre'],
                description=movie_data['description'],
                imdb_rating=movie_data['rating'],
                year=movie_data['year'],
                how_its_going='plan',
                user_who_owns=current_user.id
            )

            db.session.add(new_item)
            db.session.commit()
            flash(f'Фильм "{movie_data["title"]}" добавлен! Рейтинг IMDb: {movie_data["rating"]}', 'success')
        else:
            flash('Не удалось загрузить информацию о фильме', 'danger')

        return redirect(url_for('index'))

    return render_template('add_item.html')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    item_to_edit = MyItem.query.get_or_404(id)

    if item_to_edit.user_who_owns != current_user.id:
        flash('Это не твой элемент!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        status_from_form = request.form.get('status')
        rating_from_form = request.form.get('rating')

        if status_from_form:
            item_to_edit.how_its_going = status_from_form

        if rating_from_form:
            item_to_edit.my_rating = int(rating_from_form)

        db.session.commit()
        flash('Изменения сохранены!', 'success')
        return redirect(url_for('index'))

    return render_template('edit_item.html', item=item_to_edit)


@app.route('/delete/<int:id>')
@login_required
def delete_item(id):
    item_to_delete = MyItem.query.get_or_404(id)

    if item_to_delete.user_who_owns == current_user.id:
        db.session.delete(item_to_delete)
        db.session.commit()
        flash('Удалено!', 'success')
    else:
        flash('Нельзя удалить чужое!', 'danger')

    return redirect(url_for('index'))


with app.app_context():
    db.drop_all()
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
