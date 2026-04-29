from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///watchlist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    items = db.relationship('WatchItem', backref='owner', lazy=True, cascade='all, delete-orphan')

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class WatchItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    item_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='planned')
    rating = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def index():
    items = WatchItem.query.filter_by(user_id=current_user.id).order_by(WatchItem.created_at.desc()).all()
    return render_template('index.html', items=items)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Пароли не совпадают!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Этот email уже зарегистрирован', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация успешна! Теперь войдите', 'success')
            return redirect(url_for('login'))
        except:
            flash('Произошла ошибка при регистрации', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
            flash(f'С возвращением, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Неверный email или пароль', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('login'))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        item_type = request.form.get('item_type')
        status = request.form.get('status')
        rating = request.form.get('rating')

        if not title:
            flash('Название обязательно', 'danger')
            return redirect(url_for('add_item'))

        new_item = WatchItem(
            title=title,
            description=description,
            item_type=item_type,
            status=status,
            rating=int(rating) if rating else None,
            owner=current_user
        )

        db.session.add(new_item)
        db.session.commit()
        flash('Элемент добавлен!', 'success')
        return redirect(url_for('index'))

    return render_template('add_item.html')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    item = WatchItem.query.get_or_404(id)

    if item.owner != current_user:
        flash('У вас нет прав', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        item.title = request.form.get('title')
        item.description = request.form.get('description')
        item.item_type = request.form.get('item_type')
        item.status = request.form.get('status')
        rating = request.form.get('rating')
        item.rating = int(rating) if rating else None

        db.session.commit()
        flash('Изменения сохранены!', 'success')
        return redirect(url_for('index'))

    return render_template('edit_item.html', item=item)


@app.route('/delete/<int:id>')
@login_required
def delete_item(id):
    item = WatchItem.query.get_or_404(id)

    if item.owner == current_user:
        db.session.delete(item)
        db.session.commit()
        flash('Элемент удален!', 'success')

    return redirect(url_for('index'))


@app.route('/api/items')
@login_required
def api_items():
    items = WatchItem.query.filter_by(user_id=current_user.id).all()
    return {
        'items': [{
            'id': item.id,
            'title': item.title,
            'type': item.item_type,
            'status': item.status,
            'rating': item.rating
        } for item in items]
    }


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)