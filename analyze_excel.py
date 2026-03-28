import pandas as pd
import os

files = [
    ('AM', 'AMDiv_GuidePriceFormat_R00.xlsx'),
    ('HI', 'HIDiv_GuidePriceFormat_R00.xlsx'),
    ('IT', 'ITDiv_GuidePriceFormat_R00.xlsx'),
    ('LT', 'LTDiv_GuidePriceFormat_R00.xlsx')
]

quarters = ['25.1Q', '25.2Q', '25.3Q', '25.4Q', '26.1Q']
base_path = 'data_raw/'

results = []

for div, filename in files:
    full_path = os.path.join(base_path, filename)
    if not os.path.exists(full_path):
        results.append(f"\n--- {div}: File not found ---")
        continue
        
    xl = pd.ExcelFile(full_path)
    found_sheets = [s for s in xl.sheet_names if any(q in s for q in quarters)]
    
    results.append(f"=== DIVISION: {div} ===")
    for sheet in found_sheets:
        df = pd.read_excel(xl, sheet_name=sheet, nrows=1)
        results.append(f"Sheet: {sheet}")
        results.append(f"Headers: {list(df.columns)}")
        results.append(f"Data: {df.to_dict(orient='records')}")
        results.append("-" * 20)

with open('analysis_output.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(results))

print("Analysis Complete. Read analysis_output.txt")
