
# db.py
import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
load_dotenv('./../.dbenv')


PG_HOST = os.environ["PG_HOST"]
PG_PORT = os.environ["PORT"]  
PG_DB   = os.environ["POSTGRES_DB"]
PG_USER = os.environ["POSTGRES_USER"]
PG_PASS = os.environ["POSTGRES_PASSWORD"]

pool = SimpleConnectionPool(
    1,  20,   # min 1 connection, max 20
    user=PG_USER,
    password=PG_PASS,
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB
)

def get_conn():
    print("✓ Connected to PostgreSQL")
    return pool.getconn()

def release_conn(conn):
    print("✓ Disconnecting to PostgreSQL")
    pool.putconn(conn)
