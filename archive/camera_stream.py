import cv2
import time
import sys
import yaml
import subprocess
import os
from pathlib import Path
import numpy as np

print(f"Using Python from: {sys.executable}")

class CameraStream:
    def __init__(self):
        self.config_file = Path('camera_config.yml')
        self.camera_settings = self.load_or_create_settings()
        
    def load_or_create_settings(self):
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                settings = yaml.safe_load(f)
                if settings:
                    return self.select_camera(settings)
        return self.prompt_for_settings()

    def prompt_for_settings(self):
        print("\nEnter ONVIF camera settings:")
        settings = {
            'name': input("Camera name: "),
            'ip': input("IP address [192.168.1.65]: ") or "192.168.1.65",
            'port': input("Port [8554]: ") or "8554",
            'username': input("Username [admin]: ") or "admin",
            'password': input("Password: ")  # It's better not to use default passwords for security
        }
        
        # Set URL using the correct format for your camera
        settings['url'] = f"rtsp://{settings['username']}:{settings['password']}@{settings['ip']}:{settings['port']}/Streaming/Channels/101"
        
        print(f"\nUsing URL: {settings['url']}")
        
        # Save to existing or new config
        self.save_settings(settings)
        return settings

    def save_settings(self, new_settings):
        existing_settings = []
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                existing_settings = yaml.safe_load(f) or []
                
        if not isinstance(existing_settings, list):
            existing_settings = []
            
        existing_settings.append(new_settings)
        
        with open(self.config_file, 'w') as f:
            yaml.dump(existing_settings, f, default_flow_style=False, sort_keys=False)

    def select_camera(self, settings):
        if not isinstance(settings, list):
            return settings
            
        print("\nAvailable cameras:")
        for i, camera in enumerate(settings):
            print(f"{i+1}. {camera['name']} ({camera['ip']})")
        print(f"{len(settings)+1}. Add new camera")
        
        while True:
            try:
                choice = int(input("\nSelect camera (enter number): "))
                if 1 <= choice <= len(settings):
                    return settings[choice-1]
                elif choice == len(settings)+1:
                    return self.prompt_for_settings()
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def test_connection(self):
        """Test the RTSP connection and print detailed information"""
        stream_url = self.camera_settings['url']
        print(f"\nTesting connection to: {stream_url}")

        # Test commands with different transport protocols
        test_commands = [
            ['ffprobe', '-v', 'error', '-rtsp_transport', 'tcp', '-i', stream_url],
            ['ffprobe', '-v', 'error', '-rtsp_transport', 'udp', '-i', stream_url],
            ['ffprobe', '-v', 'error', '-i', stream_url]
        ]

        for cmd in test_commands:
            print(f"\nTrying: {' '.join(cmd)}")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10  # Increased timeout for connection issues
                )
                if result.returncode == 0:
                    print("Connection successful!")
                    return True
                else:
                    print(f"Error: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                print("Connection timed out")
            except Exception as e:
                print(f"Error: {str(e)}")

        return False

    def start_stream(self):
        try:
            stream_url = self.camera_settings['url']
            print(f"\nAttempting to connect to: {stream_url}")

            # FFmpeg command to test connection and stream
            # Commented out as we've already tested the connection
            # Uncomment if you wish to use FFmpeg directly
            '''
            ffmpeg_cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', stream_url,
                '-f', 'image2pipe',
                '-pix_fmt', 'bgr24',
                '-vcodec', 'rawvideo',
                '-'
            ]

            # Start FFmpeg process
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            '''

            # Create capture object with FFMPEG backend
            cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
            
            if not cap.isOpened():
                print("Error: Could not open camera stream with OpenCV.")
                return

            print(f"\nStarting stream for camera: {self.camera_settings['name']}")
            print("Press 'q' to stop")

            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Error: Can't receive frame (stream ended?)")
                    break

                # Display the frame
                cv2.imshow('Camera Stream', frame)

                # Break the loop if 'q' is pressed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Quitting stream...")
                    break

        except KeyboardInterrupt:
            print("\nStopping camera stream...")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            # Clean up
            if 'cap' in locals() and cap is not None:
                cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    stream = CameraStream()
    # Test connection first
    if stream.test_connection():
        stream.start_stream()
    else:
        print("\nFailed to establish connection to the camera.") 