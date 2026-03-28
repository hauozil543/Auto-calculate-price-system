import streamlit as st
import auth
import database as db

def render_login():
    # Initialize state for view toggle
    if 'login_view' not in st.session_state:
        st.session_state.login_view = 'signin'

    # Custom CSS for modern aesthetics
    st.markdown("""
        <style>
            [data-testid="stAppViewContainer"] {
                background-color: #dafdf4 !important;
            }
            [data-testid="stHeader"], [data-testid="stFooter"] {visibility: hidden;}
            
            .social-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f0f2f6;
                color: #555;
                font-weight: bold;
                font-size: 14px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }
            
            .login-title {
                font-size: 36px;
                font-weight: 800;
                color: #262730;
                margin-bottom: 30px;
                letter-spacing: -0.5px;
            }

            .stTextInput > div > div > input {
                background-color: #f8f9fa !important;
                border: 1px solid #e9ecef !important;
                padding: 12px !important;
                border-radius: 8px !important;
            }

            /* FORCE REMOVE ALL BOX STYLING FROM THE TOGGLE BUTTON */
            div.stButton > button {
                transition: all 0.2s;
            }
            
            /* Target ONLY the link-style button */
            div.stButton > button:not([data-testid="stBaseButton-primary"]) {
                background-color: transparent !important;
                border: none !important;
                color: #555 !important;
                padding: 0 !important;
                font-weight: 500 !important;
                text-decoration: underline !important;
                box-shadow: none !important;
                font-size: 14px !important;
                display: block !important;
                margin: 0 !important;
                text-align: left !important;
                height: auto !important;
                min-height: auto !important;
            }
            
            div.stButton > button:not([data-testid="stBaseButton-primary"]):hover {
                color: #0df27e !important;
                background-color: transparent !important;
                border: none !important;
                text-decoration: none !important;
            }
            
            div.stButton > button:not([data-testid="stBaseButton-primary"]):active,
            div.stButton > button:not([data-testid="stBaseButton-primary"]):focus {
                background-color: transparent !important;
                border: none !important;
                color: #0df27e !important;
                box-shadow: none !important;
            }

            /* Adjust spacing for the link under the checkbox */
            .link-container {
                margin-top: -15px;
                margin-bottom: 20px;
                padding-left: 2px;
            }

            /* PRIMARY BUTTON COLOR OVERRIDE */
            button[data-testid="stBaseButton-primary"] {
                background-color: #0df27e !important;
                border-color: #0df27e !important;
                color: white !important;
            }
            button[data-testid="stBaseButton-primary"]:hover {
                background-color: #079971 !important;
                border-color: #079971 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
    
    col_l, col_main, col_r = st.columns([1, 8, 1])
    
    with col_main:
        left_side, right_side = st.columns([1.2, 1], gap="large")
        
        with left_side:
            st.markdown(f"<h1 class='login-title'>{'Signin' if st.session_state.login_view == 'signin' else 'Request Account'}</h1>", unsafe_allow_html=True)
            
            if st.session_state.login_view == 'signin':
                u = st.text_input("Username", placeholder="sales_demo")
                p = st.text_input("Password", type="password", placeholder="••••••••")
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                rem = st.checkbox("Remember me for 30 days")
                
                # Link Container to precisely position the text link
                st.markdown('<div class="link-container">', unsafe_allow_html=True)
                target_view = 'signup' if st.session_state.login_view == 'signin' else 'signin'
                btn_txt = "No account yet? Signup." if st.session_state.login_view == 'signin' else "Already have an account? Signin."
                
                if st.button(btn_txt, key="toggle_login_state"):
                    st.session_state.login_view = target_view
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                if st.button("Signin", use_container_width=True, type="primary"):
                    if auth.login(u, p):
                        st.success("Access Granted. Redirecting...")
                        st.rerun()
                    else:
                        st.error("Authentication failed. Please check your credentials.")
                
                
                
            else:
                rn = st.text_input("Full Name")
                ri = st.text_input("Employee ID / Username")
                re = st.text_input("Outlook Email")
                rl = st.selectbox("Tier", ["Staff", "Team Leader", "Manager", "Director"])
                div = st.selectbox("Division", ["HI", "LT", "AM", "IT"])
                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                
                if st.button("Submit Request", use_container_width=True, type="primary"):
                    if rn and ri and re:
                        success, msg = db.request_account(rn, ri, re, rl, div)
                        if success: st.success("Request logged! Please check your Outlook for approval.")
                        else: st.error(msg)
                
                # Back button as simple text too
                if st.button("Back to Login", key="back_to_login"):
                    st.session_state.login_view = 'signin'
                    st.rerun()

        with right_side:
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #09bc8a 0%, #0077b6 100%); 
                            padding: 60px 40px; border-radius: 20px; color: white; height: 550px; 
                            display: flex; flex-direction: column; justify-content: center; align-items: center; 
                            text-align: center; box-shadow: 0 15px 35px rgba(9,188,138,0.2);">
                    <h2 style="color: white !important; font-size: 32px; font-weight: 700; margin-bottom: 20px;">Welcome back!</h2>
                    <p style="color: rgba(255,255,255,0.9) !important; font-size: 16px; line-height: 1.6;">
                        NexusPrice: Advanced Sales Pricing & Intelligence System.<br><br>
                        Process pricing requests quickly, accurately and save time for everyone involved.
                    </p>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)

