import os
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENROUTER_API_KEY: str = ""
    GOOGLE_API_KEY: str
    DATABASE_URL: str
    ENVIRONMENT: str = "production"
    
    class Config:
        env_file = ".env"

settings = Settings()

class RuntimeConfigManager:
    """Handles hot-reloading of runtime configuration without backend restarts."""
    def __init__(self, config_path="runtime_config.json"):
        self.config_path = config_path
        self._last_mtime = 0
        self._cache = {}

    def get(self):
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self._last_mtime:
                with open(self.config_path, "r") as f:
                    self._cache = json.load(f)
                self._last_mtime = current_mtime
            return self._cache
        except Exception:
            return self._cache # Return last known good config on error

    def update(self, new_config: dict):
        with open(self.config_path, "w") as f:
            json.dump(new_config, f, indent=2)
        self._last_mtime = 0 # Force reload next time

config_manager = RuntimeConfigManager()
