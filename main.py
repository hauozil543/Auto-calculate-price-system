import streamlit as st
import auth

APP_THEME_COLOR = "#2E7D32" # Professional Forest Green
APP_BG_COLOR = "#F8FAF9"     # Very light sage-grey background

st.set_page_config(page_title="Price Calculator Hub", page_icon="📈", layout="wide")

# Inject Google Material Icons and Premium CSS
st.markdown(f"""
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        /* Global Background */
        [data-testid="stAppViewContainer"] {{
            background-color: {APP_BG_COLOR} !important;
        }}
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {{
            background-color: #ffffff !important;
            border-right: 1px solid #e0e0e0;
        }}
        
        /* Card Styling */
        .st-emotion-cache-12w0qpk {{
            padding: 0 !important;
        }}
        
        .premium-card {{
            background-color: #ffffff;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            margin-bottom: 20px;
        }}
        
        /* Button Styling - Bo góc & Modern Green */
        button[kind="primary"], 
        button[data-testid="stBaseButton-primary"],
        div.stButton button:first-child[data-testid*="primary"] {{ 
            background-color: {APP_THEME_COLOR} !important;
            border-radius: 8px !important;
            padding: 0.5rem 2rem !important;
            border: none !important;
            transition: all 0.3s ease !important;
        }}
        
        button[kind="primary"]:hover {{
            box-shadow: 0 4px 12px rgba(46,125,50,0.3) !important;
            transform: translateY(-1px);
        }}
        
        /* Navigation & Tabs */
        [data-testid="stTabs"] button[aria-selected="true"] {{
            color: {APP_THEME_COLOR} !important;
            border-bottom: 3px solid {APP_THEME_COLOR} !important;
        }}
        
        /* Inputs */
        .stTextInput > div > div:focus-within {{
            border-color: {APP_THEME_COLOR} !important;
            box-shadow: 0 0 0 1px {APP_THEME_COLOR} !important;
        }}
    </style>
""", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        user_initial = st.session_state.username[0].upper() if st.session_state.username else "?"
        role_label = st.session_state.role
        region_label = st.session_state.get('region', 'N/A')
        
        # Profile Card HTML
        st.markdown(f"""
            <div style="background-color: #f1f8f3; padding: 20px; border-radius: 12px; border: 1px solid #c8e6c9; margin-bottom: 25px;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="background-color: {APP_THEME_COLOR}; color: white; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        {user_initial}
                    </div>
                    <div>
                        <div style="font-weight: 700; color: #1b5e20; font-size: 16px;">{st.session_state.username}</div>
                        <div style="font-size: 12px; color: #4caf50; font-weight: 600;">{role_label} • {region_label}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        if st.button("Sign Out", use_container_width=True, icon="🚪"):
            auth.logout()
            st.session_state.delete_cookie = True
            st.rerun()

def main():
    is_deleting = st.session_state.get("delete_cookie", False)
    if is_deleting:
        import streamlit.components.v1 as components
        components.html("""
            <script>
                document.cookie = "remember_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            </script>
        """, height=0)
        st.session_state.delete_cookie = False

    if st.session_state.get("set_cookie", False):
        import streamlit.components.v1 as components
        u = st.session_state.cookie_u
        components.html(f"""
            <script>
                var d = new Date(); d.setTime(d.getTime() + (30*24*60*60*1000));
                document.cookie = "remember_token={u}; expires=" + d.toUTCString() + "; path=/;";
            </script>
        """, height=0)
        st.session_state.set_cookie = False

    auth.init_session_state()
    
    if not st.session_state.logged_in and not st.session_state.get('just_logged_out', False) and not is_deleting:
        try:
            token = st.context.cookies.get("remember_token")
            if token:
                auth.login_by_username(token)
        except Exception:
            pass

    if not st.session_state.logged_in:
        import ui_login
        ui_login.render_login()
    else:
        render_sidebar()
        if st.session_state.role == "Admin":
            import ui_admin
            ui_admin.render()
        elif st.session_state.role == "Pricing":
            import ui_pricing
            ui_pricing.render()
        elif st.session_state.role == "Sales":
            import ui_sales
            ui_sales.render()
    
    try:
        import ui_footer
        ui_footer.render()
    except: pass

if __name__ == "__main__":
    main()
