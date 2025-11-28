from io import BytesIO
import os
import requests
import json
from flask import Flask, render_template, request, redirect, send_file, send_from_directory, url_for, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS

# os.chdir("/home/twthnn/server/")

# ------------------ App Setup ------------------
app = Flask(__name__, template_folder='../client')
app.secret_key = 'yourSecretKey'  # consider using environment variable
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
application = app

login_manager = LoginManager()
login_manager.login_view = 'loginPage'
login_manager.init_app(app)

# ------------------ Constants ------------------
gamesJsonUrl = "https://cdn.jsdelivr.net/gh/jacobinathanialpeterson/GS@main/games.json"
gamesBaseUrl = "https://cdn.jsdelivr.net/gh/jacobinathanialpeterson/GS@main/games"
downloadCountsFile = "downloadCounts.json"
usersFile = os.path.join(os.path.dirname(__file__), 'users.json')

# ------------------ User Model ------------------
class User(UserMixin):
    def __init__(self, userId, username, displayName, permissions, downloads):
        self.id = userId
        self.username = username
        self.displayName = displayName
        self.permissions = permissions
        self.downloads = downloads

# ------------------ Utility Functions ------------------
def _loadUsers():
    if not os.path.exists(usersFile):
        return []
    with open(usersFile, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def _saveUsers(users):
    try:
        with open(usersFile, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Failed to save users file {usersFile}: {e}")

def initUsers(force=False):
    if os.path.exists(usersFile) and not force:
        try:
            data = _loadUsers()
            if data:
                return
        except Exception:
            pass
    users = [
        {
            'id': 1,
            'username': 'admin',
            'password': generate_password_hash('qwer1234QWER!@#$'),
            'displayName': 'Admin',
            'email': 'twthnn.admin@gmail.com',
            'permissions': 2,
            'downloads': []
        },
        {
            'id': 2,
            'username': 'cyranicusmcneff',
            'password': generate_password_hash('qwer1234QWER!@#$'),
            'displayName': 'Cyrus Neff',
            'email': 'neffcyr000@my.jordandistrict.org',
            'permissions': 1,
            'downloads': []
        }
    ]
    _saveUsers(users)

def getUserByField(field, value):
    users = _loadUsers()
    # Case-sensitive first
    for u in users:
        if u.get(field) == value:
            return u
    # Case-insensitive fallback
    for u in users:
        if u.get(field, '').lower() == (value or '').lower():
            return u
    return None

def getUserById(userId):
    users = _loadUsers()
    for u in users:
        if u.get('id') == int(userId):
            return u
    return None

def loadDownloadCounts():
    if not os.path.exists(downloadCountsFile):
        return {}
    with open(downloadCountsFile, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def saveDownloadCounts(counts):
    with open(downloadCountsFile, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)

def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ------------------ Flask-Login Callbacks ------------------
@login_manager.user_loader
def loadUser(userId):
    u = getUserById(userId)
    if u:
        return User(u['id'], u['username'], u['displayName'], u.get('permissions', 0), u.get('downloads', []))
    return None

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "message": "Login required"}), 401
    return redirect(url_for('loginPage'))

# ------------------ API Routes ------------------
@app.route('/api/login', methods=['POST'])
def apiLogin():
    data = request.get_json() or {}
    usernameOrEmail = data.get('username')
    password = data.get('password')
    if not usernameOrEmail or not password:
        return jsonify({"success": False, "message": "Username/email and password required"}), 400

    u = getUserByField('username', usernameOrEmail) or getUserByField('email', usernameOrEmail)
    if u and check_password_hash(u['password'], password):
        login_user(User(u['id'], u['username'], u['displayName'], u.get('permissions', 0), u.get('downloads', [])))
        return jsonify({"success": True, "message": "Login successful"}), 200
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/register', methods=['POST'])
def apiRegister():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    displayName = data.get('displayName')
    email = data.get('email')
    if not all([username, password, displayName, email]):
        return jsonify({"success": False, "message": "Username, password, display name, and email required"}), 400

    if getUserByField('username', username) or getUserByField('email', email):
        return jsonify({"success": False, "message": "Username or email already exists"}), 409

    users = _loadUsers()
    newId = max([u.get('id', 0) for u in users], default=0) + 1
    newUser = {'id': newId, 'username': username, 'password': generate_password_hash(password),
               'displayName': displayName, 'email': email, 'permissions': 0, 'downloads': []}
    users.append(newUser)
    _saveUsers(users)
    login_user(User(newUser['id'], username, displayName, 0, []))
    return jsonify({"success": True, "message": "Registration successful"}), 201

@app.route('/api/currentUser', methods=['GET'])
@login_required
def apiCurrentUser():
    u = getUserById(current_user.id)
    if u:
        return jsonify({"success": True, "message": {
            "id": u['id'],
            "username": u['username'],
            "displayName": u['displayName'],
            "email": u['email'],
            "permissions": u.get('permissions', 0),
            "downloads": u.get('downloads', []),
            "avatar": u.get('avatar')
        }}), 200
    return jsonify({"success": False, "message": "User not found"}), 404

@app.route('/api/updateProfile', methods=['POST'])
@login_required
def apiUpdateProfile():
    data = request.get_json() or {}
    u = getUserById(current_user.id)
    if not u:
        return jsonify(success=False, message="User not found"), 404

    if 'displayName' in data: u['displayName'] = data['displayName']
    if 'email' in data: u['email'] = data['email']
    if 'password' in data and data['password']: u['password'] = generate_password_hash(data['password'])
    if 'avatar' in data: u['avatar'] = data['avatar']

    users = _loadUsers()
    for i, user in enumerate(users):
        if user['id'] == u['id']:
            users[i] = u
            break
    _saveUsers(users)
    return jsonify(success=True, message="Profile updated"), 200

@app.route('/api/games', methods=['GET'])
@login_required
def apiGames():
    try:
        r = requests.get(gamesJsonUrl)
        r.raise_for_status()
        return jsonify({"success": True, "message": r.json()}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve games: {str(e)}"}), 500

@app.route('/api/download', methods=['POST'])
@login_required
def apiDownload():
    if int(current_user.permissions) < 1:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403

    data = request.get_json() or {}
    gameId = data.get('gameId')
    if not gameId:
        return jsonify({"success": False, "message": "Missing game ID"}), 400

    try:
        games = requests.get(gamesJsonUrl).json()
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to load games.json: {str(e)}"}), 500

    if gameId not in games:
        return jsonify({"success": False, "message": "Game ID not found"}), 404

    game = games[gameId]
    parts = game.get("gameParts", 1)
    if parts <= 0: return jsonify({"success": False, "message": "Invalid number of game parts"}), 400

    combinedData = BytesIO()
    urls = [f"{gamesBaseUrl}/game-{gameId}.zip"] if parts == 1 else [f"{gamesBaseUrl}/game-{gameId}.zip.{i:03d}" for i in range(parts)]
    for url in urls:
        try:
            partResp = requests.get(url)
            partResp.raise_for_status()
            combinedData.write(partResp.content)
        except Exception as e:
            return jsonify({"success": False, "message": f"Failed to download {url}: {str(e)}"}), 500

    combinedData.seek(0)

    # Update counts
    counts = loadDownloadCounts()
    counts[gameId] = counts.get(gameId, 0) + 1
    saveDownloadCounts(counts)

    # Update user downloads
    users = _loadUsers()
    for u in users:
        if u['username'] == current_user.username:
            if gameId not in u.get('downloads', []):
                u.setdefault('downloads', []).append(gameId)
            break
    _saveUsers(users)

    return send_file(combinedData, mimetype='application/zip', as_attachment=True, download_name=f'game-{gameId}.zip')

@app.route('/api/removeDownload', methods=['POST'])
@login_required
def apiRemoveDownload():
    data = request.get_json() or {}
    gameId = data.get('gameId')
    if not gameId: return jsonify(success=False, message="Missing gameId"), 400

    users = _loadUsers()
    for u in users:
        if u['username'] == current_user.username:
            u['downloads'] = [d for d in u.get('downloads', []) if d != gameId]
            break
    _saveUsers(users)
    return jsonify(success=True)

@app.route('/api/downloadCounts', methods=['GET'])
@login_required
def apiDownloadCounts():
    return jsonify({"success": True, "counts": loadDownloadCounts()}), 200

# ------------------ Admin Routes ------------------
@app.route('/admin/userRequests', methods=['GET'])
@login_required
def adminUserRequests():
    if current_user.permissions < 2: return "403 Forbidden", 403
    users = _loadUsers()
    pending = [u for u in users if u.get('permissions', 0) == 0]
    return jsonify({"success": True, "message": [{"id": u['id'], "username": u['username'], "displayName": u['displayName'], "email": u['email']} for u in pending]}), 200

@app.route('/admin/approveUser', methods=['POST'])
@login_required
def adminApproveUser():
    if current_user.permissions < 2: return jsonify(success=False, message="Forbidden"), 403
    userId = request.get_json().get('userId')
    if not userId: return jsonify(success=False, message="Missing userId"), 400
    users = _loadUsers()
    updated = False
    for u in users:
        if u['id'] == int(userId) and u.get('permissions', 0) == 0:
            u['permissions'] = 1
            updated = True
            break
    if updated: _saveUsers(users); return jsonify(success=True)
    return jsonify(success=False, message="User not found or already approved"), 404

@app.route('/admin/declineUser', methods=['POST'])
@login_required
def adminDeclineUser():
    if current_user.permissions < 2: return jsonify(success=False, message="Forbidden"), 403
    userId = request.get_json().get('userId')
    if not userId: return jsonify(success=False, message="Missing userId"), 400
    users = [u for u in _loadUsers() if not (u['id'] == int(userId) and u.get('permissions', 0) == 0)]
    _saveUsers(users)
    return jsonify(success=True)

# ------------------ Page Routes ------------------
@app.route('/login', methods=['GET'])
def loginPage():
    return redirect(url_for('dashboardPage')) if current_user.is_authenticated else render_template('login.html')

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
    return redirect(url_for('dashboardPage')) if current_user.is_authenticated else render_template('register.html')

@app.route('/play', methods=['GET'])
@login_required
def playPage():
    if current_user.permissions < 1: return "403 Forbidden", 403
    return no_cache(make_response(render_template('play.html')))

@app.route('/play/<path:subpath>', methods=['GET'])
@login_required
def playSubpath(subpath):
    return render_template('game.html')

@app.route('/game/<path:subpath>', methods=['GET'])
@login_required
def gameSubpath(subpath):
    if current_user.permissions < 1: return "403 Forbidden", 403
    return no_cache(make_response(render_template('game.html')))

@app.route('/style.css', methods=['GET'])
def serveCss():
    return send_from_directory('../client', 'style.css')

@app.route('/sw.js', methods=['GET'])
def serveSw():
    return no_cache(make_response(send_from_directory('../client', 'sw.js')))

# ------------------ Main ------------------
if __name__ == '__main__':
    initUsers()
    app.run(debug=True)
