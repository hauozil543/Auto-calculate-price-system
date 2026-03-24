import streamlit as st
import pandas as pd
import database as db

def render():
    st.header("Admin Area: User & Log Management 🛠️")
    
    tabs = st.tabs(["👥 Users Management", "📜 System Logs"])
    
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
                    cursor.execute("DELETE FROM users WHERE username = ?", (user_to_delete,))
                    conn.commit()
                    db.log_action(st.session_state.username, "Delete User", f"Deleted user {user_to_delete}")
                    st.toast(f"User '{user_to_delete}' deleted.", icon="✔️")
                    st.rerun()

        conn.close()
        
    with tabs[1]:
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
