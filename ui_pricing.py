import streamlit as st
import pandas as pd
import database as db
import datetime

def render():
    st.header("Pricing Team Dashboard 📊")
    
    tabs = st.tabs(["📨 Special Requests", "⚙️ Database Monitor"])
    
    with tabs[0]:
        st.subheader("Actionable Sales Requests")
        st.info("Process pending quotation requests and missing cost queries to finalize Base Prices for Sales.")
        
        conn = db.get_connection()
        df_req = pd.read_sql_query("SELECT id, sales_username, material_code, request_type, region, status, actual_yield, final_price, created_at FROM requests ORDER BY created_at DESC", conn)
        
        if df_req.empty:
            st.write("No requests pending.")
        else:
            st.write("### All Requests Log Tracker")
            st.dataframe(df_req, use_container_width=True, hide_index=True)
            
            df_pending = df_req[df_req['status'].str.contains('Pending')]
            
            if not df_pending.empty:
                st.markdown("---")
                st.subheader("Process a Pending Ticket")
                
                req_id = st.selectbox("Select Request ID", df_pending['id'].tolist())
                req_row = df_pending[df_pending['id'] == req_id].iloc[0]
                
                req_type = req_row['request_type']
                req_status = req_row['status']
                mat_code = req_row['material_code']
                reg_val = req_row['region']
                sales_user = req_row['sales_username']
                
                st.write(f"**Target:** `{mat_code}` | **Type:** `{req_type}` | **Region:** `{reg_val}` | **Sales Rep:** `{sales_user}` | **Status:** `{req_status}`")
                
                with st.form("process_ticket_form"):
                    input_cost = None
                    input_yield = None
                    
                    if "Cost" in req_status:
                        input_cost = st.number_input("Input Base Cost ($)", min_value=0.0001, format="%.4f", value=10.0000)
                    else:
                        c_df = pd.read_sql_query("SELECT cost_unified FROM costs WHERE material_code = ?", conn, params=(mat_code[:7],))
                        if not c_df.empty:
                            st.info(f"Existing Base Cost in Database: **${c_df['cost_unified'].iloc[0]:.4f}**")
                        
                    if "Yield" in req_status or req_type == "Single Bin":
                        input_yield = st.number_input("Input Production Yield (%)", min_value=0.1, max_value=100.0, value=85.0, step=0.1)
                        
                    submit_process = st.form_submit_button("Submit & Calculate Final Guide Price", type="primary")
                    
                    if submit_process:
                        final_cost = input_cost
                        if final_cost is None:
                            c_df = pd.read_sql_query("SELECT cost_unified FROM costs WHERE material_code = ?", conn, params=(mat_code[:7],))
                            final_cost = c_df['cost_unified'].iloc[0] if not c_df.empty else 0.0
                            
                        prod_df = pd.read_sql_query("SELECT category FROM standard_products WHERE material_code = ?", conn, params=(mat_code[:7],))
                        cat_val = prod_df['category'].iloc[0] if not prod_df.empty else ""
                        target_gm = db.get_gm_target(cat_val, reg_val)
                        
                        calc_price = 0.0
                        if target_gm > 0 and target_gm < 1 and final_cost > 0:
                            if req_type == "Single Bin" and input_yield:
                                # Formula approved by user: (Cost / Yield) / (1 - Target GM)
                                calc_price = (final_cost / (input_yield / 100.0)) / (1 - target_gm)
                            else:
                                # Standard Bin Formula: Cost / (1 - Target GM)
                                calc_price = final_cost / (1 - target_gm)
                                
                        try:
                            cursor = conn.cursor()
                            # Update requests table
                            cursor.execute('''
                                UPDATE requests
                                SET status = 'Completed', base_price = ?, actual_yield = ?, final_price = ?, updated_at = ?
                                WHERE id = ?
                            ''', (final_cost, input_yield if input_yield else 0.0, calc_price, datetime.datetime.now(), int(req_id)))
                            
                            # If pricing input a new cost, update the main costs cache so future requests don't fail!
                            if input_cost is not None:
                                cursor.execute("SELECT 1 FROM costs WHERE material_code = ?", (mat_code[:7],))
                                if cursor.fetchone():
                                    cursor.execute("UPDATE costs SET cost_unified = ? WHERE material_code = ?", (input_cost, mat_code[:7]))
                                else:
                                    cursor.execute("INSERT INTO costs (material_code, cost_unified) VALUES (?, ?)", (mat_code[:7], input_cost))
                            
                            conn.commit()
                            
                            # Log action (Pricing processes the request) MUST BE AFTER COMMIT to prevent SQLite 'database is locked'
                            db.log_action("System/Pricing", "Process Request", f"{st.session_state.username} processed Request #{req_id} for {sales_user}. Final Price: ${calc_price:.4f}")
                            st.success(f"Request #{req_id} perfectly processed & successfully routed back to Sales! Final Calculated Price: ${calc_price:.4f}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating request: {e}")
                            
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
