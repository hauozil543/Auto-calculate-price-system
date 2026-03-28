import sqlite3
import pandas as pd
import os
import datetime
import json

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
            region TEXT,
            division TEXT
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
            custom_id TEXT,
            sales_username TEXT,
            material_code TEXT,
            request_type TEXT,
            status TEXT,
            region TEXT,
            division TEXT,
            base_price REAL,
            actual_yield REAL,
            final_price REAL,
            range_1 REAL,
            range_2 REAL,
            range_3 REAL,
            range_4 REAL,
            range_5 REAL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')

    # Migration: Add custom_id column if it doesn't exist
    cursor.execute("PRAGMA table_info(requests)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'custom_id' not in columns:
        cursor.execute("ALTER TABLE requests ADD COLUMN custom_id TEXT")

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

    # Bảng Tài Khoản Chờ Phê Duyệt
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE,
            name TEXT,
            email TEXT UNIQUE,
            region TEXT,
            level TEXT,
            division TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP
        )
    ''')
    
    # Migration: Thêm các cột division nếu chưa có
    try: cursor.execute("ALTER TABLE users ADD COLUMN division TEXT DEFAULT 'ALL'")
    except: pass
    try: cursor.execute("ALTER TABLE account_requests ADD COLUMN division TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE requests ADD COLUMN division TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE account_requests ADD COLUMN level TEXT")
    except: pass

    # Tạo User mặc định phục vụ test
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password_hash, role, division) VALUES ('admin', 'admin123', 'Admin', 'ALL')")
        cursor.execute("INSERT INTO users (username, password_hash, role, division) VALUES ('pricing_demo', '123456', 'Pricing', 'HI')")
        cursor.execute("INSERT INTO users (username, password_hash, role, division) VALUES ('sales_demo', '123456', 'Sales', 'HI')")

    # Bảng lưu lịch sử Guide Price từ các file Excel mẫu của 4 Division
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guide_price_historical (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_code TEXT,
            region TEXT,
            division TEXT,
            quarter TEXT,
            pricing_data TEXT, -- Lưu toàn bộ Row dưới dạng JSON để linh hoạt số cột
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(material_code, region, division, quarter) -- Chống trùng lặp
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hist_mat ON guide_price_historical(material_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hist_div ON guide_price_historical(division)')
    
    conn.commit()
    conn.close()

def import_excel_to_sqlite(excel_file=r'data_raw\GuidePriceAIRaw.xlsx'):
    """Đọc dữ liệu từ file Excel và đổ vào Database SQLite để chuyển đổi nhanh"""
    # Nếu là chuỗi (đường dẫn), kiểm tra sự tồn tại. Nếu là File object (Streamlit), bỏ qua check này.
    if isinstance(excel_file, str) and not os.path.exists(excel_file):
        return False, f"Không tìm thấy file {excel_file} để import!"

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Để đảm bảo Schema mới nhất, ta Drop và Recreate các bảng cache trước khi import
        cursor.execute("DROP TABLE IF EXISTS standard_products")
        cursor.execute("DROP TABLE IF EXISTS gm_targets")
        cursor.execute("DROP TABLE IF EXISTS price_gaps")
        cursor.execute("DROP TABLE IF EXISTS baseline_costs")
        conn.commit()
        
        # Khởi tạo lại schema
        init_db()

        # 1. Standard Product
        df_std = pd.read_excel(excel_file, sheet_name='Standard Product', keep_default_na=False, na_filter=False)
        df_std.columns = df_std.columns.str.strip()
        df_std = df_std.rename(columns={
            'Category': 'category', 'Type': 'type', 'Materials Name': 'material_name',
            'Materials Code': 'material_code', 'Note': 'note', 'Buffer': 'buffer'
        })
        if 'material_code' in df_std.columns:
            df_std['material_code'] = df_std['material_code'].astype(str).str.strip().str[:7]
            df_std = df_std.drop_duplicates(subset=['material_code'], keep='last')
        df_std.to_sql('standard_products', conn, if_exists='replace', index=False)
        
        # 2. GM Target
        df_gm = pd.read_excel(excel_file, sheet_name='GM Target', keep_default_na=False, na_filter=False)
        df_gm.columns = df_gm.columns.str.strip()
        df_gm = df_gm.rename(columns={
            'Category': 'category', 'Region': 'region', 'OHC': 'ohc', 'OPM': 'opm', 'GM': 'gm_target'
        })
        df_gm.to_sql('gm_targets', conn, if_exists='replace', index=False)

        # 3. Price Gap
        df_gap = pd.read_excel(excel_file, sheet_name='Price Gap', keep_default_na=False, na_filter=False)
        df_gap.columns = df_gap.columns.str.strip()
        df_gap = df_gap.rename(columns={
            'Category': 'category', 'Range': 'range_name', 'Gap': 'gap_ratio'
        })
        df_gap.to_sql('price_gaps', conn, if_exists='replace', index=False)

        # 4. Cost (Flexible sheet name matching)
        all_sheets = pd.ExcelFile(excel_file).sheet_names
        cost_sheet = next((s for s in all_sheets if s.lower().strip() in ['cost', 'costs', 'baseline cost', 'baseline costs']), 'Cost')
        
        df_cost = pd.read_excel(excel_file, sheet_name=cost_sheet, keep_default_na=False, na_filter=False)
        df_cost.columns = df_cost.columns.str.strip()
        df_cost = df_cost.rename(columns={
            'Material Code': 'material_code', 'material code': 'material_code', 'Material code': 'material_code',
            'Region': 'region', 'region': 'region', 'Reg': 'region', 'reg': 'region',
            'Material Description': 'material_description', 
            '26.1Q Cost': 'q26_1_cost',
            '26.2Q Cost': 'q26_2_cost',
            '26.2Q Cost Unified': 'cost',
            'Final Cost': 'cost'
        })
        
        # Strip string columns to ensure clean matching
        for col in ['material_code', 'region']:
            if col in df_cost.columns:
                df_cost[col] = df_cost[col].astype(str).str.strip()
                
        if 'material_code' in df_cost.columns:
            df_cost['material_code'] = df_cost['material_code'].str[:7]
            
            # Determine available columns for duplicate dropping
            subset_cols = ['material_code']
            if 'region' in df_cost.columns:
                subset_cols.append('region')
                
            df_cost = df_cost.drop_duplicates(subset=subset_cols, keep='last')
            
        # Final: Save to 'baseline_costs' to match calculation logic!
        df_cost.to_sql('baseline_costs', conn, if_exists='replace', index=False)

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

# ==========================================
# CÁC HÀM LỊCH SỬ GIÁ (HISTORICAL DATA)
# ==========================================

def import_guide_price_history(excel_file, division):
    """Nạp dữ liệu lịch sử giá từ Excel vào bảng guide_price_historical."""
    quarters = ['25.1Q', '25.2Q', '25.3Q', '25.4Q', '26.1Q']
    try:
        conn = get_connection()
        xl = pd.ExcelFile(excel_file)
        
        # Chỉ lấy các Sheet khớp với Quý yêu cầu
        found_sheets = [s for s in xl.sheet_names if any(q in s for q in quarters)]
        total_rows = 0
        
        for sheet in found_sheets:
            df = pd.read_excel(xl, sheet_name=sheet, keep_default_na=False, na_filter=False)
            df.columns = df.columns.str.strip()
            
            # 1. Tìm cột Mã vật tư (Aliases)
            alt_mat_cols = ['Material Code', 'Material code', 'material_code', 'Mat 7D', 'Mat 18D', 'ITEM CODE', 'PART NUMBER']
            mat_col = next((c for c in df.columns if c in alt_mat_cols), None)
            
            # 2. Tìm cột Khu vực (Aliases)
            alt_reg_cols = ['Region', 'region', 'Reg', 'reg', 'REG']
            reg_col = next((c for c in df.columns if c in alt_reg_cols), None)
            
            if not mat_col:
                continue
                
            for _, row in df.iterrows():
                mat_val = str(row[mat_col]).strip()[:7] if mat_col else "Unknown"
                reg_val = str(row[reg_col]).strip() if reg_col else "Unknown"
                
                # Chuyển đổi toàn bộ Row sang Dict rồi dump thành JSON
                row_dict = row.to_dict()
                pricing_json = json.dumps(row_dict, ensure_ascii=False)
                
                conn.execute('''
                    INSERT OR REPLACE INTO guide_price_historical (material_code, region, division, quarter, pricing_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (mat_val, reg_val, division, sheet, pricing_json))
                total_rows += 1
        
        conn.commit()
        conn.close()
        return True, f"✅ Đã nạp {total_rows} dòng lịch sử cho Division {division} từ {len(found_sheets)} quý."
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"❌ Lỗi nạp lịch sử ({division}): {e}"

