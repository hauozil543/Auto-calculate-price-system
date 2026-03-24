import sqlite3
import pandas as pd
import sys

# Ensure utf-8 output so print doesn't crash on windows CMD
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('price_database.db')
tables = ['standard_products', 'gm_targets', 'price_gaps', 'costs', 'users']

for table in tables:
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        print(f"\n{'='*50}")
        print(f"Table: {table.upper()} - (Total Rows: {len(df)})")
        print(f"{'='*50}")
        print(df.head(5))
    except Exception as e:
        print(f"Error reading table {table}: {e}")

conn.close()
