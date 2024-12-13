import cv2
import yaml
from flask import Flask, render_template, Response, jsonify, request, url_for, send_from_directory, redirect, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import logging
from ptz_controller import PTZController
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from threading import Thread
import time
import sys
from auth import Auth
import secrets
from flask_talisman import Talisman

app = Flask(__name__)

# Set logging level based on environment variable
log_level = os.environ.get('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'recordings')
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

# Add these after app initialization
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
auth = Auth(app)

# Initialize Talisman for security headers but disable HTTPS for development
talisman = Talisman(
    app,
    force_https=True,
    strict_transport_security=True,
    session_cookie_secure=True,
    content_security_policy={
        'default-src': "'self'",
        'img-src': "'self' data: blob:",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
        'font-src': "'self' https://fonts.gstatic.com",
        'connect-src': "'self' wss: https:",
    }
)

class CameraStream:
    def __init__(self, camera_settings):
        self.camera_settings = camera_settings
        self.cap = None

    def get_video_stream(self):
        """Generator function to yield video frames"""
        stream_url = self.camera_settings['url']
        logger.info(f"Attempting to connect to: {stream_url}")

        try:
            # Create capture object with FFMPEG backend
            self.cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)

            if not self.cap.isOpened():
                logger.error(f"Could not open camera stream for {self.camera_settings['name']}.")
                return

            logger.info(f"Successfully connected to camera: {self.camera_settings['name']}")

            while True:
                ret, frame = self.cap.read()
                if not ret:
                    logger.error(f"Can't receive frame from {self.camera_settings['name']} (stream ended?)")
                    break

                # Encode the frame in JPEG format
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    logger.error(f"Failed to encode frame from {self.camera_settings['name']}.")
                    continue

                frame = buffer.tobytes()

                # Yield the frame in byte format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        except Exception as e:
            logger.error(f"Error in camera stream {self.camera_settings['name']}: {str(e)}")
            raise

        finally:
            # Cleanup
            if self.cap is not None:
                self.cap.release()
                logger.info(f"Stream closed for camera: {self.camera_settings['name']}")

