import sqlite3
import json

conn = sqlite3.connect('price_database.db')
c = conn.cursor()
c.execute("SELECT quarter, pricing_data FROM guide_price_historical WHERE division='HI' LIMIT 1")
res = c.fetchone()
if res:
    print(res[0])
    data = json.loads(res[1])
    for k, v in data.items():
        print(f"  {k}: {v}")
else:
    print("No data for HI division.")
conn.close()
