"""Global configuration.

Settings are read from the environment, falling back to the defaults below, so
the app runs out of the box in development and is configured by env vars
everywhere else. Module-local settings belong in that module's own config.py.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Relative path, so the database file sits next to this project's root when
    # the app is started from there.
    DATABASE_URL: str = "sqlite:///perfume.db"

    APP_TITLE: str = "Perfume Inventory"

    # Logging is configured from this file at startup; see logging.ini.
    LOGGING_CONFIG_FILE: str = "logging.ini"


settings = Settings()
