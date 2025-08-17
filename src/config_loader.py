import yaml
import os

class ConfigLoader:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_feeds(self):
        return self.config.get('feeds', [])

    def get_option(self, key, default=None):
        return self.config.get(key, default)
