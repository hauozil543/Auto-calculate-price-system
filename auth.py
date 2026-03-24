import streamlit as st
import database as db

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None

def login(username, password):
    conn = db.get_connection()
    cursor = conn.cursor()
    # Mật khẩu demo đang để plaintext dựa trên init_db()
    cursor.execute("SELECT role FROM users WHERE username = ? AND password_hash = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = user[0]
        db.log_action(username, "Login", "User logged in successfully")
        return True
    return False

def logout():
    if st.session_state.username:
        db.log_action(st.session_state.username, "Logout", "User logged out")
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
