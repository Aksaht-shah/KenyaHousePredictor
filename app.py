# --- [IMPORTS] ---
import os
import sqlite3
import secrets
import joblib
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import re

# --- [SETUP] ---
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
DATABASE = 'users.db'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- [DATABASE CONNECTION] ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- [INITIALIZE DATABASE TABLES] ---
def init_user_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT,
                email TEXT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                status TEXT,
                timestamp TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS help_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                message TEXT,
                timestamp TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                location TEXT,
                property_type TEXT,
                city TEXT,
                bedrooms INTEGER,
                bathrooms INTEGER,
                size REAL,
                price REAL,
                image_path TEXT,
                created_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forgot_password_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                timestamp TEXT
            )
        ''')

        db.commit()

# --- [CONSTANTS] ---
KENYAN_COUNTIES = ['Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo-Marakwet', 'Embu', 'Garissa', 'Homa Bay', 'Isiolo',
    'Kajiado', 'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga', 'Kisii', 'Kisumu', 'Kitui', 'Kwale',
    'Laikipia', 'Lamu', 'Machakos', 'Makueni', 'Mandera', 'Marsabit', 'Meru', 'Migori', 'Mombasa',
    "Murang'a", 'Nairobi', 'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua', 'Nyeri', 'Samburu',
    'Siaya', 'Taita-Taveta', 'Tana River', 'Tharaka-Nithi', 'Trans Nzoia', 'Turkana', 'Uasin Gishu',
    'Vihiga', 'Wajir', 'West Pokot']
PROPERTY_TYPES = ['House', 'Apartment', 'Villa', 'Townhouse', 'Bungalow']
CITIES = ['Nairobi', 'Mombasa', 'Kisumu', 'Eldoret', 'Thika']
TEMPLATE_CONTEXT = {
    'locations': KENYAN_COUNTIES,
    'property_types': PROPERTY_TYPES,
    'cities': CITIES
}

# --- [ROUTES] ---
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password_raw = request.form['password']
        confirm_password = request.form['confirm']

        if password_raw != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('signup'))

        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password_raw):
            flash("Password must be strong.")
            return redirect(url_for('signup'))

        password = generate_password_hash(password_raw)

        db = get_db()
        try:
            db.execute("INSERT INTO users (fullname, email, username, password) VALUES (?, ?, ?, ?)",
                       (fullname, email, username, password))
            db.commit()
            flash('Account created successfully!')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.')

    return render_template('signup.html', auth_title="Sign Up", form_action=url_for('signup'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()

        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user and check_password_hash(user['password'], password):
            session['user'] = user['fullname']
            session['username'] = user['username']
            db.execute("INSERT INTO login_history (username, status, timestamp) VALUES (?, ?, ?)", (username, "success", now))
            db.commit()
            flash("✅ Login successful!")
            return redirect(url_for('dashboard'))
        else:
            db.execute("INSERT INTO login_history (username, status, timestamp) VALUES (?, ?, ?)", (username, "failure", now))
            db.commit()
            flash('❌ Invalid username or password')

    return render_template('login.html', auth_title="Login", form_action=url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = get_db()
        db.execute("INSERT INTO forgot_password_requests (email, timestamp) VALUES (?, ?)", (email, timestamp))
        db.commit()

        flash("If this email exists, a password reset link will be sent.")
        return redirect(url_for('login'))

    return render_template('forgot_password.html', title="Forgot Password")

@app.route('/logout')
def logout():
    if 'username' in session:
        username = session['username']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = get_db()
        db.execute("INSERT INTO login_history (username, status, timestamp) VALUES (?, ?, ?)", (username, "logout", timestamp))
        db.commit()

    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    db = get_db()
    props = db.execute("SELECT * FROM properties ORDER BY created_at DESC").fetchall()

    return render_template('dashboard.html', user={'name': session['user']}, properties=props, datetime=datetime, **TEMPLATE_CONTEXT)

@app.route('/help', methods=['GET', 'POST'])
def help():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = get_db()
        db.execute("INSERT INTO help_requests (name, email, message, timestamp) VALUES (?, ?, ?, ?)",
                   (name, email, message, timestamp))
        db.commit()

        flash("✅ Help request submitted.")
        return redirect(url_for('help'))

    return render_template('help.html')

@app.route('/add_property', methods=['GET', 'POST'])
def add_property():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        property_type = request.form['property_type']
        city = request.form['city']
        bedrooms = request.form['bedrooms']
        bathrooms = request.form['bathrooms']
        size = request.form['size']
        price = request.form['price']

        image = request.files.get('image')
        image_path = ''
        if image and image.filename:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = filename  # ✅ Only filename is saved

        db = get_db()
        db.execute('''
            INSERT INTO properties (name, location, property_type, city, bedrooms, bathrooms, size, price, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, location, property_type, city, bedrooms, bathrooms, size, price, image_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        db.commit()

        flash('✅ Property added successfully!')
        return redirect(url_for('dashboard'))

    return render_template('add_property.html', **TEMPLATE_CONTEXT)

@app.route('/ml_status')
def ml_status():
    if os.path.exists('kenya_house_predictor.joblib'):
        return "✅ Model is trained and ready!"
    return "❌ Model not trained yet."

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        model = joblib.load('kenya_house_predictor.joblib')
        try:
            location = request.form.get('location', '').strip()
            property_type = request.form.get('property_type', '').strip()
            city = request.form.get('city', 'N/A').strip()
            bedrooms = float(request.form.get('bedrooms', 0))
            bathrooms = float(request.form.get('bathrooms', 0))
            size = float(request.form.get('size', 0))

            county_code = KENYAN_COUNTIES.index(location)
            property_type_code = PROPERTY_TYPES.index(property_type)

            features = [[bedrooms, bathrooms, size, county_code, property_type_code]]
            prediction = model.predict(features)[0]

            return render_template('predict.html', prediction=round(prediction), **TEMPLATE_CONTEXT)
        except Exception as e:
            flash(f"Prediction error: {e}")
            return redirect(url_for('predict'))

    return render_template('predict.html', **TEMPLATE_CONTEXT)

@app.route('/view-activity')
def view_activity():
    if 'user' not in session:
        return redirect(url_for('login'))

    db = get_db()
    history = db.execute("SELECT * FROM login_history ORDER BY timestamp DESC").fetchall()
    return render_template('view_activity.html', history=history)

# --- [ENTRY POINT] ---
if __name__ == '__main__':
    init_user_db()
    app.run(debug=True, use_reloader=False)
