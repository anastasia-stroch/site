from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

YOUR_KINOPOISK_API_KEY = 'A3HSBCJ-H7R4DKV-J06VFAH-2H86DVE'

KNOWN_MOVIES = {
    'рапунцель': {
        'id': 84049,
        'title': 'Рапунцель: Запутанная история',
        'alt_titles': ['Tangled', 'Рапунцель', 'Запутанная история']
    },
    'шрек': {
        'id': 434,
        'title': 'Шрек',
        'alt_titles': ['Shrek']
    },
    'тачки': {
        'id': 417,
        'title': 'Тачки',
        'alt_titles': ['Cars']
    },
    'леон': {
        'id': 389,
        'title': 'Леон',
        'alt_titles': ['Leon', 'The Professional']
    },
    'зеленая книга': {
        'id': 512730,
        'title': 'Зеленая книга',
        'alt_titles': ['Green Book']
    },
    'джокер': {
        'id': 1143242,
        'title': 'Джокер',
        'alt_titles': ['Joker']
    },
    'интерстеллар': {
        'id': 258687,
        'title': 'Интерстеллар',
        'alt_titles': ['Interstellar']
    },
    'побег из шоушенка': {
        'id': 326,
        'title': 'Побег из Шоушенка',
        'alt_titles': ['The Shawshank Redemption']
    },
    'начало': {
        'id': 447301,
        'title': 'Начало',
        'alt_titles': ['Inception']
    }
}


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
    kinopoisk_rating = db.Column(db.String(20), default='Нет рейтинга')
    year = db.Column(db.String(20))
    how_its_going = db.Column(db.String(50), default='plan')
    my_rating = db.Column(db.Integer, nullable=True)
    user_who_owns = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_when_created = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_this_user(user_id):
    return User.query.get(int(user_id))


def search_movies_kinopoisk(query):
    try:
        query_lower = query.strip().lower()
        if len(query_lower) < 2:
            return []

        for known_key, known_movie in KNOWN_MOVIES.items():
            if query_lower in known_key or query_lower in [t.lower() for t in known_movie['alt_titles']]:
                details = get_movie_details_kinopoisk(known_movie['id'])
                if details:
                    return [{
                        'id': known_movie['id'],
                        'title': known_movie['title'],
                        'year': details.get('year', ''),
                        'rating': details.get('rating', 'Нет рейтинга')
                    }]
                else:
                    return [{
                        'id': known_movie['id'],
                        'title': known_movie['title'],
                        'year': '',
                        'rating': 'Нет рейтинга'
                    }]

        url = "https://api.kinopoisk.dev/v1.4/movie/search"
        headers = {
            'X-API-KEY': YOUR_KINOPOISK_API_KEY,
            'Content-Type': 'application/json'
        }
        params = {
            'query': query_lower,
            'limit': 30
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            movies = []

            for movie in data.get('docs', []):
                name_ru = movie.get('name') or ''
                name_alt = movie.get('alternativeName') or ''
                name_en = movie.get('enName') or ''

                if (query_lower in name_ru.lower() or
                        query_lower in name_alt.lower() or
                        query_lower in name_en.lower()):
                    title = name_ru or name_alt or name_en or 'Без названия'
                    movies.append({
                        'id': movie.get('id'),
                        'title': title,
                        'year': movie.get('year', ''),
                        'rating': movie.get('rating', {}).get('kp', 'Нет рейтинга')
                    })

            seen = set()
            unique_movies = []
            for movie in movies:
                if movie['id'] not in seen:
                    seen.add(movie['id'])
                    unique_movies.append(movie)

            return unique_movies
        else:
            return []

    except Exception:
        return []


def get_movie_details_kinopoisk(movie_id):
    try:
        url = f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}"
        headers = {
            'X-API-KEY': YOUR_KINOPOISK_API_KEY,
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            title = data.get('name') or data.get('alternativeName') or data.get('enName') or 'Без названия'
            year = data.get('year', '')
            genres = [genre.get('name', '') for genre in data.get('genres', [])]
            genre_str = ', '.join(genres) if genres else 'Неизвестно'

            rating_data = data.get('rating', {})
            rating = rating_data.get('kp') or rating_data.get('imdb') or 'Нет рейтинга'
            if isinstance(rating, (int, float)):
                rating = f"{rating:.1f}"

            description = data.get('description') or data.get('shortDescription') or 'Описание не найдено'

            return {
                'title': title,
                'year': str(year) if year else '',
                'genre': genre_str,
                'rating': str(rating),
                'description': description
            }
        else:
            return None

    except Exception:
        return None


@app.route('/')
@login_required
def index():
    all_my_items = MyItem.query.filter_by(user_who_owns=current_user.id).order_by(MyItem.date_when_created.desc()).all()

    planned = sum(1 for item in all_my_items if item.how_its_going == 'plan')
    watching = sum(1 for item in all_my_items if item.how_its_going == 'watching')
    completed = sum(1 for item in all_my_items if item.how_its_going == 'completed')

    ratings = [item.my_rating for item in all_my_items if item.my_rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    return render_template('index.html',
                           items=all_my_items,
                           planned=planned,
                           watching=watching,
                           completed=completed,
                           avg_rating=round(avg_rating, 1))


@app.route('/search_movies')
def search_movies():
    query = request.args.get('query', '').strip()
    if len(query) < 2:
        return jsonify([])
    movies = search_movies_kinopoisk(query)
    return jsonify(movies)


@app.route('/get_movie_details')
def get_movie_details_route():
    movie_id = request.args.get('id', '')
    if not movie_id:
        return jsonify({'error': 'No ID provided'}), 400
    details = get_movie_details_kinopoisk(movie_id)
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
        except Exception:
            db.session.rollback()
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
                login_user(my_user, remember=bool(remember_me))
                flash('Привет, ' + my_user.username + '!', 'success')
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
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

        movie_data = get_movie_details_kinopoisk(selected_id)

        if movie_data:
            existing = MyItem.query.filter_by(
                name=movie_data['title'],
                user_who_owns=current_user.id
            ).first()

            if existing:
                flash(f'Фильм "{movie_data["title"]}" уже есть в вашем списке!', 'warning')
                return redirect(url_for('index'))

            new_item = MyItem(
                name=movie_data['title'],
                genre=movie_data['genre'],
                description=movie_data['description'],
                kinopoisk_rating=movie_data['rating'],
                year=movie_data['year'],
                how_its_going='plan',
                user_who_owns=current_user.id
            )

            db.session.add(new_item)
            db.session.commit()
            flash(f'Фильм "{movie_data["title"]}" добавлен! Рейтинг КП: {movie_data["rating"]}', 'success')
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

        if rating_from_form and rating_from_form.isdigit():
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
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
