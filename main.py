import streamlit as st
import auth

# Page configuration (must be the first Streamlit call)
st.set_page_config(page_title="Price Calculator App", page_icon="🧮", layout="wide")

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
                submit_login = st.form_submit_button("Login", use_container_width=True)
                
                if submit_login:
                    if auth.login(username, password):
                        st.success(f"Logged in successfully as {username}!")
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
                submit_req = st.form_submit_button("Submit Request", use_container_width=True)
                
                if submit_req:
                    if req_name and req_id and req_email:
                        import database as db
                        success, message = db.request_account(req_name, req_id, req_email)
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
            auth.logout()
            st.rerun()

def main():
    # Initialize login state
    auth.init_session_state()
    
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

if __name__ == "__main__":
    main()
