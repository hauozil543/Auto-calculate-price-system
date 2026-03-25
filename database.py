import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_PATH = "price_database.db"

def get_connection():
    """Tạo kết nối tới SQLite Database."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """Khởi tạo cấu trúc các bảng trong Database (Schema)"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Bảng Users (Người dùng và phân quyền)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            level TEXT,
            region TEXT
        )
    ''')
    
    # Bảng Standard Products
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standard_products (
            category TEXT,
            type TEXT,
            material_name TEXT,
            material_code TEXT PRIMARY KEY,
            note TEXT,
            buffer REAL
        )
    ''')

    # Bảng GM Target
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gm_targets (
            category TEXT,
            region TEXT,
            ohc REAL,
            opm REAL,
            gm_target REAL,
            PRIMARY KEY (category, region)
        )
    ''')

    # Bảng Price Gaps
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_gaps (
            category TEXT,
            range_name TEXT,
            gap_ratio REAL,
            PRIMARY KEY (category, range_name)
        )
    ''')

    # Bảng Costs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS costs (
            material_code TEXT PRIMARY KEY,
            material_description TEXT,
            q26_1_cost REAL,
            q26_2_cost REAL,
            cost_unified REAL
        )
    ''')

    # Bảng Requests
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sales_username TEXT,
            material_code TEXT,
            request_type TEXT,
            status TEXT,
            actual_yield REAL,
            base_price REAL,
            region TEXT,
            final_price REAL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')

    # Bảng Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP
        )
    ''')

    # Bảng Account Requests
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            employee_id TEXT UNIQUE,
            email TEXT UNIQUE,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP
        )
    ''')

    # Tạo User mặc định phục vụ test
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES ('admin', 'admin123', 'Admin')")
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES ('pricing_demo', '123456', 'Pricing')")
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES ('sales_demo', '123456', 'Sales')")

    conn.commit()
    conn.close()

def import_excel_to_sqlite(excel_file=r'data_raw\GuidePriceAIRaw.xlsx'):
    """Đọc dữ liệu từ file Excel và đổ vào Database SQLite để chuyển đổi nhanh"""
    if not os.path.exists(excel_file):
        return False, f"Không tìm thấy file {excel_file} để import!"

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Để đảm bảo Schema mới nhất, ta Drop và Recreate các bảng cache trước khi import
        cursor.execute("DROP TABLE IF EXISTS standard_products")
        cursor.execute("DROP TABLE IF EXISTS gm_targets")
        cursor.execute("DROP TABLE IF EXISTS price_gaps")
        cursor.execute("DROP TABLE IF EXISTS costs")
        conn.commit()
        
        # Khởi tạo lại schema
        init_db()

        # 1. Standard Product
        df_std = pd.read_excel(excel_file, sheet_name='Standard Product')
        df_std.columns = df_std.columns.str.strip()
        df_std = df_std.rename(columns={
            'Category': 'category', 'Type': 'type', 'Materials Name': 'material_name',
            'Materials Code': 'material_code', 'Note': 'note', 'Buffer': 'buffer'
        })
        if 'material_code' in df_std.columns:
            df_std['material_code'] = df_std['material_code'].astype(str).str.strip().str[:7]
            df_std = df_std.drop_duplicates(subset=['material_code'], keep='last')
        df_std.to_sql('standard_products', conn, if_exists='append', index=False)
        
        # 2. GM Target
        df_gm = pd.read_excel(excel_file, sheet_name='GM Target')
        df_gm.columns = df_gm.columns.str.strip()
        df_gm = df_gm.rename(columns={
            'Category': 'category', 'Region': 'region', 'OHC': 'ohc', 'OPM': 'opm', 'GM': 'gm_target'
        })
        df_gm.to_sql('gm_targets', conn, if_exists='append', index=False)

        # 3. Price Gap
        df_gap = pd.read_excel(excel_file, sheet_name='Price Gap')
        df_gap.columns = df_gap.columns.str.strip()
        df_gap = df_gap.rename(columns={
            'Category': 'category', 'Range': 'range_name', 'Gap': 'gap_ratio'
        })
        df_gap.to_sql('price_gaps', conn, if_exists='append', index=False)

        # 4. Cost
        df_cost = pd.read_excel(excel_file, sheet_name='Cost')
        df_cost.columns = df_cost.columns.str.strip()
        df_cost = df_cost.rename(columns={
            'Material Code': 'material_code', 
            'Material Description': 'material_description', 
            '26.1Q Cost': 'q26_1_cost',
            '26.2Q Cost': 'q26_2_cost',
            '26.2Q Cost Unified': 'cost_unified'
        })
        if 'material_code' in df_cost.columns:
            df_cost['material_code'] = df_cost['material_code'].astype(str).str.strip().str[:7]
        if 'cost_unified' in df_cost.columns:
            df_cost['cost_unified'] = pd.to_numeric(df_cost['cost_unified'], errors='coerce').fillna(0)
            
        if 'material_code' in df_cost.columns:
            df_cost = df_cost.drop_duplicates(subset=['material_code'], keep='last')
            
        df_cost.to_sql('costs', conn, if_exists='append', index=False)

        conn.commit()
        conn.close()
        return True, "✅ Import dữ liệu từ Excel sang SQLite thành công!"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"❌ Lỗi khi import qua SQL: {e}"

# ==========================================
# CÁC HÀM TRUY XUẤT DỮ LIỆU (CRUD)
# ==========================================

def get_standard_product(material_code):
    """Tìm thông tin sản phẩm từ bản SQL."""
    conn = get_connection()
    query = "SELECT * FROM standard_products WHERE material_code = ?"
    df = pd.read_sql_query(query, conn, params=(material_code,))
    conn.close()
    return df

def get_cost(material_code):
    """Lấy dữ liệu chi phí của một sản phẩm."""
    conn = get_connection()
    query = "SELECT * FROM costs WHERE material_code = ?"
    df = pd.read_sql_query(query, conn, params=(material_code,))
    conn.close()
    return df

def get_gm_target(category, region):
    """Lấy số tỷ lệ GM từ DB."""
    conn = get_connection()
    query = "SELECT gm_target FROM gm_targets WHERE category = ? AND region = ?"
    cursor = conn.cursor()
    cursor.execute(query, (category, region))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def get_price_gaps(category):
    """Lấy dict phần trăm Price Gap."""
    conn = get_connection()
    query = "SELECT range_name, gap_ratio FROM price_gaps WHERE category = ?"
    df = pd.read_sql_query(query, conn, params=(category,))
    conn.close()
    if not df.empty:
        return dict(zip(df['range_name'], df['gap_ratio']))
    return {}

def log_action(username, action, details):
    """Ghi log hành vi hệ thống."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (username, action, details, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (username, action, details, datetime.now()))
    conn.commit()
    conn.close()

def request_account(name, employee_id, email):
    """Lưu yêu cầu cấp quyền từ trang đăng nhập"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO account_requests (name, employee_id, email, status, created_at)
            VALUES (?, ?, ?, 'Pending', ?)
        ''', (name, employee_id, email, datetime.now()))
        conn.commit()
        return True, "✅ Yêu cầu cấp tài khoản đã được gửi thành công!"
    except sqlite3.IntegrityError:
        return False, "❌ Lỗi: ID Nhân viên hoặc Email này đã tồn tại yêu cầu!"
    except Exception as e:
        return False, f"❌ Lỗi: {e}"
    finally:
        conn.close()

# Tự động khởi tạo cấu trúc (schema) nếu DB chưa có
init_db()

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("Đang xử lý import dữ liệu từ file Excel vào Database SQLite...")
    success, message = import_excel_to_sqlite()
    print(message)