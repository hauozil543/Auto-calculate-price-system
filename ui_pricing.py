import streamlit as st
import pandas as pd
import database as db

def render():
    st.header("Pricing Team Dashboard 📊")
    
    tabs = st.tabs(["📨 Special Requests", "⚙️ Database Monitor"])
    
    with tabs[0]:
        st.subheader("Pending Sales Requests")
        st.info("Pending quotation requests and manual cost adjustments from Sales will be displayed here for review.")
        conn = db.get_connection()
        df_req = pd.read_sql_query("SELECT * FROM requests ORDER BY created_at DESC", conn)
        if df_req.empty:
            st.write("No requests pending.")
        else:
            st.dataframe(df_req, use_container_width=True, hide_index=True)
        conn.close()
        
    with tabs[1]:
        st.subheader("Real-time Database Status")
        st.write("Quick monitor of the current database cache configuration (SQLite).")
        conn = db.get_connection()
        
        col1, col2, col3, col4 = st.columns(4)
        count_std = pd.read_sql_query("SELECT COUNT(*) FROM standard_products", conn).iloc[0,0]
        count_gm = pd.read_sql_query("SELECT COUNT(*) FROM gm_targets", conn).iloc[0,0]
        count_gap = pd.read_sql_query("SELECT COUNT(*) FROM price_gaps", conn).iloc[0,0]
        count_cost = pd.read_sql_query("SELECT COUNT(*) FROM costs", conn).iloc[0,0]
        conn.close()
        
        col1.metric("Standard Products", count_std)
        col2.metric("GM Targets Rules", count_gm)
        col3.metric("Price Gap Rules", count_gap)
        col4.metric("Cost Records", count_cost)
        
        st.divider()
        st.warning("🔄 If the `GuidePriceAIRaw.xlsx` template is updated, the trigger for `import_excel_to_sqlite()` will be placed here.")
