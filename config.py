import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "ppppp")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql://root:1234@localhost/electronics_store")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
