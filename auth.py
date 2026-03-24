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

def login(username, password):
    conn = db.get_connection()
    cursor = conn.cursor()
    # Password is plaintext for demo purposes per init_db() logic
    cursor.execute("SELECT role, region FROM users WHERE username = ? AND password_hash = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = user[0]
        st.session_state.region = user[1] if user[1] else "ALL"
        db.log_action(username, "Login", "User logged in successfully")
        return True
    return False

def logout():
    if st.session_state.username:
        db.log_action(st.session_state.username, "Logout", "User logged out")
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.region = None
