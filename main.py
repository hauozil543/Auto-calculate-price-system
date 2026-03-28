import streamlit as st
import auth

# ==========================================
# 🎨 CENTRAL THEME CONFIGURATION (CHỈ CẦN SỬA Ở ĐÂY)
# ==========================================
APP_THEME_COLOR = "#0df27e"  # Màu chính cho nút bấm, tab, hover...
APP_BG_COLOR = "#dafdf4"     # Màu nền cho toàn bộ ứng dụng
# ==========================================

# Page configuration (must be the first Streamlit call)
st.set_page_config(page_title="Price Calculator App", page_icon="", layout="wide")

# Global Theme Injection (Apply across and override secondary elements)
st.markdown(f"""
    <style>
        /* 1. TOTAL ENFORCEMENT FOR ALL PRIMARY BUTTONS (Xóa sạch màu đỏ) */
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
        
        /* 2. ALL TABS - Text & Underline */
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
        
        /* 3. GLOBAL BACKGROUND (Màu nền toàn tập) */
        [data-testid="stAppViewContainer"] {{
            background-color: {APP_BG_COLOR} !important;
        }}
        
        /* 4. HYPERLINKS & TEXT HOVER (Di chuột vào chữ đổi màu) */
        button[data-testid*="toggle_login_state"]:hover, 
        button[key*="back_to_login"]:hover,
        div.stButton > button:not([kind="primary"]):hover,
        a:hover {{
            color: {APP_THEME_COLOR} !important;
            text-decoration: underline !important;
            background-color: transparent !important;
        }}
        
        /* Tinh chỉnh các input focus */
        .stTextInput > div > div:focus-within {{
            border-color: {APP_THEME_COLOR} !important;
            box-shadow: 0 0 0 1px {APP_THEME_COLOR} !important;
        }}
    </style>
""", unsafe_allow_html=True)

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

def render_sidebar():
    with st.sidebar:
        st.title(f"Hello, {st.session_state.username} 👋")
        st.caption(f"Role: **{st.session_state.role}**")
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            delete_cookie_js('remember_token')
            st.query_params.clear()
            auth.logout()
            st.rerun()

def main():
    auth.init_session_state()
    
    if not st.session_state.logged_in and not st.session_state.get('just_logged_out'):
        q_user = st.query_params.get("u")
        if q_user:
            if auth.login_by_username(q_user):
                st.rerun()

    if not st.session_state.logged_in and not st.session_state.get('just_logged_out'):
        token = st.context.cookies.get('remember_token')
        if token:
            if auth.login_by_username(token):
                st.query_params["u"] = token
                st.rerun()

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
        else:
            st.error("Error: Role permission not recognized!")
            
    import ui_footer
    ui_footer.render()

if __name__ == "__main__":
    main()

