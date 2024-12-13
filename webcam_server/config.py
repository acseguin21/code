import os
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        self.key = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher_suite = Fernet(self.key)

    def encrypt_value(self, value):
        return self.cipher_suite.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value):
        return self.cipher_suite.decrypt(encrypted_value.encode()).decode()

    def load_camera_config(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            # Decrypt sensitive values
            for camera in config:
                if 'onvif' in camera:
                    camera['onvif']['password'] = self.decrypt_value(camera['onvif']['password'])
            return config 