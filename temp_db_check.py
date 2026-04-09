import sqlite3
import pandas as pd

conn = sqlite3.connect("price_database.db")
print("PCR Reports:")
print(pd.read_sql_query("SELECT * FROM pcr_reports", conn))
print("\nPCR Report Details (First 5):")
print(pd.read_sql_query("SELECT * FROM pcr_report_details LIMIT 5", conn))
conn.close()
