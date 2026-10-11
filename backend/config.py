import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql+psycopg2://missionsprint:change-me@localhost:5432/missionsprint")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # detect connections broken by a database restart instead of failing the first request after it
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
    CICD_STATUS_URL = os.getenv("CICD_STATUS_URL", "")
    JSON_SORT_KEYS = False


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CICD_STATUS_URL = ""
