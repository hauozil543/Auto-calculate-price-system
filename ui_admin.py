import streamlit as st
import pandas as pd
import database as db

def render():
    st.header("Admin Area: User and Log Management")
    
    active_tab = st.radio("Menu", ["Users Management", "Account Requests", "System Logs"], horizontal=True, label_visibility="collapsed", key="admin_main_nav")
    
    if active_tab == "Users Management":
        st.subheader("System Users Roster")
        conn = db.get_connection()
        df_users = pd.read_sql_query("SELECT id, username, role, level, region, division FROM users", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)
        
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
                    cursor.execute("DELETE FROM users WHERE username = ?", (user_to_delete,))
                    cursor.execute("DELETE FROM account_requests WHERE employee_id = ?", (user_to_delete,))
                    conn.commit()
                    db.log_action(st.session_state.username, "Delete User", f"Deleted user {user_to_delete}")
                    st.toast(f"User '{user_to_delete}' deleted.")
                    st.rerun()

        st.subheader("Add New User")
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_level = st.selectbox("Level", ["Staff", "L team leader", "C team leader", "G team leader"])
            with col2:
                new_role = st.selectbox("Role", ["Admin", "Pricing", "Sales"])
                new_region = st.selectbox("Region", ["ALL", "CN", "EU", "IN", "JP", "KR", "NA", "NM"])
                new_division = st.selectbox("Division", ["HI", "LT", "AM", "IT"])
            
            col_b1, col_b2, col_b3 = st.columns([1, 1, 1])
            with col_b2:
                submit_user = st.form_submit_button("Create User", type="primary", use_container_width=True)
            
            if submit_user:
                if new_username.strip() and new_password.strip():
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (username, password_hash, role, level, region, division) VALUES (?, ?, ?, ?, ?, ?)", (new_username.strip(), new_password.strip(), new_role, new_level, new_region, new_division))
                        conn.commit()
                        db.log_action(st.session_state.username, "Create User", f"Created user {new_username} ({new_role})")
                        st.success(f"User '{new_username}' has been successfully created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create user. Ensure username is unique.")
                else:
                    st.warning("Please fill in both Username and Password.")
        conn.close()

    elif active_tab == "Account Requests":
        st.subheader("Pending Account Requests")
        conn = db.get_connection()
        df_reqs = pd.read_sql_query("SELECT id, name, employee_id, email, level, division, status, created_at FROM account_requests WHERE status = 'Pending'", conn)
        
        if df_reqs.empty:
            st.info("Currently, there are no pending requests.")
        else:
            def style_status(val):
                return 'color: #fd7e14; font-weight: bold;' if val == 'Pending' else 'color: #28a745; font-weight: bold;'
            st.dataframe(df_reqs.style.map(style_status, subset=['status']), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("Approve and Provision Account")
            req_id = st.selectbox("Select Request ID to Process", df_reqs['id'].tolist())
            req_info = df_reqs[df_reqs['id'] == req_id].iloc[0]
            
            with st.form("approve_req_form"):
                st.info(f"Request details: {req_info['name']} ({req_info['employee_id']}) | Requested Level: {req_info['level']}")
                col1, col2 = st.columns(2)
                with col1:
                    role_assign = st.selectbox("Assign Role", ["Sales", "Pricing", "Admin"])
                with col2:
                    region_assign = st.selectbox("Assign Region", ["ALL", "CN", "EU", "IN", "JP", "KR", "NA", "NM"])
                    level_assign = st.selectbox("Assign Level", ["Staff", "L team leader", "C team leader", "G team leader"])
                    
                divisions = ["HI", "LT", "AM", "IT"]
                division_assign = st.selectbox("Assign Division", divisions)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    approve_btn = st.form_submit_button("Approve Account", type="primary", use_container_width=True)
                with col_btn2:
                    reject_btn = st.form_submit_button("Reject and Delete Request", use_container_width=True)
                
                if reject_btn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM account_requests WHERE id = ?", (int(req_id),))
                    conn.commit()
                    st.toast(f"Request rejected and deleted.")
                    st.rerun()

                if approve_btn:
                    import random
                    import string
                    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    username = req_info['employee_id']
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (username, password_hash, role, level, region, division) VALUES (?, ?, ?, ?, ?, ?)", (username, temp_password, role_assign, level_assign, region_assign, division_assign))
                        cursor.execute("UPDATE account_requests SET status = 'Approved' WHERE id = ?", (int(req_id),))
                        conn.commit()
                        st.success(f"Request approved! User '{username}' created. Temp Password: {temp_password}")
                        try:
                            subject = "Account Created - Price Calculator App"
                            user_email_str = str(req_info['email']).strip()
                            user_name_str = str(req_info['name']).strip()
                            body = f"Congratulations {user_name_str}!\n\nYour account has been approved.\nUsername: {username}\nTemporary Password: {temp_password}\n\nPlease log in and change your password.\nLink: http://172.16.124.126:8501"
                            if db.send_email_notification(user_email_str, subject, body):
                                st.info(f"Approval notification sent to user {user_email_str} via local Outlook.")
                            else:
                                st.error(f"Failed to dispatch Outlook mail to {user_email_str}. See terminal errors.")
                        except Exception as e:
                            st.error(f"Mail Exception: {e}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        conn.close()
        
    elif active_tab == "System Logs":
        st.subheader("System Access and Action Logs")
        conn = db.get_connection()
        df_logs = pd.read_sql_query("SELECT id, username, action, details, timestamp FROM logs ORDER BY timestamp DESC LIMIT 100", conn)
        
        if df_logs.empty:
            st.info("No logs generated yet.")
        else:
            st.write("System logs (Latest 100 entries)")
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
            sel_log_ids = st.multiselect("Select Log IDs to Export:", options=df_logs['id'].tolist())
            df_exp = df_logs[df_logs['id'].isin(sel_log_ids)] if sel_log_ids else df_logs
            csv = df_exp.to_csv(index=False).encode('utf-8-sig')
            st.download_button("Export Logs to CSV", csv, "system_logs.csv", "text/csv")

        if st.button("Refresh Logs"):
            st.rerun()
        conn.close()
