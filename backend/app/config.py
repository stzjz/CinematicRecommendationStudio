import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "app.db")


def get_runtime_settings():
    data_source = os.getenv("RECSYS_DATA_SOURCE", "auto").strip().lower()
    db_path = os.getenv("RECSYS_DB_PATH", DEFAULT_DB_PATH).strip()
    return {"data_source": data_source, "db_path": db_path}
