from io import BytesIO
import time
import os
import sqlite3
import requests
import json
from flask import (
    Flask, render_template, request, redirect, send_file, send_from_directory,
    url_for, jsonify, make_response
)
from flask_login import (
    LoginManager, login_user, login_required, logout_user, UserMixin, current_user
)
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS

# --- App Config ---
app = Flask(__name__, template_folder='../client')
app.secret_key = 'yourSecretKey'
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
application = app
loginManager = LoginManager()
loginManager.login_view = 'loginPage'
loginManager.init_app(app)

GAMES_JSON_URL = "https://cdn.jsdelivr.net/gh/jacobinathanialpeterson/GS@main/games.json"
GAMES_BASE_URL = "https://cdn.jsdelivr.net/gh/jacobinathanialpeterson/GS@main/games"

DOWNLOAD_COUNTS_FILE = "downloadCounts.json"

# --- Database Setup ---
def initDb():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                displayName TEXT NOT NULL,
                email TEXT,
                permissions INTEGER NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                gameId TEXT NOT NULL,
                timestamp INT NOT NULL,
                UNIQUE(username, gameId)
            )
        ''')
        users = [
            ('testviewer', '0', 'Test User 0', 'viewer@example.com', 0),
            ('testuser', '1', 'Test User 1', 'user@example.com', 1),
            ('testadmin', '2', 'Test User 2', 'admin@example.com', 2),
        ]
        for username, password, displayName, email, permissions in users:
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password, displayName, email, permissions)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, generate_password_hash(password), displayName, email, permissions))
        conn.commit()

# --- User Model ---
class User(UserMixin):
    def __init__(self, userId, username, displayName, permissions, downloads):
        self.id = userId
        self.username = username
        self.displayName = displayName
        self.permissions = permissions
        self.downloads = downloads

# --- User Utilities ---
def getUserByUsername(username):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password, displayName, email, permissions FROM users WHERE username = ?",
            (username,))
        user = cursor.fetchone()
        if user:
            cursor.execute("SELECT gameId FROM downloads WHERE username = ?", (user[1],))
            downloads = [row[0] for row in cursor.fetchall()]
            user = [user[0], user[1], user[2], user[3], user[4], user[5], downloads]
        return user

def getUserByEmail(email):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password, displayName, email, permissions FROM users WHERE email = ?",
            (email,))
        user = cursor.fetchone()
        if user:
            cursor.execute("SELECT gameId FROM downloads WHERE username = ?", (user[1],))
            downloads = [row[0] for row in cursor.fetchall()]
            user = [user[0], user[1], user[2], user[3], user[4], user[5], downloads]
        return user

def getUserById(userId):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password, displayName, email, permissions FROM users WHERE id = ?",
            (userId,))
        user = cursor.fetchone()
        if user:
            cursor.execute("SELECT gameId FROM downloads WHERE username = ?", (user[1],))
            downloads = [row[0] for row in cursor.fetchall()]
            user = [user[0], user[1], user[2], user[3], user[4], user[5], downloads]
        return user

@loginManager.user_loader
def loadUser(userId):
    user = getUserById(userId)
    if user:
        return User(user[0], user[1], user[3], user[5], user[6])
    return None

@loginManager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "message": "Login required"}), 401
    return redirect(url_for('loginPage'))

# --- Auth Routes ---
@app.route('/api/login', methods=['POST'])
def apiLogin():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Missing JSON data"}), 400
    usernameOrEmail = data.get('username')
    password = data.get('password')
    if not usernameOrEmail or not password:
        return jsonify({"success": False, "message": "Username/email and password required"}), 400
    user = getUserByUsername(usernameOrEmail) or getUserByEmail(usernameOrEmail)
    if user and check_password_hash(user[2], password):
        login_user(User(user[0], user[1], user[3], user[5], user[6]))
        return jsonify({"success": True, "message": "Login successful"}), 200
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/register', methods=['POST'])
def apiRegister():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Missing JSON data"}), 400
    username = data.get('username')
    password = data.get('password')
    displayName = data.get('displayName')
    email = data.get('email')
    if not username or not password or not displayName or not email:
        return jsonify({"success": False, "message": "Username, password, display name, and email required"}), 400
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, displayName, email) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), displayName, email)
            )
            conn.commit()
            user = getUserByUsername(username)
            if user:
                login_user(User(user[0], user[1], user[3], user[5], user[6]))
            return jsonify({"success": True, "message": "Registration successful"}), 201
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "Username already exists"}), 409

@app.route('/api/currentUser', methods=['GET'])
@login_required
def apiCurrentUser():
    user = getUserById(current_user.id)
    if user:
        return jsonify({
            "success": True,
            "message": {
                "id": user[0],
                "username": user[1],
                "displayName": user[3],
                "email": user[4],
                "permissions": user[5],
                "downloads": user[6]
            }
        }), 200
    return jsonify({"success": False, "message": "User not found"}), 404

# --- Game API Routes ---
@app.route('/api/games', methods=['GET'])
@login_required
def apiGames():
    try:
        response = requests.get(GAMES_JSON_URL)
        response.raise_for_status()
        games = response.json()
        return jsonify({"success": True, "message": games}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve games: {str(e)}"}), 500

def loadDownloadCounts():
    if not os.path.exists(DOWNLOAD_COUNTS_FILE):
        return {}
    with open(DOWNLOAD_COUNTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def saveDownloadCounts(counts):
    with open(DOWNLOAD_COUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)

@app.route('/api/download', methods=['POST'])
@login_required
def apiDownload():
    data = request.get_json()
    if not data or 'gameId' not in data:
        return jsonify({"success": False, "message": "Missing game ID"}), 400
    if int(current_user.permissions) < 1:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    gameId = data['gameId']
    try:
        response = requests.get(GAMES_JSON_URL)
        response.raise_for_status()
        games = response.json()
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to load games.json: {str(e)}"}), 500
    if gameId not in games:
        return jsonify({"success": False, "message": "Game ID not found"}), 404
    game = games[gameId]
    parts = game.get("gameParts", 1)
    if parts <= 0:
        return jsonify({"success": False, "message": "Invalid number of game parts"}), 400
    combinedData = BytesIO()
    if parts == 1:
        gameUrls = [f"{GAMES_BASE_URL}/game-{gameId}.zip"]
    else:
        gameUrls = [f"{GAMES_BASE_URL}/game-{gameId}.zip.{i:03d}" for i in range(parts)]
    for url in gameUrls:
        try:
            print(f"Downloading: {url}")
            partResponse = requests.get(url)
            partResponse.raise_for_status()
            combinedData.write(partResponse.content)
        except Exception as e:
            print(f"❌ Error downloading part: {url}")
            return jsonify({"success": False, "message": f"Failed to download {url}: {str(e)}"}), 500
    combinedData.seek(0)

    # Update download count in JSON file
    counts = loadDownloadCounts()
    counts[gameId] = counts.get(gameId, 0) + 1
    saveDownloadCounts(counts)

    # Still record user download in DB for user tracking
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO downloads (username, gameId, timestamp) VALUES (?, ?, ?)",
            (current_user.username, gameId, int(time.time()))
        )
        conn.commit()
    return send_file(
        combinedData,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'game-{gameId}.zip'
    )

@app.route('/api/removeDownload', methods=['POST'])
@login_required
def apiRemoveDownload():
    data = request.get_json()
    if not data or 'gameId' not in data:
        return jsonify(success=False, message="Missing gameId"), 400
    gameId = data['gameId']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM downloads WHERE username = ? AND gameId = ?",
            (current_user.username, gameId)
        )
        conn.commit()
    return jsonify(success=True)

@app.route('/api/downloadCounts', methods=['GET'])
@login_required
def apiDownloadCounts():
    counts = loadDownloadCounts()
    return jsonify({"success": True, "counts": counts}), 200

# --- Admin Routes ---
@app.route('/admin/userRequests', methods=['GET'])
@login_required
def adminUserRequests():
    if current_user.permissions < 2:
        return "403 Forbidden", 403
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, displayName, email FROM users WHERE permissions = 0")
        users = cursor.fetchall()
    return jsonify({
        "success": True,
        "message": [
            {"id": user[0], "username": user[1], "displayName": user[2], "email": user[3]}
            for user in users
        ]
    }), 200

@app.route('/admin/approveUser', methods=['POST'])
@login_required
def adminApproveUser():
    if current_user.permissions < 2:
        return jsonify(success=False, message="Forbidden"), 403
    data = request.get_json()
    userId = data.get('userId')
    if not userId:
        return jsonify(success=False, message="Missing userId"), 400
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET permissions = 1 WHERE id = ? AND permissions = 0",
            (userId,)
        )
        conn.commit()
        updated = cursor.rowcount
    if updated:
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="User not found or already approved"), 404

@app.route('/admin/declineUser', methods=['POST'])
@login_required
def adminDeclineUser():
    if current_user.permissions < 2:
        return jsonify(success=False, message="Forbidden"), 403
    data = request.get_json()
    userId = data.get('userId')
    if not userId:
        return jsonify(success=False, message="Missing userId"), 400
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM users WHERE id = ? AND permissions = 0",
            (userId,)
        )
        conn.commit()
        deleted = cursor.rowcount
    if deleted:
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="User not found or already processed"), 404

# --- Page Routes ---
@app.route('/login', methods=['GET'])
def loginPage():
    if current_user.is_authenticated:
        return redirect(url_for('dashboardPage'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('loginPage'))

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboardPage():
    return render_template('dashboard.html')

@app.route('/register', methods=['GET'])
def registerPage():
    if current_user.is_authenticated:
        return redirect(url_for('dashboardPage'))
    return render_template('register.html')

@app.route('/play', methods=['GET'])
@login_required
def playPage():
    if current_user.permissions < 1:
        return "403 Forbidden", 403
    resp = make_response(render_template('play.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/play/<path:subpath>', methods=['GET'])
@login_required
def playSubpath(subpath):
    # This is just for the service worker to intercept, or you can serve a placeholder
    return render_template('game.html')

@app.route('/game/<path:subpath>', methods=['GET'])
@login_required
def gameSubpath(subpath):
    if current_user.permissions < 1:
        return "403 Forbidden", 403
    resp = make_response(render_template('game.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/style.css', methods=['GET'])
def serveCss():
    return send_from_directory('../client', 'style.css')

@app.route('/sw.js', methods=['GET'])
def serveSw():
    resp = make_response(send_from_directory('../client', 'sw.js'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

# --- Main ---
if __name__ == '__main__':
    initDb()
    app.run(debug=True)
