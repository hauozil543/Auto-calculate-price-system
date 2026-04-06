import pandas as pd
import sys

file = r"data_raw\PCR.xlsx"
xl = pd.ExcelFile(file)

with open('temp_out.txt', 'w', encoding='utf-8') as f:
    f.write(f"Sheets: {xl.sheet_names}\n")
    for s in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=s)
        f.write(f"--- Sheet: {s} ---\n")
        cols = list(df.columns)
        f.write(f"All columns: {cols}\n")
        region_cols = [c for c in cols if 'region' in str(c).lower()]
        f.write(f"Columns containing 'region': {region_cols}\n")
