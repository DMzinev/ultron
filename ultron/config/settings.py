"""Runtime settings manager for Ultron."""
import os
import json

class Settings:
    @staticmethod
    def get_resources_dir():
        return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "resources"))

    @staticmethod
    def get_weights_path():
        return os.path.normpath(os.path.join(Settings.get_resources_dir(), "weights.json"))
