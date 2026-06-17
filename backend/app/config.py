import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "app.db")
DEFAULT_METADATA_PATH = os.path.join(BASE_DIR, "data", "movie_metadata_cache.json")


def get_runtime_settings():
    data_source = os.getenv("RECSYS_DATA_SOURCE", "auto").strip().lower()
    db_path = os.getenv("RECSYS_DB_PATH", DEFAULT_DB_PATH).strip()
    metadata_path = os.getenv("RECSYS_METADATA_PATH", DEFAULT_METADATA_PATH).strip()
    return {"data_source": data_source, "db_path": db_path, "metadata_path": metadata_path}
