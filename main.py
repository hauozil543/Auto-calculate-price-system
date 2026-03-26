import streamlit as st
import auth

# Page configuration (must be the first Streamlit call)
st.set_page_config(page_title="Price Calculator App", page_icon="🧮", layout="wide")

import streamlit.components.v1 as components

def set_cookie_js(name, value, days=30):
    """Sử dụng JavaScript để lưu Cookie vào trình duyệt."""
    expires = days * 24 * 60 * 60
    components.html(f"""
        <script>
            document.cookie = "{name}={value}; path=/; max-age={expires}";
        </script>
    """, height=0)

def delete_cookie_js(name):
    """Sử dụng JavaScript để xóa Cookie."""
    components.html(f"""
        <script>
            document.cookie = "{name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
        </script>
    """, height=0)

def login_screen():
    st.title("Welcome to Price Calculator App")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tabs = st.tabs(["🔐 Login", "📝 Request Account"])
        
        with tabs[0]:
            st.subheader("Login to your account")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                remember_me = st.checkbox("Ghi nhớ đăng nhập (30 ngày)")
                submit_login = st.form_submit_button("Login", use_container_width=True)
                
                if submit_login:
                    if auth.login(username, password):
                        st.success(f"Logged in successfully as {username}!")
                        if remember_me:
                            set_cookie_js('remember_token', username)
                            st.query_params["u"] = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")
            
            st.info("**Demo Accounts:**\n- Admin: `admin` / `admin123`\n- Pricing: `pricing_demo` / `123456`\n- Sales: `sales_demo` / `123456`")
            
        with tabs[1]:
            st.subheader("Request New Account")
            st.write("Don't have an account? Request one from Admin.")
            with st.form("request_account_form", clear_on_submit=True):
                req_name = st.text_input("Full Name")
                req_id = st.text_input("Employee ID / Username")
                req_email = st.text_input("Outlook Email")
                req_level = st.selectbox("Position/Level", ["Staff", "L team leader", "C team leader", "G team leader"])
                submit_req = st.form_submit_button("Submit Request", use_container_width=True)
                
                if submit_req:
                    if req_name and req_id and req_email:
                        import database as db
                        success, message = db.request_account(req_name, req_id, req_email, req_level)
                        if success:
                            st.success("Request sent! You will receive your password via Outlook email once approved.")
                        else:
                            st.error(message)
                    else:
                        st.warning("Please fill in all fields.")

def render_sidebar():
    with st.sidebar:
        st.title(f"Hello, {st.session_state.username} 👋")
        st.caption(f"Role: **{st.session_state.role}**")
        st.divider()
        
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            delete_cookie_js('remember_token')
            if "u" in st.query_params:
                del st.query_params["u"]
            auth.logout()
            st.rerun()

def main():
    # 1. Initialize session state
    auth.init_session_state()
    
    # 2. Check for Auto-Login (Query Params - fastest)
    if not st.session_state.logged_in:
        q_user = st.query_params.get("u")
        if q_user:
            if auth.login_by_username(q_user):
                st.rerun()

    # 3. Check for Auto-Login (Native Cookies)
    if not st.session_state.logged_in:
        # st.context.cookies is available in 1.55.0
        token = st.context.cookies.get('remember_token')
        if token:
            if auth.login_by_username(token):
                # Sync query param for easier F5 next time
                st.query_params["u"] = token
                st.rerun()

    # 4. Render UI
    if not st.session_state.logged_in:
        login_screen()
    else:
        # Load sidebar navigation
        render_sidebar()
        
        # Render Role-based UI modules
        if st.session_state.role == "Admin":
            import ui_admin
            ui_admin.render()
            
        elif st.session_state.role == "Pricing":
            import ui_pricing
            ui_pricing.render()
            
        elif st.session_state.role == "Sales":
            import ui_sales
            ui_sales.render()
            
        else:
            st.error("Error: Role permission not recognized!")
            
    # Always render footer at the bottom
    import ui_footer
    ui_footer.render()

if __name__ == "__main__":
    main()
