# Imports
import sqlite3,os,dotenv
from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_bcrypt import Bcrypt
from authlib.integrations.flask_client import OAuth

# Pre_Setup
dotenv.load_dotenv()
app = Flask(__name__)
bcrypt = Bcrypt(app)
oauth = OAuth(app)

# ENV_Setup
app.config['SECRET_KEY'] = os.getenv('secret_key')  # Important for session management
app.config['GOOGLE_CLIENT_ID'] =  os.getenv('google_client_id')  # Replace with your Client ID
app.config['GOOGLE_CLIENT_SECRET'] =  os.getenv('google_client_secret')  # Replace with your Client Secret


# Google Oauth
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    redirect_uri='http://localhost:5000/login/callback',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'},
)

# Initialize database
def init_db():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT
            )
        ''')
        conn.commit()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        conn.commit()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS google_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE,
                email TEXT
            )
        ''')
        conn.commit()
        conn.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

init_db()


# ROUTES
@app.route('/')
def index():
    return render_template('welcome.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/login_post', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

    if user and bcrypt.check_password_hash(user[0], password):
        session['username'] = username
        return redirect(url_for('welcome'))
    return redirect(url_for('index'))

@app.route('/dashboard')
def welcome():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template("dashboard.html")

@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('index'))
    except sqlite3.IntegrityError:
        flash('Username already exists', 'danger')
        return redirect(url_for('index'))

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/callback')
def google_authorized():
    token = google.authorize_access_token()
    user_info = token['userinfo']
    google_id = user_info['sub']
    email = user_info['email']

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM google_users WHERE google_id = ?', (google_id,))
        user = cursor.fetchone()

        if user:
            session['username'] = user[0]
            return redirect(url_for('welcome'))

        # Register new user
        cursor.execute('INSERT INTO google_users (google_id, email) VALUES (?, ?)', (google_id, email))
        conn.commit()
        session['username'] = email
        return redirect(url_for('welcome'))

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/suggestions")
def suggestions():
    name = request.args.get('name')
    email = request.args.get('email')
    suggestion = request.args.get('message')
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO suggestions (name, email,message) VALUES (?, ?,?)', (name, email,suggestion))
        conn.commit()
    return render_template("welcome.html")

if __name__ == '__main__':
    app.run(debug=True)
