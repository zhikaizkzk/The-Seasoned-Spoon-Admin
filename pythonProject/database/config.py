import os
from dotenv import load_dotenv

load_dotenv()

# Database URL - using SQLite by default
# For PostgreSQL, use: postgresql://user:password@localhost/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "")

# SQLAlchemy engine options
SQL_ECHO = os.getenv("SQL_ECHO", "true")
