from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
import ssl

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'info'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    date_registered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    feedbacks = db.relationship('Feedback', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_sent = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f"Feedback('{self.name}', '{self.subject}')"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.before_request
def force_https():
    if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        if app.debug:
            return
        return redirect(request.url.replace('http://', 'https://'), code=301)

@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html', title='Главная')

@app.route('/about')
def about():
    return render_template('about.html', title='О нас')

@app.route('/services')
def services():
    return render_template('services.html', title='Услуги')

@app.route('/register', methods=['GET', 'POST'])
def register():

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password:
            flash('Все поля обязательны для заполнения!', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Пароли не совпадают!', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято!', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти ', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации!', 'danger')
            print(f"Ошибка регистрации: {e}")

    return render_template('register.html', title='Регистрация')

@app.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')

        if not email or not password:
            flash('Пожалуйста, заполните все поля!', 'danger')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
            flash(f'Добро пожаловать, {user.username}! ', 'success')

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Неверный email или пароль! ', 'danger')

    return render_template('login.html', title='Вход')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта. До встречи! ', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():

    user_feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.date_sent.desc()).all()
    return render_template('dashboard.html', title='Личный кабинет', feedbacks=user_feedbacks)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        if not username or not email:
            flash('Все поля обязательны!', 'danger')
            return redirect(url_for('profile'))

        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash('Этот email уже используется!', 'danger')
            return redirect(url_for('profile'))

        existing_username = User.query.filter(User.username == username, User.id != current_user.id).first()
        if existing_username:
            flash('Это имя пользователя уже занято!', 'danger')
            return redirect(url_for('profile'))

        try:
            current_user.username = username
            current_user.email = email
            db.session.commit()
            flash('Профиль успешно обновлён! ', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при обновлении профиля!', 'danger')
            print(f"Ошибка: {e}")

    return render_template('profile.html', title='Профиль')

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            flash('Все поля обязательны!', 'danger')
            return redirect(url_for('change_password'))

        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('Неверный текущий пароль!', 'danger')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('Новые пароли не совпадают!', 'danger')
            return redirect(url_for('change_password'))

        if len(new_password) < 6:
            flash('Пароль должен содержать минимум 6 символов!', 'danger')
            return redirect(url_for('change_password'))

        try:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            current_user.password = hashed_password
            db.session.commit()
            flash('Пароль успешно изменён! ', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при смене пароля!', 'danger')
            print(f"Ошибка: {e}")

    return render_template('change_password.html', title='Смена пароля')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not all([name, email, subject, message]):
            flash('Все поля обязательны для заполнения!', 'danger')
            return redirect(url_for('contact'))

        new_feedback = Feedback(
            name=name,
            email=email,
            subject=subject,
            message=message,
            user_id=current_user.id if current_user.is_authenticated else None
        )

        try:
            db.session.add(new_feedback)
            db.session.commit()
            flash('Ваше сообщение успешно отправлено! ', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при отправке сообщения!', 'danger')
            print(f"Ошибка отправки: {e}")

    return render_template('contact.html', title='Контакты')

@app.route('/ssl-info')
def ssl_info():
    ssl_info = {
        'is_secure': request.is_secure,
        'scheme': request.scheme,
        'headers': dict(request.headers)
    }
    return f"<pre>{ssl_info}</pre>"

if __name__ == '__main__':
    cert_file = 'certs/server.crt'
    key_file = 'certs/server.key'

    cert_exists = os.path.exists(cert_file)
    key_exists = os.path.exists(key_file)

    print("=" * 50)
    print("Проверка SSL сертификатов:")
    print(f"Сертификат: {cert_file} - {'Найден' if cert_exists else 'Не найден'}")
    print(f"Ключ: {key_file} - {'Найден' if key_exists else 'Не найден'}")
    print("=" * 50)

    if cert_exists and key_exists:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert_file, key_file)

            print("Запуск Flask приложения с HTTPS...")
            print("Доступные URL:")
            print("   • https://89.169.164.25:5000/")
            print("   • https://127.0.0.1:5000/ (localhost)")
            print("=" * 50)

            app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=context)

        except ssl.SSLError as e:
            print(f"Ошибка SSL: {e}")
        except Exception as e:
            print(f"Ошибка запуска: {e}")
    else:
        print("Запуск без SSL (HTTP)...")
        app.run(host='0.0.0.0', port=5000, debug=True)
