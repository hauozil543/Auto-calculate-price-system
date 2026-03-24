import streamlit as st
import auth

# Cấu hình trang (phải là lệnh gọi đầu tiên của Streamlit)
st.set_page_config(page_title="Price Calculator App", page_icon="🧮", layout="wide")

def login_screen():
    st.title("🧮 Welcome to Price Calculator App")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Login to your account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if auth.login(username, password):
                    st.success(f"Logged in successfully as {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")
        
        st.info("**Demo Accounts:**\n- Admin: `admin` / `admin123`\n- Pricing: `pricing_demo` / `123456`\n- Sales: `sales_demo` / `123456`")

def render_sidebar():
    with st.sidebar:
        st.title(f"Hello, {st.session_state.username} 👋")
        st.caption(f"Role: **{st.session_state.role}**")
        st.divider()
        
        # Các options chung sẽ nằm ở đây
        
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()

def main():
    # Khởi tạo trạng thái đăng nhập
    auth.init_session_state()
    
    if not st.session_state.logged_in:
        login_screen()
    else:
        # Load thanh điều hướng bên trái
        render_sidebar()
        
        # Render các Module UI tùy theo quyền (Role-based)
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
            st.error("Lỗi: Không nhận diện được Role phân quyền này!")

if __name__ == "__main__":
    main()
