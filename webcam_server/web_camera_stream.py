import cv2
import yaml
from flask import Flask, render_template, Response, redirect, request, url_for, session
from requests_oauthlib import OAuth2Session
import requests
import os
from dotenv import load_dotenv
from urllib.parse import quote, urlencode

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Load environment variables from .env file
load_dotenv()

# OAuth2 Configuration
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
AUTHORIZATION_BASE_URL = 'https://api.yosmart.com/oauth2/authorize'
TOKEN_URL = 'https://api.yosmart.com/oauth2/token'
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Initialize OAuth2 session
oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=['read', 'write'])

# Camera Configuration
UAID = quote(os.getenv('UAID'))
SECRET_KEY = quote(os.getenv('SECRET_KEY'))

class CameraStream:
    def __init__(self, camera_settings):
        self.camera_settings = camera_settings
        self.cap = None

    def get_video_stream(self):
        """Generator function to yield video frames"""
        stream_url = self.camera_settings['url']
        print(f"\nAttempting to connect to: {stream_url}")

        # Create capture object with FFMPEG backend
        self.cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)

        if not self.cap.isOpened():
            print(f"Error: Could not open camera stream for {self.camera_settings['name']}.")
            return

        print(f"\nStreaming started for camera: {self.camera_settings['name']}")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print(f"Error: Can't receive frame from {self.camera_settings['name']} (stream ended?)")
                break

            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print(f"Error: Failed to encode frame from {self.camera_settings['name']}.")
                continue

            frame = buffer.tobytes()

            # Yield the frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        # Cleanup
        self.cap.release()
        print(f"Streaming stopped for camera: {self.camera_settings['name']}")

def load_camera_settings():
    with open('camera_config.yml', 'r') as f:
        return yaml.safe_load(f)

def get_yolink_sensor_data(token):
    api_url = "https://api.yosmart.com/open/yolink/v2/api"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "method": "Home.getDeviceList",
        "params": {
            "uaid": UAID
        }
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        print("API Response:", data)  # Log the API response
        return data.get('data', [])
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            # Unauthorized, possibly token expired
            refresh_token()
            # Retry the request after refreshing token
            token = session.get('oauth_token')['access_token']
            headers["Authorization"] = f"Bearer {token}"
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            print("API Response after refresh:", data)  # Log the API response
            return data.get('data', [])
        else:
            print(f"HTTP error occurred: {http_err}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching YoLink data: {e}")
        return []

@app.route('/')
def index():
    """Home page."""
    camera_settings = load_camera_settings()
    return render_template('index.html', cameras=camera_settings)

@app.route('/video_feed/<int:camera_id>')
def video_feed(camera_id):
    """Video streaming route. Put this in the src attribute of an img tag."""
    camera_settings = load_camera_settings()
    if camera_id < len(camera_settings):
        camera_stream = CameraStream(camera_settings[camera_id])
        return Response(camera_stream.get_video_stream(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Camera not found", 404

@app.route('/sensors')
def sensors():
    """Sensor status page."""
    token = session.get('oauth_token')
    if not token:
        return redirect(url_for('login'))

    sensor_data = get_yolink_sensor_data(token['access_token'])
    return render_template('sensors.html', sensors=sensor_data)

@app.route('/login')
def login():
    """Step 1: User Authorization.
    Redirect the user/resource owner to the OAuth provider (YoLink)
    using an URL with a few key OAuth parameters.
    """
    authorization_url, state = oauth.authorization_url(AUTHORIZATION_BASE_URL)

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    """Step 2: Retrieving an access token.
    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """
    oauth.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET,
                      authorization_response=request.url)

    # Save token in session
    session['oauth_token'] = oauth.token
    return redirect(url_for('sensors'))

@app.route('/logout')
def logout():
    """Logout the user by clearing the session."""
    session.clear()
    return redirect(url_for('index'))

def refresh_token():
    """Refresh the OAuth2 access token using the refresh token."""
    extra = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }

    oauth = OAuth2Session(CLIENT_ID, token=session.get('oauth_token'), auto_refresh_kwargs=extra,
                          auto_refresh_url=TOKEN_URL, token_updater=token_updater)

    try:
        new_token = oauth.refresh_token(TOKEN_URL)
        session['oauth_token'] = new_token
        print("Token refreshed successfully.")
    except Exception as e:
        print(f"Error refreshing token: {e}")

def token_updater(token):
    """Update the session with the new token."""
    session['oauth_token'] = token

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True)
