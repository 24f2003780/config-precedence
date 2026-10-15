
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def as_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true", "1", "yes", "on"
    }


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return as_bool(value)

    return str(value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    # Layer 2: YAML configuration.
    env_name = os.getenv("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"

    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}

        config.update(yaml_config)

    # Layer 3: .env configuration.
    env_file = dotenv_values(BASE_DIR / ".env")

    for name, value in env_file.items():
        if value is None or name == "APP_ENV":
            continue

        if name == "NUM_WORKERS":
            key = "workers"
        elif name.startswith("APP_"):
            key = name[4:].lower()
        else:
            key = name.lower()

        config[key] = value

    # Layer 4: operating-system environment variables.
    for name, value in os.environ.items():
        if name == "APP_ENV":
            continue

        if name.startswith("APP_"):
            key = name[4:].lower()
            config[key] = value

    # Layer 5: query-string overrides.
    for item in set:
        key, separator, value = item.partition("=")

        if not separator or not key:
            continue

        key = key.strip()
        value = value.strip()

        if key == "NUM_WORKERS":
            key = "workers"
        elif key.startswith("APP_"):
            key = key[4:].lower()

        config[key] = value

    # Convert values to their required types.
    for key in ("port", "workers"):
        config[key] = int(config[key])

    config["debug"] = as_bool(config["debug"])

    for key in ("log_level", "api_key"):
        config[key] = str(config[key])

    # Never expose the actual secret.
    config["api_key"] = "****"

    return config

