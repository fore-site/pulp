from dotenv import load_dotenv
from pathlib import Path
import os
import psycopg

dev_env_path = Path(__file__).resolve().parent.parent / '.env'

load_dotenv(dotenv_path=dev_env_path)

DATABASE_URI = os.getenv('DATABASE_URI')

conn = psycopg.connect(DATABASE_URI)
cur = conn.cursor()

with open('init_db.sql', 'r') as r:
    sql_script = r.read()
    cur.execute(sql_script)
    conn.commit()

conn.close()