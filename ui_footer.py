import streamlit as st

def render():
    """
    Renders a unified premium footer for the application.
    """
    st.markdown("---")
    
    footer_html = """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: #666;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #eee;
        z-index: 1000;
    }
    .footer-content {
        display: flex;
        justify-content: center;
        gap: 30px;
        opacity: 0.8;
    }
    .footer-item {
        display: flex;
        align-items: center;
        gap: 5px;
    }
    </style>
    <div class="footer-content">
        <div class="footer-item">
            <span>© Auto-reply sales price request system</span>
        </div>
        <div class="footer-item">
            <span>Performance Boost</span>
        </div>
        <div class="footer-item">
            <span>Secure System</span>
        </div>
        <div class="footer-item">
            <span>709432@seoulsemicon.com</span>
        </div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)
