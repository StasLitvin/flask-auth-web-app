# webapp — веб-приложение на Flask с авторизацией

Многостраничный сайт на Flask с регистрацией, входом, профилем и сменой пароля. Пароли хэшируются (bcrypt), сессии через flask-login, поддержка HTTPS.

## Файлы

- `app.py` — приложение Flask: модели, маршруты, `flask-login`, `flask-bcrypt`, SQLAlchemy (SQLite), SSL.
- `templates/` — `base, index, about, services, contact, login, register, dashboard, profile, change_password` и страница верификации Яндекса.
- `static/style.css` — стили.
- `requirements.txt` — зависимости.

## Технологии

Flask, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt, SQLite.

## Запуск

```bash
pip install -r requirements.txt
python app.py
```

Сайт поднимется на `http://127.0.0.1:5000/` (или по HTTPS, если настроены сертификаты).

## ⚠️ Замечания

- `SECRET_KEY` — заглушка; замените на случайный и храните в окружении.
- Файлы БД (`instance/site.db`) и сертификаты (`certs/`) исключены из набора и добавлены в `.gitignore`.
