from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
    about = db.Column(db.Text)
    type_of_item = db.Column(db.String(50), nullable=False)
    how_its_going = db.Column(db.String(50), default='plan')
    my_rating = db.Column(db.Integer)
    user_who_owns = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_when_created = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_this_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def index():
    all_my_items = MyItem.query.filter_by(user_who_owns=current_user.id).order_by(MyItem.date_when_created.desc()).all()
    return render_template('index.html', items=all_my_items)


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
        name_from_form = request.form.get('title')
        about_from_form = request.form.get('description')
        type_from_form = request.form.get('item_type')
        status_from_form = request.form.get('status')
        rating_from_form = request.form.get('rating')

        if not name_from_form:
            flash('Название обязательно', 'danger')
            return redirect(url_for('add_item'))

        if rating_from_form:
            rating_as_number = int(rating_from_form)
        else:
            rating_as_number = None

        new_item = MyItem(
            name=name_from_form,
            about=about_from_form,
            type_of_item=type_from_form,
            how_its_going=status_from_form,
            my_rating=rating_as_number,
            user_who_owns=current_user.id
        )

        db.session.add(new_item)
        db.session.commit()
        flash('Добавлено!', 'success')
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
        item_to_edit.name = request.form.get('title')
        item_to_edit.about = request.form.get('description')
        item_to_edit.type_of_item = request.form.get('item_type')
        item_to_edit.how_its_going = request.form.get('status')
        rating_from_form = request.form.get('rating')

        if rating_from_form:
            item_to_edit.my_rating = int(rating_from_form)
        else:
            item_to_edit.my_rating = None

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


@app.route('/api/items')
@login_required
def api_items():
    all_my_items = MyItem.query.filter_by(user_who_owns=current_user.id).all()

    items_list = []
    for one_item in all_my_items:
        items_list.append({
            'id': one_item.id,
            'title': one_item.name,
            'type': one_item.type_of_item,
            'status': one_item.how_its_going,
            'rating': one_item.my_rating
        })

    return {'items': items_list}


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
