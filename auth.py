import streamlit as st
import database as db

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'region' not in st.session_state:
        st.session_state.region = None
    if 'level' not in st.session_state:
        st.session_state.level = None

def login(username, password):
    conn = db.get_connection()
    cursor = conn.cursor()
    # Password is plaintext for demo purposes per init_db() logic
    cursor.execute("SELECT role, region, level FROM users WHERE username = ? AND password_hash = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = user[0]
        st.session_state.region = user[1] if user[1] else "ALL"
        st.session_state.level = user[2]
        db.log_action(username, "Login", "User logged in successfully")
        return True
    return False

def login_by_username(username):
    """Đăng nhập tự động bằng username (khi có Cookie)"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, region, level FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = user[0]
        st.session_state.region = user[1] if user[1] else "ALL"
        st.session_state.level = user[2]
        db.log_action(username, "Auto-Login", "User logged in via Cookie")
        return True
    return False

def logout():
    if st.session_state.username:
        db.log_action(st.session_state.username, "Logout", "User logged out")
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.region = None
    st.session_state.level = None
