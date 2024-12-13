import cv2
import yaml
from flask import Flask, render_template, Response, jsonify, request
import logging
from ptz_controller import PTZController

app = Flask(__name__)

# Set logging level based on environment variable
log_level = app.config.get('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

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

@app.route('/settings/<int:camera_id>', methods=['POST'])
def update_settings(camera_id):
    data = request.get_json()
    record_length = data.get('recordLength', 10)
    file_size = data.get('fileSize', 100)
    # Update the recording settings for the camera
    # Implement logic to adjust recording length, file size, and loop
    return jsonify({'status': 'success'})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True)
