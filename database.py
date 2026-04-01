import sqlite3
import pandas as pd
import os
import datetime
import json

DB_PATH = "price_database.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, role TEXT, level TEXT, region TEXT, division TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS standard_products (category TEXT, type TEXT, material_name TEXT, material_code TEXT PRIMARY KEY, note TEXT, buffer REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gm_targets (category TEXT, region TEXT, ohc REAL, opm REAL, gm_target REAL, PRIMARY KEY (category, region))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS price_gaps (category TEXT, range_name TEXT, gap_ratio REAL, PRIMARY KEY (category, range_name))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS baseline_costs (material_code TEXT PRIMARY KEY, material_description TEXT, q26_1_cost REAL, q26_2_cost REAL, cost REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, custom_id TEXT, sales_username TEXT, material_code TEXT, request_type TEXT, status TEXT, region TEXT, division TEXT, base_price REAL, actual_yield REAL, final_price REAL, range_1 REAL, range_2 REAL, range_3 REAL, range_4 REAL, range_5 REAL, target_price REAL, approval_level TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, action TEXT, details TEXT, timestamp TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS account_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT UNIQUE, name TEXT, email TEXT UNIQUE, region TEXT, level TEXT, division TEXT, status TEXT DEFAULT 'Pending', created_at TIMESTAMP)''')
    
    try: cursor.execute("ALTER TABLE users ADD COLUMN division TEXT DEFAULT 'ALL'")
    except: pass
    try: cursor.execute("ALTER TABLE account_requests ADD COLUMN division TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE requests ADD COLUMN division TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE requests ADD COLUMN target_price REAL")
    except: pass
    try: cursor.execute("ALTER TABLE requests ADD COLUMN approval_level TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE account_requests ADD COLUMN level TEXT")
    except: pass

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password_hash, role, division) VALUES ('admin', 'admin123', 'Admin', 'ALL')")
        cursor.execute("INSERT INTO users (username, password_hash, role, division) VALUES ('pricing_demo', '123456', 'Pricing', 'HI')")
        cursor.execute("INSERT INTO users (username, password_hash, role, division) VALUES ('sales_demo', '123456', 'Sales', 'HI')")

    cursor.execute('''CREATE TABLE IF NOT EXISTS guide_price_historical (id INTEGER PRIMARY KEY AUTOINCREMENT, material_code TEXT, region TEXT, division TEXT, quarter TEXT, pricing_data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(material_code, region, division, quarter))''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hist_mat ON guide_price_historical(material_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hist_div ON guide_price_historical(division)')
    
    conn.commit()
    conn.close()

def import_excel_to_sqlite(excel_file=r'data_raw\GuidePriceAIRaw.xlsx'):
    if isinstance(excel_file, str) and not os.path.exists(excel_file):
        return False, f"File not found: {excel_file}"
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS standard_products")
        cursor.execute("DROP TABLE IF EXISTS gm_targets")
        cursor.execute("DROP TABLE IF EXISTS price_gaps")
        cursor.execute("DROP TABLE IF EXISTS baseline_costs")
        conn.commit()
        init_db()

        df_std = pd.read_excel(excel_file, sheet_name='Standard Product', keep_default_na=False, na_filter=False)
        df_std.columns = df_std.columns.str.strip()
        df_std = df_std.rename(columns={'Category':'category','Type':'type','Materials Name':'material_name','Materials Code':'material_code','Note':'note','Buffer':'buffer'})
        if 'material_code' in df_std.columns:
            df_std['material_code'] = df_std['material_code'].astype(str).str.strip().str[:7]
            df_std = df_std.drop_duplicates(subset=['material_code'], keep='last')
        df_std.to_sql('standard_products', conn, if_exists='replace', index=False)
        
        df_gm = pd.read_excel(excel_file, sheet_name='GM Target', keep_default_na=False, na_filter=False)
        df_gm.columns = df_gm.columns.str.strip()
        df_gm = df_gm.rename(columns={'Category':'category','Region':'region','OHC':'ohc','OPM':'opm','GM':'gm_target'})
        df_gm.to_sql('gm_targets', conn, if_exists='replace', index=False)

        df_gap = pd.read_excel(excel_file, sheet_name='Price Gap', keep_default_na=False, na_filter=False)
        df_gap.columns = df_gap.columns.str.strip()
        df_gap = df_gap.rename(columns={'Category':'category','Range':'range_name','Gap':'gap_ratio'})
        df_gap.to_sql('price_gaps', conn, if_exists='replace', index=False)

        all_sheets = pd.ExcelFile(excel_file).sheet_names
        cost_sheet = next((s for s in all_sheets if s.lower().strip() in ['cost', 'costs', 'baseline cost', 'baseline costs']), 'Cost')
        df_cost = pd.read_excel(excel_file, sheet_name=cost_sheet, keep_default_na=False, na_filter=False)
        df_cost.columns = df_cost.columns.str.strip()
        df_cost = df_cost.rename(columns={'Material Code':'material_code','Material code':'material_code','Region':'region','Reg':'region','Material Description':'material_description','26.1Q Cost':'q26_1_cost','26.2Q Cost':'q26_2_cost','26.2Q Cost Unified':'cost','Final Cost':'cost'})
        
        for col in ['material_code', 'region']:
            if col in df_cost.columns: df_cost[col] = df_cost[col].astype(str).str.strip()
        if 'material_code' in df_cost.columns:
            df_cost['material_code'] = df_cost['material_code'].str[:7]
            subset_cols = ['material_code']
            if 'region' in df_cost.columns: subset_cols.append('region')
            df_cost = df_cost.drop_duplicates(subset=subset_cols, keep='last')
        df_cost.to_sql('baseline_costs', conn, if_exists='replace', index=False)
        conn.commit()
        conn.close()
        return True, "Import successful from Excel to SQLite."
    except Exception as e:
        return False, f"Import error: {e}"

def get_standard_product(code):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM standard_products WHERE material_code = ?", conn, params=(code,))
    conn.close()
    return df

def get_cost(code):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM baseline_costs WHERE material_code = ?", conn, params=(code,))
    conn.close()
    return df

def import_guide_price_history(excel_file, division):
    quarters = ['25.1Q', '25.2Q', '25.3Q', '25.4Q', '26.1Q']
    try:
        conn = get_connection()
        xl = pd.ExcelFile(excel_file)
        found_sheets = [s for s in xl.sheet_names if any(q in s for q in quarters)]
        total = 0
        for sheet in found_sheets:
            df = pd.read_excel(xl, sheet_name=sheet, keep_default_na=False, na_filter=False)
            df.columns = df.columns.str.strip()
            mat_col = next((c for c in df.columns if c in ['Material Code', 'Mat 7D', 'ITEM CODE']), None)
            reg_col = next((c for c in df.columns if c in ['Region', 'Reg']), None)
            if not mat_col: continue
            for _, row in df.iterrows():
                mat_val = str(row[mat_col]).strip()[:7]
                reg_val = str(row[reg_col]).strip() if reg_col else "Unknown"
                pricing_json = json.dumps(row.to_dict(), ensure_ascii=False)
                conn.execute("INSERT OR REPLACE INTO guide_price_historical (material_code, region, division, quarter, pricing_data) VALUES (?, ?, ?, ?, ?)", (mat_val, reg_val, division, sheet, pricing_json))
                total += 1
        conn.commit()
        conn.close()
        return True, f"Imported {total} records for {division} across {len(found_sheets)} quarters."
    except Exception as e:
        return False, f"Import error ({division}): {e}"

def search_guide_price_history(material_code=None, region=None, quarter=None, division=None):
    try:
        conn = get_connection()
        conditions, params = [], []
        if material_code: conditions.append("material_code = ?"); params.append(str(material_code).strip()[:7])
        if region: conditions.append("region = ?"); params.append(region)
        if quarter: conditions.append("quarter = ?"); params.append(quarter)
        if division: conditions.append("division = ?"); params.append(division)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        df = pd.read_sql_query(f"SELECT division, quarter, region, pricing_data FROM guide_price_historical {where} ORDER BY quarter DESC LIMIT 1000", conn, params=params)
        conn.close()
        if df.empty: return pd.DataFrame()
        h_list = []
        for _, row in df.iterrows():
            item = json.loads(row['pricing_data'])
            fixed = {'Division': row['division'], 'Quarter': row['quarter'], 'Region': row['region']}
            fixed.update(item)
            h_list.append(fixed)
        return pd.DataFrame(h_list)
    except: return pd.DataFrame()

def get_historical_summary():
    try:
        conn = get_connection()
        query = "SELECT division, quarter, COUNT(*) as count FROM guide_price_historical GROUP BY division, quarter"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if df.empty: return pd.DataFrame()
        pivot_df = df.pivot(index='division', columns='quarter', values='count').fillna(0).astype(int)
        return pivot_df
    except: return pd.DataFrame()

def get_gm_target(category, region):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT gm_target FROM gm_targets WHERE category = ? AND region = ?", (category, region))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0.0

def get_price_gaps(category):
    conn = get_connection()
    df = pd.read_sql_query("SELECT range_name, gap_ratio FROM price_gaps WHERE category = ?", conn, params=(category,))
    conn.close()
    return dict(zip(df['range_name'], df['gap_ratio']))

def calculate_full_pricing_suite(category, region, cost, yields=1.0, b1=None, b2=0.0):
    gm = get_gm_target(category, region)
    if b1 is None:
        conn = get_connection()
        p = pd.read_sql_query("SELECT buffer FROM standard_products WHERE category = ?", conn, params=(category,))
        conn.close()
        b1 = float(p['buffer'].iloc[0]) if not p.empty else 0.0
    gp_base = ((1+b1)*(cost/yields))/(1-gm) if (0<gm<1 and cost>0 and yields>0) else 0.0
    gaps = get_price_gaps(category)
    res = {"gp_base": gp_base, "target_gm": gm, "buffer_1": b1, "yields": yields}
    for i in range(1, 6):
        gp_n = gp_base * (1 + gaps.get(f"Range {i}", 0.0)) * (1 + b2)
        res[f"gp_r{i}"] = gp_n
        res[f"vp_r{i}"] = gp_n * 0.95
        if i == 5:
            res["gt"] = res[f"vp_r{i}"] * 0.95
            res["st"] = res["gt"] * 0.95
    return res

def generate_request_id(div, reg):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM requests WHERE date(created_at) = date('now')")
    count = c.fetchone()[0]
    conn.close()
    return f"{div}-{reg}-{datetime.datetime.now().strftime('%Y%m%d')}-{(count+1):03d}"

def log_action(user, action, details):
    conn = get_connection()
    conn.execute("INSERT INTO logs (username, action, details, timestamp) VALUES (?, ?, ?, ?)", (user, action, details, datetime.datetime.now()))
    conn.commit()
    conn.close()

def request_account(name, employee_id, email, level, division):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO account_requests (name, employee_id, email, level, division, status, created_at) VALUES (?, ?, ?, ?, ?, 'Pending', ?)", (name, employee_id, email, level, division, datetime.datetime.now()))
        conn.commit()
        return True, "Account request submitted successfully!"
    except sqlite3.IntegrityError: return False, "Error: Employee ID or Email already exists."
    except Exception as e: return False, f"Error: {e}"
    finally: conn.close()

def send_email_notification(to_email, subject, body):
    try:
        import pythoncom
        pythoncom.CoInitialize()
        import win32com.client
        outlook = win32com.client.Dispatch('outlook.application')
        mail = outlook.CreateItem(0)
        mail.To = to_email
        mail.Subject = subject
        mail.Body = body
        mail.Send()
        
        try:
            namespace = outlook.GetNamespace("MAPI")
            sync = namespace.SyncObjects.Item(1)
            sync.Start()
        except:
            pass
            
        return True
    except Exception as e:
        print(f"Outlook Error: {e}")
        return False

init_db()