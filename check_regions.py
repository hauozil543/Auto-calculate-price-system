import sqlite3
import pandas as pd

conn = sqlite3.connect("price_database.db")
print("Distinct Regions in pcr_report_details:")
print(pd.read_sql_query("SELECT DISTINCT region FROM pcr_report_details", conn))
print("\nUser roles and levels for testing:")
print(pd.read_sql_query("SELECT username, role, level, region FROM users", conn))
conn.close()
