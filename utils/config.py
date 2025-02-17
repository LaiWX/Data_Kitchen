import json
import os
import base64
from typing import Optional, Dict

class ConfigManager:
    def __init__(self):
        self.config_file = "settings.json"
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_auth_header(self) -> Optional[Dict[str, str]]:
        """Get authorization header from saved credentials"""
        username = self.config.get('username')
        password = self.config.get('password')
        
        if username and password:
            credentials = f"{username}:{password}"
            auth = base64.b64encode(credentials.encode()).decode()
            return {'Authorization': f'Basic {auth}'}
        return None

    def set_credentials(self, username: str, password: str):
        """Save credentials to config"""
        self.config['username'] = username
        self.config['password'] = password
        self.save_config()

    def get_last_url(self) -> Optional[str]:
        """Get last used URL"""
        return self.config.get('last_url')

    def set_last_url(self, url: str):
        """Save last used URL"""
        self.config['last_url'] = url
        self.save_config()

    def clear_credentials(self):
        """Clear saved credentials"""
        self.config.pop('username', None)
        self.config.pop('password', None)
        self.save_config() 