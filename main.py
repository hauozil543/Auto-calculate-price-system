import streamlit as st
import auth

APP_THEME_COLOR = "#0df27e"
APP_BG_COLOR = "#dafdf4"

st.set_page_config(page_title="Price Calculator App", page_icon="", layout="wide")

st.markdown(f"""
    <style>
        button[kind="primary"], 
        button[data-testid="stBaseButton-primary"],
        div.stButton button:first-child[data-testid*="primary"] {{ 
            background-color: {APP_THEME_COLOR} !important;
            background-image: none !important;
            border-color: {APP_THEME_COLOR} !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }}
        
        button[kind="primary"]:hover, 
        button[data-testid="stBaseButton-primary"]:hover {{
            background-color: {APP_THEME_COLOR} !important;
            opacity: 0.9;
            border-color: {APP_THEME_COLOR} !important;
            box-shadow: 0 4px 12px rgba(13,242,126,0.3) !important;
        }}
        
        [data-testid="stTabs"] button[aria-selected="true"] p {{
            color: #1a1a1a !important;
            font-weight: 700 !important;
        }}
        [data-testid="stTabs"] button[aria-selected="true"] {{
            border-bottom: 3px solid {APP_THEME_COLOR} !important;
        }}
        [data-testid="stTabs"] button:hover p {{
            color: {APP_THEME_COLOR} !important;
        }}
        
        [data-testid="stAppViewContainer"] {{
            background-color: {APP_BG_COLOR} !important;
        }}
        
        button[data-testid*="toggle_login_state"]:hover, 
        button[key*="back_to_login"]:hover,
        div.stButton > button:not([kind="primary"]):hover,
        a:hover {{
            color: {APP_THEME_COLOR} !important;
            text-decoration: underline !important;
            background-color: transparent !important;
        }}
        
        .stTextInput > div > div:focus-within {{
            border-color: {APP_THEME_COLOR} !important;
            box-shadow: 0 0 0 1px {APP_THEME_COLOR} !important;
        }}
    </style>
""", unsafe_allow_html=True)

import streamlit.components.v1 as components



def render_sidebar():
    with st.sidebar:
        st.title(f"Hello, {st.session_state.username}")
        st.caption(f"Role: {st.session_state.role}")
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.query_params.clear()
            auth.logout()
            # Set this AFTER auth.logout() because it clears session state
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
