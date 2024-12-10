import cv2
import yaml
from flask import Flask, render_template, Response

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True)
