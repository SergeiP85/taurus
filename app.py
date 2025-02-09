from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash

app = Flask(__name__)

# Настройка базы данных
app.config['SECRET_KEY'] = 'your_very_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from flask_migrate import Migrate

migrate = Migrate(app, db)  # Инициализируем Flask-Migrate


# Модель данных
class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)

# Модель пользователей
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Флаг администратора

    def __repr__(self):
        return f'<User {self.username}>'

# Проверка авторизации (декоратор)
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))  # Отправляем на страницу логина
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Проверка прав администратора
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return "Доступ запрещен!", 403  # Ошибка доступа
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Главная страница (видна всем)
@app.route('/')
def home():
    pages = Page.query.all()
    return render_template('index.html', pages=pages)

# Страница "Сайт" (доступна только после входа)
@app.route('/site')
@login_required
def public_site():
    pages = Page.query.all()
    return render_template('public_site.html', pages=pages)

# Панель администратора (только для админа)
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    return render_template('add_page.html')

# Добавление контента (только для админа)
@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_page():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_page = Page(title=title, content=content)
        db.session.add(new_page)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_page.html')

# Просмотр отдельной страницы (для всех авторизованных)
@app.route('/page/<int:page_id>')
@login_required
def view_page(page_id):
    page = Page.query.get_or_404(page_id)
    return render_template('view_page.html', page=page)

# Удаление страницы (только для админа)
@app.route('/delete/<int:page_id>', methods=['POST'])
@login_required
@admin_required
def delete_page(page_id):
    page = Page.query.get_or_404(page_id)
    db.session.delete(page)
    db.session.commit()
    return redirect(url_for('home'))

# Добавление пользователя (только для админа)
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = request.form.get('is_admin') == 'on'  # Флаг админа

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Такой пользователь уже существует!"

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()

        flash('Пользователь успешно добавлен!', 'success')  # Сообщение о добавлении
        return redirect(url_for('home'))  # После добавления пользователя возвращаем в админку

    return render_template('add_user.html')

# Удаление пользователя (только для админа)
@app.route('/delete_user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    user_id = request.form.get('user_id')  # Получаем ID из формы
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()

        flash('Пользователь успешно удален!', 'success')  # Сообщение об удалении
        return redirect(url_for('home'))  # Перенаправляем обратно в панель
    return "Пользователь не найден!", 404



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin  # Запоминаем, админ ли он

            # Проверяем, админ ли это и направляем на нужную страницу
            if user.is_admin:
                return redirect(url_for('home'))  # Админ → в панель администратора
            return redirect(url_for('public_site'))  # Обычный пользователь → на сайт
        else:
            return "Неверный логин или пароль. Попробуйте снова."

    return render_template('login.html')


# Выход
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    from app import db  # Импортируем базу данных
    from app import app  # Импортируем само приложение
    with app.app_context():
        db.create_all()  # Создаем таблицы, если их нет
    print("Таблицы созданы!")  # Выводим сообщение в консоль
    
    app.run(debug=True)