def load_camera_settings():
    try:
        with open('camera_config.yml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading camera config: {str(e)}")
        return []

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = auth.authenticate(username, password)
        if user:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Home page."""
    camera_settings = load_camera_settings()
    return render_template('index.html', cameras=camera_settings)

@app.route('/video_feed/<int:camera_id>')
@login_required
def video_feed(camera_id):
    """Video streaming route. Put this in the src attribute of an img tag."""
    camera_settings = load_camera_settings()
    if camera_id < len(camera_settings):
        try:
            camera_stream = CameraStream(camera_settings[camera_id])
            return Response(camera_stream.get_video_stream(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        except Exception as e:
            logger.error(f"Error in video feed for camera {camera_id}: {str(e)}")
            return f"Error: {str(e)}", 500
    else:
        return "Camera not found", 404

ptz_controllers = {}

def init_ptz_controller(camera_settings):
    """Initialize PTZ controller for a camera"""
    if 'onvif' in camera_settings:
        try:
            controller = PTZController(
                camera_settings['onvif']['host'],
                camera_settings['onvif']['username'],
                camera_settings['onvif']['password']
            )
            return controller
        except Exception as e:
            logger.error(f"Failed to initialize PTZ controller: {str(e)}")
    return None

@app.route('/ptz/<int:camera_id>/move', methods=['POST'])
def ptz_move(camera_id):
    """Handle PTZ movement commands"""
    try:
        camera_settings = load_camera_settings()
        if camera_id >= len(camera_settings):
            return jsonify({'error': 'Camera not found'}), 404

        if camera_id not in ptz_controllers:
            ptz_controllers[camera_id] = init_ptz_controller(camera_settings[camera_id])

        if not ptz_controllers[camera_id]:
            return jsonify({'error': 'PTZ not available for this camera'}), 400

        data = request.get_json()
        movement_type = data.get('type', 'continuous')
        pan = float(data.get('pan', 0))
        tilt = float(data.get('tilt', 0))
        zoom = float(data.get('zoom', 0))

        if movement_type == 'continuous':
            ptz_controllers[camera_id].move_continuous(pan, tilt, zoom)
        elif movement_type == 'absolute':
            ptz_controllers[camera_id].move_absolute(pan, tilt, zoom)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"PTZ movement error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/ptz/<int:camera_id>/stop', methods=['POST'])
def ptz_stop(camera_id):
    """Stop PTZ movement"""
    try:
        if camera_id not in ptz_controllers or not ptz_controllers[camera_id]:
            return jsonify({'error': 'PTZ not available'}), 400

        ptz_controllers[camera_id].stop()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"PTZ stop error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/ptz/<int:camera_id>/status', methods=['GET'])
def ptz_status(camera_id):
    """Get PTZ status"""
    try:
        if camera_id not in ptz_controllers or not ptz_controllers[camera_id]:
            return jsonify({'error': 'PTZ not available'}), 400

        status = ptz_controllers[camera_id].get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"PTZ status error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/current', methods=['GET'])
def get_current_settings():
    try:
        # Get settings from your storage (database/file/etc)
        settings = {
            'recordLength': 10,  # default values
            'fileSize': 100,
            'autoRecord': False,
            'quality': 'high',
            'fps': 30
        }
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    try:
        settings = request.get_json()
        # Validate settings
        if not all(key in settings for key in ['recordLength', 'fileSize', 'autoRecord', 'quality', 'fps']):
            return jsonify({'error': 'Missing required settings'}), 400
            
        # Save settings to your storage (database/file/etc)
        # For now, just log them
        logger.info(f"Updated settings: {settings}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/recordings')
def list_recordings():
    """Endpoint to list recorded videos."""
    try:
        recordings = []
        for filename in os.listdir(RECORDINGS_DIR):
            if filename.endswith('.mp4'):
                file_path = os.path.join(RECORDINGS_DIR, filename)
                file_stats = os.stat(file_path)
                recordings.append({
                    'name': filename,
                    'size': file_stats.st_size,
                    'date': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'url': url_for('static', filename=f'recordings/{filename}')
                })
        return jsonify({'recordings': recordings}), 200
    except Exception as e:
        logger.error(f"Error listing recordings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/recordings/<path:filename>')
def serve_recording(filename):
    """Serve a recorded video file."""
    try:
        return send_from_directory(RECORDINGS_DIR, filename)
    except Exception as e:
        logger.error(f"Error serving recording {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 404

class CameraRecorder:
    def __init__(self, camera_id, settings):
        self.camera_id = camera_id
        self.settings = settings
        self.is_recording = False
        self.current_recording = None
        self.recording_thread = None

    def start_recording(self):
        if not self.is_recording:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"camera_{self.camera_id}_{timestamp}.mp4"
            filepath = os.path.join(RECORDINGS_DIR, filename)
            self.current_recording = filename
            self.is_recording = True
            self.recording_thread = Thread(target=self._record_video, args=(filepath,))
            self.recording_thread.start()
            return {'status': 'started', 'filename': filename}
        return {'status': 'already_recording', 'filename': self.current_recording}

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join()
            return {'status': 'stopped', 'filename': self.current_recording}
        return {'status': 'not_recording'}

    def _record_video(self, filepath):
        try:
            cap = cv2.VideoCapture(self.settings['url'])
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = None
            
            while self.is_recording:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if out is None:
                    height, width = frame.shape[:2]
                    out = cv2.VideoWriter(filepath, fourcc, 20.0, (width, height))
                    
                out.write(frame)
                
        except Exception as e:
            logger.error(f"Recording error for camera {self.camera_id}: {str(e)}")
        finally:
            if out:
                out.release()
            if cap:
                cap.release()

camera_recorders = {}

@app.route('/camera/<int:camera_id>/record/start', methods=['POST'])
def start_recording(camera_id):
    try:
        camera_settings = load_camera_settings()
        if camera_id >= len(camera_settings):
            return jsonify({'error': 'Camera not found'}), 404

        if camera_id not in camera_recorders:
            camera_recorders[camera_id] = CameraRecorder(camera_id, camera_settings[camera_id])

        result = camera_recorders[camera_id].start_recording()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to start recording: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/camera/<int:camera_id>/record/stop', methods=['POST'])
def stop_recording(camera_id):
    try:
        if camera_id not in camera_recorders:
            return jsonify({'error': 'Camera not recording'}), 404

        result = camera_recorders[camera_id].stop_recording()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to stop recording: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/camera/<int:camera_id>/record/status', methods=['GET'])
def recording_status(camera_id):
    if camera_id in camera_recorders:
        return jsonify({
            'is_recording': camera_recorders[camera_id].is_recording,
            'current_recording': camera_recorders[camera_id].current_recording
        })
    return jsonify({'is_recording': False, 'current_recording': None})

@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Unhandled error: {str(error)}", exc_info=True)
    return jsonify({'error': str(error)}), 500

@app.route('/settings')
@login_required
def settings():
    """Settings and documentation page."""
    return render_template('settings.html')

@app.route('/api/recordings/download/<path:filename>')
@login_required
def download_recording(filename):
    """Download a specific recording."""
    try:
        return send_from_directory(
            RECORDINGS_DIR, 
            filename,
            as_attachment=True,
            attachment_filename=filename
        )
    except Exception as e:
        logger.error(f"Error downloading recording {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 404

if __name__ == "__main__":
    try:
        logger.info("Starting web camera stream server...")
        ssl_context = (
            os.environ.get('SSL_CERT_PATH', 'certs/cert.pem'),
            os.environ.get('SSL_KEY_PATH', 'certs/key.pem')
        )
        app.run(
            host='0.0.0.0',
            port=443,
            ssl_context=ssl_context,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        sys.exit(1)
