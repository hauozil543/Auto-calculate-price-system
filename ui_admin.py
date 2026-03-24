import streamlit as st
import pandas as pd
import database as db

def render():
    st.header("Admin Area: User & Log Management 🛠️")
    
    tabs = st.tabs(["👥 Users Management", "📝 Account Requests", "📜 System Logs"])
    
    with tabs[0]:
        st.subheader("System Users Roster")
        conn = db.get_connection()
        df_users = pd.read_sql_query("SELECT id, username, role, level, region FROM users", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Add New User")
        
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
            with col2:
                new_role = st.selectbox("Role", ["Admin", "Pricing", "Sales"])
                new_region = st.selectbox("Region", ["ALL", "CN", "EU", "IN", "JP", "KR", "US"])
            
            submit_user = st.form_submit_button("Create User")
            
            if submit_user:
                if new_username.strip() and new_password.strip():
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO users (username, password_hash, role, region) VALUES (?, ?, ?, ?)",
                            (new_username.strip(), new_password.strip(), new_role, new_region)
                        )
                        conn.commit()
                        db.log_action(st.session_state.username, "Create User", f"Created user {new_username} ({new_role})")
                        st.success(f"User '{new_username}' has been successfully created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create user. Ensure username is unique. (Error: {e})")
                else:
                    st.warning("Please fill in both Username and Password.")
                    
        st.markdown("---")
        st.subheader("Delete User")
        with st.form("delete_user_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                user_to_delete = st.selectbox("Select User to Delete", df_users['username'].tolist())
            with col2:
                st.write("")
                st.write("")
                delete_btn = st.form_submit_button("Delete User", type="primary")
            
            if delete_btn:
                if user_to_delete == st.session_state.username:
                    st.error("You cannot delete your own account while logged in!")
                elif user_to_delete == "admin":
                    st.error("Cannot delete the root 'admin' user.")
                else:
                    cursor = conn.cursor()
                    # Delete from users table
                    cursor.execute("DELETE FROM users WHERE username = ?", (user_to_delete,))
                    # Đồng thời xóa luôn request cũ (NẾU CÓ) dựa vào employee_id để giải phóng constraint cho phép đăng ký lại
                    cursor.execute("DELETE FROM account_requests WHERE employee_id = ?", (user_to_delete,))
                    
                    conn.commit()
                    db.log_action(st.session_state.username, "Delete User", f"Deleted user {user_to_delete}")
                    st.toast(f"User '{user_to_delete}' deleted.", icon="✔️")
                    st.rerun()

        conn.close()

    with tabs[1]:
        st.subheader("Pending Account Requests")
        conn = db.get_connection()
        df_reqs = pd.read_sql_query("SELECT id, name, employee_id, email, status, created_at FROM account_requests WHERE status = 'Pending'", conn)
        
        if df_reqs.empty:
            st.info("Currently, there are no pending requests.")
        else:
            st.dataframe(df_reqs, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("Approve & Provision Account")
            with st.form("approve_req_form"):
                col1, col2 = st.columns(2)
                with col1:
                    req_id = st.selectbox("Select Request ID", df_reqs['id'].tolist())
                    role_assign = st.selectbox("Assign Role", ["Sales", "Pricing", "Admin"])
                with col2:
                    region_assign = st.selectbox("Assign Region", ["ALL", "CN", "EU", "IN", "JP", "KR", "US"])
                    
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    approve_btn = st.form_submit_button("Approve & Send Outlook Email", type="primary", use_container_width=True)
                with col_btn2:
                    reject_btn = st.form_submit_button("Reject & Delete Request", use_container_width=True)
                
                if reject_btn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM account_requests WHERE id = ?", (int(req_id),))
                    conn.commit()
                    st.toast(f"Request #{req_id} rejected and deleted.", icon="🗑️")
                    st.rerun()

                if approve_btn:
                    req_info = df_reqs[df_reqs['id'] == req_id].iloc[0]
                    import random
                    import string
                    
                    # Tự động sinh password ngẫu nhiên 8 ký tự
                    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    username = req_info['employee_id']
                    
                    try:
                        cursor = conn.cursor()
                        # Thêm User vào hệ thống
                        cursor.execute("INSERT INTO users (username, password_hash, role, region) VALUES (?, ?, ?, ?)", (username, temp_password, role_assign, region_assign))
                        # Đổi Status
                        cursor.execute("UPDATE account_requests SET status = 'Approved' WHERE id = ?", (int(req_id),))
                        conn.commit()
                        db.log_action(st.session_state.username, "Account Approval", f"Approved {username} as {role_assign}")
                        
                        # Bắn mail từ cục Outlook nội bộ của Admin bằng win32com
                        import win32com.client as win32
                        try:
                            outlook = win32.Dispatch('outlook.application')
                            mail = outlook.CreateItem(0)
                            mail.To = req_info['email']
                            mail.Subject = "Your Price Calculator App Account is Ready!"
                            mail.Body = f"Hello {req_info['name']},\n\nYour account access request has been approved by the Admin.\n\n" \
                                        f"System Link: http://172.16.124.126:8501\n\n" \
                                        f"Username: {username}\n" \
                                        f"Temporary Password: {temp_password}\n" \
                                        f"Assigned Role: {role_assign}\n\n" \
                                        f"Please login to the system. Keep this information secure.\n\nRegards,\nAdmin Team"
                            mail.Send()
                            st.success(f"Request #{req_id} approved! User '{username}' created and Outlook email dispatched to {req_info['email']}.")
                        except Exception as outlook_e:
                            st.warning(f"User '{username}' created, but failed to send Outlook email. (Is Outlook currently running?). Error: {outlook_e}")
                            
                    except db.sqlite3.IntegrityError:
                        st.error("Error: This Username/Employee ID already exists in the system!")
                    except Exception as db_e:
                        st.error(f"Database error during approval: {db_e}")
        conn.close()
        
    with tabs[2]:
        st.subheader("System Access & Action Logs")
        conn = db.get_connection()
        df_logs = pd.read_sql_query("SELECT id, username, action, details, timestamp FROM logs ORDER BY timestamp DESC LIMIT 100", conn)
        
        if df_logs.empty:
            st.info("No logs generated yet.")
        else:
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
            
        if st.button("Refresh Logs"):
            st.rerun()
            
        conn.close()
