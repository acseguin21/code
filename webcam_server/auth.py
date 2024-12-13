from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import jwt

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username
        self.last_activity = datetime.now()

    def get_id(self):
        return self.username

class Auth:
    def __init__(self, app):
        self.login_manager = LoginManager()
        self.login_manager.init_app(app)
        self.login_manager.login_view = 'login'
        self.login_manager.login_message = 'Please log in to access this page.'
        self.users = {}
        self.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)
        
        @self.login_manager.user_loader
        def load_user(username):
            if username not in self.users:
                user = User(username)
                self.users[username] = user
            return self.users.get(username)

    def authenticate(self, username, password):
        # For development, use a simple password check
        if username == 'admin' and password == os.environ.get('ADMIN_PASSWORD', 'admin123'):
            if username not in self.users:
                user = User(username)
                self.users[username] = user
            return self.users[username]
        return None

    def generate_token(self, user_id):
        return jwt.encode(
            {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(days=1)
            },
            self.secret_key,
            algorithm='HS256'
        )

    def verify_token(self, token):
        try:
            data = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return data['user_id']
        except:
            return None 