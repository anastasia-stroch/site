from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, make_response
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

YOUR_KINOPOISK_API_KEY = 'AVGM0J4-PSZ47T5-K7TTGN9-QDXQEQA'

KNOWN_MOVIES = {
    'шрек': {
        'id': 434,
        'title': 'Шрек',
        'alt_titles': ['Shrek']
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
    poster_url = db.Column(db.String(500), default='')
    date_watched = db.Column(db.DateTime, nullable=True)
    is_favorite = db.Column(db.Boolean, default=False)


@login_manager.user_loader
def load_this_user(user_id):
    return User.query.get(int(user_id))

def search_movies_kinopoisk(query):
    try:
        query_lower = query.strip().lower()
        if len(query_lower) < 2:
            return []
        for known_key, known_movie in KNOWN_MOVIES.items():
            if query_lower in known_key or query_lower in [t.lower() for t in
                                                           known_movie['alt_titles']]:
                details = get_movie_details_kinopoisk(known_movie['id'])
                if details:
                    return [{
                        'id': known_movie['id'],
                        'title': known_movie['title'],
                        'year': details.get('year', ''),
                        'rating': details.get('rating', 'Нет рейтинга'),
                        'poster': details.get('poster', '')
                    }]
                else:
                    return [{
                        'id': known_movie['id'],
                        'title': known_movie['title'],
                        'year': '',
                        'rating': 'Нет рейтинга',
                        'poster': ''
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
                    poster = movie.get('poster', {}).get('url', '') or ''
                    movies.append({
                        'id': movie.get('id'),
                        'title': title,
                        'year': movie.get('year', ''),
                        'rating': movie.get('rating', {}).get('kp', 'Нет рейтинга'),
                        'poster': poster
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

            title = data.get('name') or data.get('alternativeName') or data.get(
                'enName') or 'Без названия'
            year = data.get('year', '')
            genres = [genre.get('name', '') for genre in data.get('genres', [])]
            genre_str = ', '.join(genres) if genres else 'Неизвестно'
            rating_data = data.get('rating', {})
            rating = rating_data.get('kp') or rating_data.get('imdb') or 'Нет рейтинга'
            if isinstance(rating, (int, float)):
                rating = f"{rating:.1f}"
            description = data.get('description') or data.get(
                'shortDescription') or 'Описание не найдено'
            poster = data.get('poster', {}).get('url', '') or ''
            return {
                'title': title,
                'year': str(year) if year else '',
                'genre': genre_str,
                'rating': str(rating),
                'description': description,
                'poster': poster
            }
        else:
            return None
    except Exception:
        return None


@app.route('/')
@login_required
def index():
    all_my_items = MyItem.query.filter_by(user_who_owns=current_user.id).order_by(
        MyItem.date_when_created.desc()).all()
    planned = sum(1 for item in all_my_items if item.how_its_going == 'plan')
    watching = sum(1 for item in all_my_items if item.how_its_going == 'watching')
    completed = sum(1 for item in all_my_items if item.how_its_going == 'completed')
    ratings = [item.my_rating for item in all_my_items if item.my_rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    favorites_count = sum(1 for item in all_my_items if item.is_favorite)
    return render_template('index.html',
                           items=all_my_items,
                           planned=planned,
                           watching=watching,
                           completed=completed,
                           avg_rating=round(avg_rating, 1),
                           favorites_count=favorites_count)


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
                user_who_owns=current_user.id,
                poster_url=movie_data.get('poster', '')
            )
            db.session.add(new_item)
            db.session.commit()
            flash(f'Фильм "{movie_data["title"]}" добавлен! Рейтинг: {movie_data["rating"]}',
                  'success')
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
        date_watched_str = request.form.get('date_watched')
        if status_from_form:
            item_to_edit.how_its_going = status_from_form
        if rating_from_form and rating_from_form.isdigit():
            item_to_edit.my_rating = int(rating_from_form)
        if date_watched_str:
            try:
                item_to_edit.date_watched = datetime.strptime(date_watched_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

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


@app.route('/toggle_favorite/<int:id>')
@login_required
def toggle_favorite(id):
    item_to_toggle = MyItem.query.get_or_404(id)
    if item_to_toggle.user_who_owns == current_user.id:
        item_to_toggle.is_favorite = not item_to_toggle.is_favorite
        db.session.commit()
        if item_to_toggle.is_favorite:
            flash('Добавлено в избранное! ❤️', 'success')
        else:
            flash('Удалено из избранного', 'info')
    else:
        flash('Нельзя изменить чужое!', 'danger')
    return redirect(url_for('index'))


@app.route('/favorites')
@login_required
def favorites():
    favorite_items = MyItem.query.filter_by(
        user_who_owns=current_user.id,
        is_favorite=True
    ).order_by(MyItem.date_when_created.desc()).all()
    return render_template('favorites.html', items=favorite_items)


@app.route('/export/json')
@login_required
def export_json():
    items = MyItem.query.filter_by(user_who_owns=current_user.id).all()
    data = []
    for item in items:
        data.append({
            'name': item.name,
            'year': item.year,
            'genre': item.genre,
            'kinopoisk_rating': item.kinopoisk_rating,
            'my_rating': item.my_rating,
            'status': item.how_its_going,
            'description': item.description,
            'poster_url': item.poster_url,
            'date_watched': item.date_watched.isoformat() if item.date_watched else None,
            'is_favorite': item.is_favorite
        })

    json_text = '[\n'
    for i, film in enumerate(data):
        json_text += '  {\n'
        json_text += f'    "name": "{film["name"]}",\n'
        json_text += f'    "year": "{film["year"]}",\n'
        json_text += f'    "genre": "{film["genre"]}",\n'
        json_text += f'    "kinopoisk_rating": "{film["kinopoisk_rating"]}",\n'
        json_text += f'    "my_rating": {film["my_rating"] if film["my_rating"] else "null"},\n'
        json_text += f'    "status": "{film["status"]}",\n'
        json_text += f'    "description": "{film["description"].replace(chr(34), chr(92) + chr(34))}",\n'
        json_text += f'    "poster_url": "{film["poster_url"]}",\n'
        json_text += f'    "date_watched": "{film["date_watched"] if film["date_watched"] else ""}",\n'
        json_text += f'    "is_favorite": {str(film["is_favorite"]).lower()}\n'
        json_text += '  }'
        if i < len(data) - 1:
            json_text += ','
        json_text += '\n'
    json_text += ']'

    response_text = json_text
    response = make_response(response_text)
    response.headers["Content-Disposition"] = "attachment; filename=my_films.json"
    response.headers["Content-type"] = "application/json"
    return response


@app.route('/export/csv')
@login_required
def export_csv():
    items = MyItem.query.filter_by(user_who_owns=current_user.id).all()
    csv_lines = []
    csv_lines.append(
        'Название,Год,Жанр,Рейтинг КП,Моя оценка,Статус,Описание,Постер,Дата просмотра,Избранное')
    for item in items:
        name = item.name if item.name else ''
        year = item.year if item.year else ''
        genre = item.genre if item.genre else ''
        rating = item.kinopoisk_rating if item.kinopoisk_rating else ''
        my_rating = str(item.my_rating) if item.my_rating else ''
        status = ''
        if item.how_its_going == 'plan':
            status = 'В планах'
        elif item.how_its_going == 'watching':
            status = 'Смотрю'
        else:
            status = 'Просмотрено'
        description = item.description if item.description else ''
        description = description.replace(',', ';').replace('\n', ' ').replace('"', "'")
        poster = item.poster_url if item.poster_url else ''
        date_watched = item.date_watched.strftime('%d.%m.%Y %H:%M') if item.date_watched else ''
        favorite = 'Да' if item.is_favorite else 'Нет'
        line = f'{name},{year},{genre},{rating},{my_rating},{status},{description},{poster},{date_watched},{favorite}'
        csv_lines.append(line)
    csv_text = '\n'.join(csv_lines)
    response = make_response(csv_text)
    response.headers["Content-Disposition"] = "attachment; filename=my_films.csv"
    response.headers["Content-type"] = "text/csv"
    return response

class WeeklyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_text = db.Column(db.String(300), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=пн, 1=вт, ..., 6=вс
    is_done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='weekly_tasks')

@app.route('/weekly')
@login_required
def weekly():
    monday_tasks = WeeklyTask.query.filter_by(user_id=current_user.id, day_of_week=0).all()
    tuesday_tasks = WeeklyTask.query.filter_by(user_id=current_user.id, day_of_week=1).all()
    wednesday_tasks = WeeklyTask.query.filter_by(user_id=current_user.id, day_of_week=2).all()
    thursday_tasks = WeeklyTask.query.filter_by(user_id=current_user.id, day_of_week=3).all()
    friday_tasks = WeeklyTask.query.filter_by(user_id=current_user.id, day_of_week=4).all()
    saturday_tasks = WeeklyTask.query.filter_by(user_id=current_user.id, day_of_week=5).all()
    sunday_tasks = WeeklyTask.query.filter_by(user_id=current_user.id, day_of_week=6).all()

    return render_template('weekly.html',
                           monday_tasks=monday_tasks,
                           tuesday_tasks=tuesday_tasks,
                           wednesday_tasks=wednesday_tasks,
                           thursday_tasks=thursday_tasks,
                           friday_tasks=friday_tasks,
                           saturday_tasks=saturday_tasks,
                           sunday_tasks=sunday_tasks)


@app.route('/weekly/add', methods=['POST'])
@login_required
def weekly_add():
    day = request.form.get('day')
    task_text = request.form.get('task_text')

    if day == 'monday':
        day_number = 0
    elif day == 'tuesday':
        day_number = 1
    elif day == 'wednesday':
        day_number = 2
    elif day == 'thursday':
        day_number = 3
    elif day == 'friday':
        day_number = 4
    elif day == 'saturday':
        day_number = 5
    elif day == 'sunday':
        day_number = 6
    else:
        day_number = 0

    new_task = WeeklyTask(
        user_id=current_user.id,
        task_text=task_text,
        day_of_week=day_number,
        is_done=False
    )
    db.session.add(new_task)
    db.session.commit()
    flash('✅ Задача добавлена', 'success')
    return redirect(url_for('weekly'))

@app.route('/weekly/toggle/<int:task_id>')
@login_required
def weekly_toggle(task_id):
    task = WeeklyTask.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Не твоя задача!', 'danger')
        return redirect(url_for('weekly'))
    if task.is_done == True:
        task.is_done = False
    else:
        task.is_done = True

    db.session.commit()
    flash('Статус изменен', 'info')
    return redirect(url_for('weekly'))


@app.route('/weekly/delete/<int:task_id>')
@login_required
def weekly_delete(task_id):
    task = WeeklyTask.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Не твоя задача!', 'danger')
        return redirect(url_for('weekly'))

    db.session.delete(task)
    db.session.commit()
    flash('Задача удалена', 'success')
    return redirect(url_for('weekly'))

with app.app_context():
    db.create_all()

@app.route('/weekly')
@login_required
def weekly_plan():
    from datetime import datetime, timedelta

    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    new_this_week = MyItem.query.filter(
        MyItem.user_who_owns == current_user.id,
        db.func.date(MyItem.date_when_created) >= start_of_week
    ).all()

    planned_movies = MyItem.query.filter_by(
        user_who_owns=current_user.id,
        how_its_going='plan'
    ).order_by(MyItem.date_when_created).all()

    all_user_movie_names = [item.name.lower() for item in MyItem.query.filter_by(user_who_owns=current_user.id).all()]
    recommendations = []
    for key, movie in KNOWN_MOVIES.items():
        if movie['title'].lower() not in all_user_movie_names:
            details = get_movie_details_kinopoisk(movie['id'])
            if details and details.get('rating') and details['rating'] != 'Нет рейтинга':
                try:
                    rating = float(details['rating'])
                    if rating >= 8.0:
                        recommendations.append({
                            'title': movie['title'],
                            'rating': details['rating'],
                            'year': details.get('year', ''),
                            'id': movie['id']
                        })
                except:
                    pass

    return render_template('weekly.html',
                           new_this_week=new_this_week,
                           planned_movies=planned_movies[:10],
                           recommendations=recommendations[:5],
                           start_of_week=start_of_week,
                           end_of_week=end_of_week)


@app.route('/advanced_search', methods=['GET', 'POST'])
@login_required
def advanced_search():
    if request.method == 'POST':
        title = request.form.get('title', '').strip().lower()
        genre = request.form.get('genre', '').strip().lower()
        min_rating = request.form.get('min_rating', '')
        status = request.form.get('status', '')
        query = MyItem.query.filter_by(user_who_owns=current_user.id)
        if title:
            query = query.filter(MyItem.name.ilike(f'%{title}%'))
        if genre:
            query = query.filter(MyItem.genre.ilike(f'%{genre}%'))
        if status:
            query = query.filter(MyItem.how_its_going == status)
        if min_rating and min_rating.isdigit():
            query = query.filter(MyItem.my_rating >= int(min_rating))

        results = query.order_by(MyItem.date_when_created.desc()).all()
        return render_template('advanced_search.html', results=results, search_performed=True)

    return render_template('advanced_search.html', results=None, search_performed=False)


@app.route('/movies/random')
@login_required
def random_movie():
    import random
    status_filter = request.args.get('status', 'all')
    query = MyItem.query.filter_by(user_who_owns=current_user.id)
    if status_filter == 'plan':
        query = query.filter_by(how_its_going='plan')
    elif status_filter == 'watching':
        query = query.filter_by(how_its_going='watching')
    elif status_filter == 'completed':
        query = query.filter_by(how_its_going='completed')
    elif status_filter == 'favorite':
        query = query.filter_by(is_favorite=True)
    movies = query.all()
    if not movies:
        return jsonify({'error': 'Нет фильмов для выбора'}), 404
    movie = random.choice(movies)
    return jsonify({
        'id': movie.id,
        'name': movie.name,
        'year': movie.year,
        'genre': movie.genre,
        'my_rating': movie.my_rating,
        'kinopoisk_rating': movie.kinopoisk_rating,
        'status': movie.how_its_going,
        'poster_url': movie.poster_url
    })

@app.route('/random')
@login_required
def random_movie_page():
    return render_template('random_movie.html')

@app.route('/movies/recent')
@login_required
def recent_movies():
    limit = request.args.get('limit', 10, type=int)
    recent = MyItem.query.filter_by(user_who_owns=current_user.id) \
        .order_by(MyItem.date_when_created.desc()) \
        .limit(limit).all()
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'year': m.year,
        'rating': m.my_rating,
        'date_added': m.date_when_created.strftime('%d.%m.%Y %H:%M'),
        'status': m.how_its_going
    } for m in recent])


@app.route('/movies/top_rated')
@login_required
def top_rated_movies():
    limit = request.args.get('limit', 10, type=int)
    movies = MyItem.query.filter_by(
        user_who_owns=current_user.id
    ).filter(
        MyItem.my_rating.isnot(None)
    ).order_by(
        MyItem.my_rating.desc(),
        MyItem.kinopoisk_rating.desc()
    ).limit(limit).all()

    return jsonify([{
        'id': m.id,
        'name': m.name,
        'my_rating': m.my_rating,
        'kinopoisk_rating': m.kinopoisk_rating,
        'year': m.year
    } for m in movies])


@app.route('/export/custom')
@login_required
def export_custom():
    items = MyItem.query.filter_by(user_who_owns=current_user.id).all()
    format_type = request.args.get('format', 'json')
    fields = request.args.getlist('fields')
    if not fields:
        fields = ['name', 'year', 'genre', 'kinopoisk_rating', 'my_rating', 'status']
    data = []
    for item in items:
        row = {}
        if 'name' in fields:
            row['name'] = item.name
        if 'year' in fields:
            row['year'] = item.year
        if 'genre' in fields:
            row['genre'] = item.genre
        if 'kinopoisk_rating' in fields:
            row['kinopoisk_rating'] = item.kinopoisk_rating
        if 'my_rating' in fields:
            row['my_rating'] = item.my_rating
        if 'status' in fields:
            status_map = {'plan': 'В планах', 'watching': 'Смотрю', 'completed': 'Просмотрено'}
            row['status'] = status_map.get(item.how_its_going, item.how_its_going)
        if 'date_added' in fields:
            row['date_added'] = item.date_when_created.strftime('%d.%m.%Y') if item.date_when_created else ''
        data.append(row)

    if format_type == 'csv':
        import csv
        from io import StringIO
        output = StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=custom_export.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    else:
        return jsonify(data)

@app.route('/movies/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': 'Не указаны ID'}), 400

    deleted_count = 0
    for movie_id in ids:
        movie = MyItem.query.get(movie_id)
        if movie and movie.user_who_owns == current_user.id:
            db.session.delete(movie)
            deleted_count += 1

    db.session.commit()
    return jsonify({'deleted': deleted_count, 'success': True})

@app.route('/movies/stats/years')
@login_required
def yearly_stats_simple():
    items = MyItem.query.filter_by(user_who_owns=current_user.id).all()

    yearly = {}
    for item in items:
        if item.date_when_created:
            year = item.date_when_created.year
            if year not in yearly:
                yearly[year] = 0
            yearly[year] += 1

    return jsonify(yearly)

@app.route('/api/simple_stats')
@login_required
def simple_stats():
    items = MyItem.query.filter_by(user_who_owns=current_user.id).all()
    genre_count = {}
    for item in items:
        genres = item.genre.split(', ')
        for g in genres:
            if g and g != 'Неизвестно':
                genre_count[g] = genre_count.get(g, 0) + 1
    return jsonify({
        'total': len(items),
        'favorites': sum(1 for i in items if i.is_favorite),
        'completed': sum(1 for i in items if i.how_its_going == 'completed'),
        'top_genres': dict(sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5])
    })

@app.route('/stats')
@login_required
def stats():
    user_id = current_user.id
    films = MyItem.query.filter_by(user_who_owns=user_id).all()
    total = 0
    watched = 0
    watching = 0
    fav = 0
    rates = []
    for f in films:
        total = total + 1
        if f.how_its_going == 'completed':
            watched = watched + 1
        elif f.how_its_going == 'watching':
            watching = watching + 1
        if f.is_favorite == True:
            fav = fav + 1
        if f.my_rating != None:
            rates.append(f.my_rating)
    if len(rates) > 0:
        sum_rates = 0
        for r in rates:
            sum_rates = sum_rates + r
        avg = round(sum_rates / len(rates), 1)
    else:
        avg = 0
    top = MyItem.query.filter_by(user_who_owns=user_id).filter(MyItem.my_rating.isnot(None)).order_by(MyItem.my_rating.desc()).limit(5).all()
    gen = {}
    for f in films:
        if f.genre != None and f.genre != 'Неизвестно':
            g_list = f.genre.split(', ')
            for g in g_list:
                g = g.strip()
                if g != '':
                    if g in gen:
                        gen[g] = gen[g] + 1
                    else:
                        gen[g] = 1
    return render_template('stats.html',
                         total=total,
                         watched=watched,
                         watching=watching,
                         favorites=fav,
                         avg_rating=avg,
                         top_rated=top,
                         genres=gen.items())

if __name__ == '__main__':
    app.run(debug=True)
