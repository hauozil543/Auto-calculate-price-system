import database as db
import pandas as pd

def test_rbac():
    # Test case 1: L team leader JP
    ctx_jp = {'role': 'Pricing', 'level': 'L team leader', 'username': 'salecheck', 'region': 'JP'}
    df_jp = db.get_released_report_details(1, ctx_jp)
    print(f"JP Leader results (unique regions): {df_jp['region'].unique() if not df_jp.empty else 'Empty'}")
    
    # Test case 2: Admin
    ctx_admin = {'role': 'Admin', 'level': None, 'username': 'admin', 'region': None}
    df_admin = db.get_released_report_details(1, ctx_admin)
    print(f"Admin results (unique regions): {df_admin['region'].unique() if not df_admin.empty else 'Empty'}")

if __name__ == "__main__":
    test_rbac()
