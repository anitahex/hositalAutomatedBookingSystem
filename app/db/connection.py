import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in your .env file.")


def connect_db():
    return psycopg2.connect(DATABASE_URL)
