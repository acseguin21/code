from flask import Flask, render_template, Response
import cv2
import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def load_camera_settings():
    try:
        with open('camera_config.yml', 'r') as f:
            settings = yaml.safe_load(f)
            logger.debug(f"Loaded camera settings: {settings}")
            return settings
    except Exception as e:
        logger.error(f"Error loading camera settings: {e}")
        return []

class CameraStream:
    def __init__(self, camera_settings):
        self.camera_settings = camera_settings
        logger.debug(f"Initializing camera stream with settings: {camera_settings}")
        self.cap = cv2.VideoCapture(camera_settings['url'], cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera stream: {self.camera_settings['url']}")

    def get_frames(self):
        while True:
            success, frame = self.cap.read()
            if not success:
                logger.error("Failed to read frame")
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        self.cap.release()
        logger.debug("Camera stream released")

@app.route('/')
def index():
    logger.debug("Index route accessed")
    camera_settings = load_camera_settings()
    return render_template('index.html', cameras=camera_settings)

@app.route('/video_feed/<int:camera_id>')
def video_feed(camera_id):
    logger.debug(f"Video feed requested for camera {camera_id}")
    camera_settings = load_camera_settings()
    if camera_id < len(camera_settings):
        camera_stream = CameraStream(camera_settings[camera_id])
        return Response(camera_stream.get_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    logger.error(f"Camera {camera_id} not found")
    return "Camera not found", 404

if __name__ == '__main__':
    logger.info("Starting camera server...")
    app.run(host='0.0.0.0', port=5000, debug=True) 