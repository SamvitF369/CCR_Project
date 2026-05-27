from sqlalchemy.engine import URL

DB_NAME = "CCR Project"
DB_USER = "     "
DB_PASSWORD = ""
DB_HOST = "localhost"
DB_PORT = 5432

SQLALCHEMY_DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)