def search_guide_price_history(material_code):
    """Tìm kiếm lịch sử giá của một mã vật tư qua các quý và Division."""
    try:
        conn = get_connection()
        search_code = str(material_code).strip()[:7]
        query = "SELECT division, quarter, region, pricing_data FROM guide_price_historical WHERE material_code = ? ORDER BY quarter DESC"
        df = pd.read_sql_query(query, conn, params=(search_code,))
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
            
        history_list = []
        for _, row in df.iterrows():
            item = json.loads(row['pricing_data'])
            # Đảm bảo các cột chính luôn hiển thị ở đầu
            fixed_data = {
                'Division': row['division'],
                'Quarter': row['quarter'],
                'Region': row['region']
            }
            # Gộp với dữ liệu JSON, ưu tiên các cột chính
            fixed_data.update(item)
            history_list.append(fixed_data)
            
        return pd.DataFrame(history_list)
    except Exception as e:
        print(f"Error searching history: {e}")
        return pd.DataFrame()

def get_gm_target(category, region):
    """Lấy mục tiêu lợi nhuận gộp từ Database."""
    conn = get_connection()
    query = "SELECT gm_target FROM gm_targets WHERE category = ? AND region = ?"
    cursor = conn.cursor()
    cursor.execute(query, (category, region))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def get_price_gaps(category):
    """Lấy danh sách Gap của từng Category."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT range_name, gap_ratio FROM price_gaps WHERE category = ?", (category,))
    rows = cursor.fetchall()
    conn.close()
    
    gaps = {}
    for r in rows:
        gaps[r[0]] = float(r[1])
    return gaps

def calculate_full_pricing_suite(category, region, cost, yields=1.0, b1=None, b2=0.0):
    """
    Bộ não tính toán giá tập trung (Central Calculation Engine).
    Kết quả trả về dictionary chứa toàn bộ các mức giá GP, VP, GT, ST.
    1. GP_Base = ((1 + B1) * (Cost / Yield)) / (1 - GM)
    2. GP_Range_n = GP_Base * (1 + Gap_multiplier) * (1 + B2)
    """
    # 1. Lấy mục tiêu GM
    target_gm = get_gm_target(category, region)
    
    # 2. Lấy Buffer 1 từ DB (nếu không có sẵn)
    if b1 is None:
        conn = get_connection()
        prod_df = pd.read_sql_query("SELECT buffer FROM standard_products WHERE category = ?", conn, params=(category,))
        conn.close()
        b1 = float(prod_df['buffer'].iloc[0]) if not prod_df.empty else 0.0
        
    # 3. Tính giá GP Base
    gp_base = 0.0
    if 0 < target_gm < 1 and cost > 0 and yields > 0:
        gp_base = ((1 + b1) * (cost / yields)) / (1 - target_gm)
        
    # 4. Lấy danh sách Gap
    gaps = get_price_gaps(category)
    
    # 5. Tính toán các Range
    results = {
        "gp_base": gp_base,
        "target_gm": target_gm,
        "buffer_1": b1,
        "yields": yields
    }
    
    for i in range(1, 6):
        gap_val = gaps.get(f"Range {i}", 0.0)
        # Công thức: GP_n = GP_Base * (1 + Gap) * (1 + B2)
        gp_n = gp_base * (1 + gap_val) * (1 + b2)
        vp_n = gp_n * 0.95
        
        results[f"gp_r{i}"] = gp_n
        results[f"vp_r{i}"] = vp_n
        
        if i == 5:
            # GT/ST tính từ mức VP cao nhất (Range 5)
            gt = vp_n * 0.95
            st = gt * 0.95
            results["gt"] = gt
            results["st"] = st
            
    return results


def generate_request_id(division, region):
    """
    Tạo Request ID định dạng: Division-Region-YYYYMMDD-STT (Tự động reset mỗi ngày)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Lấy ngày hiện tại
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    
    # Đếm số yêu cầu đã tạo trong ngày hôm nay (tính từ 00:00:00)
    cursor.execute('''
        SELECT COUNT(*) FROM requests 
        WHERE date(created_at) = date('now')
    ''')
    count = cursor.fetchone()[0]
    conn.close()
    
    # Số thứ tự tiếp theo (định dạng 3 chữ số: 001, 002...)
    new_sequence = count + 1
    
    # Lắp ghép mã: HI-CN-20260328-001
    custom_id = f"{division}-{region}-{today_str}-{new_sequence:03d}"
    
    return custom_id

def log_action(username, action, details):
    """Ghi log hành vi hệ thống."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (username, action, details, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (username, action, details, datetime.datetime.now()))
    conn.commit()
    conn.close()

def request_account(name, employee_id, email, level, division):
    """Lưu yêu cầu cấp quyền từ trang đăng nhập"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO account_requests (name, employee_id, email, level, division, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'Pending', ?)
        ''', (name, employee_id, email, level, division, datetime.datetime.now()))
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