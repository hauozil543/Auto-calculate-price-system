import streamlit as st
import pandas as pd
import database as db
import datetime

def render():
    st.header("Sales Pricing Tool 💰")
    
    tabs = st.tabs(["Calculator", "My Requests"])
    
    with tabs[0]:
        st.subheader("Guide Price Calculation")
        
        calc_tabs = st.tabs(["Standard Bin", "Selected Bin"])
        
        with calc_tabs[0]:
            st.write("Add rows to calculate Guide Price for multiple products at once.")
            
            if "row_count" not in st.session_state:
                st.session_state.row_count = 1
                
            col_add, col_sub, col_empty = st.columns([1, 1, 6])
            with col_add:
                if st.button("➕ Add Row"):
                    st.session_state.row_count += 1
            with col_sub:
                if st.button("➖ Remove Row"):
                    if st.session_state.row_count > 1:
                        st.session_state.row_count -= 1
            
            with st.form("multi_calc_form"):
                rows_data = []
                cols = st.columns(9)
                headers = ["Mat 7D", "Mat 18D", "Name", "Region", "Category", "Qty", "Incoterm", "Shipping", "Target Price"]
                
                # Render table headers using markdown
                for i, h in enumerate(headers):
                    cols[i].markdown(f"<span style='font-size:13px'><b>{h}</b></span>", unsafe_allow_html=True)
                
                for i in range(st.session_state.row_count):
                    cols = st.columns(9)
                    mat_7d = cols[0].text_input(f"7D_{i}", label_visibility="collapsed")
                    mat_18d = cols[1].text_input(f"18D_{i}", label_visibility="collapsed")
                    mat_name = cols[2].text_input(f"Name_{i}", label_visibility="collapsed")
                    
                    user_reg = st.session_state.get('region', 'ALL')
                    allowed_regions = ["CN", "EU", "IN", "JP", "KR", "NA", "NM", "US"] if user_reg == 'ALL' else [user_reg]
                    region = cols[3].selectbox(f"Reg_{i}", allowed_regions, label_visibility="collapsed")
                    
                    cat = cols[4].text_input(f"Cat_{i}", label_visibility="collapsed")
                    qty = cols[5].text_input(f"Qty_{i}", label_visibility="collapsed")
                    incoterm = cols[6].text_input(f"Inco_{i}", label_visibility="collapsed")
                    shipping = cols[7].text_input(f"Ship_{i}", label_visibility="collapsed")
                    target = cols[8].text_input(f"Tgt_{i}", label_visibility="collapsed")
                    
                    rows_data.append({
                        "Material code (7D)": mat_7d,
                        "Material code (18D)": mat_18d,
                        "Material Name": mat_name,
                        "Region": region,
                        "Category": cat,
                        "Quantity": qty,
                        "Incoterm": incoterm,
                        "Shipping fee": shipping,
                        "Target Price (USD)": target
                    })
                    
                submit_calc = st.form_submit_button("Calculate All Guide Prices", type="primary")
                
                if submit_calc:
                    results = []
                    has_error = False
                    conn = db.get_connection()
                    for idx, r in enumerate(rows_data):
                        mat7d_val = r["Material code (7D)"].strip()
                        mat18d_val = r["Material code (18D)"].strip()
                        reg_val = r["Region"].strip()
                        
                        if not mat7d_val or not mat18d_val or not reg_val:
                            st.error(f"Row {idx + 1}: Missing mandatory fields! (Code 7D, Code 18D, and Region are required).")
                            has_error = True
                            continue

                        cat_val = r["Category"].strip()
                        reg_val = r["Region"].strip()
                        mat7d_val = r["Material code (7D)"].strip()
                        
                        guide_price = "N/A"
                        if cat_val and reg_val and mat7d_val:
                            target_gm = db.get_gm_target(cat_val, reg_val)
                            cost_df = db.get_cost(mat7d_val)
                            base_cost = cost_df['cost_unified'].iloc[0] if not cost_df.empty else 0.0
                            
                            if target_gm > 0 and target_gm < 1 and base_cost > 0:
                                gp_val = base_cost / (1 - target_gm)
                                guide_price = f"${gp_val:.4f}"
                            elif base_cost <= 0:
                                guide_price = "No Cost Data"
                            else:
                                guide_price = "No GM Target"
                                
                        r["Guide Price"] = guide_price
                        results.append(r)
                    conn.close()
                    
                    if not has_error:
                        st.success("Batch Calculation Complete!")
                        st.dataframe(pd.DataFrame(results), use_container_width=True)

        with calc_tabs[1]:
            st.info("Selected Bin Pricing requires a customized cost request based on actual yield and constraints.")
            
            conn = db.get_connection()
            df_products = pd.read_sql_query("SELECT material_code, material_name, category FROM standard_products", conn)
            conn.close()
            
            if not df_products.empty:
                selected_code_sel = st.selectbox(
                    "Select Product (Material Code)", 
                    df_products['material_code'].tolist(),
                    format_func=lambda x: f"{x} - {df_products[df_products['material_code'] == x]['material_name'].iloc[0]}",
                    key="sel_bin_select"
                )
                
                with st.form("calc_form_sel"):
                    st.write("Submit a request to the Pricing Team for a Selected Bin quotation.")
                    yield_val = st.number_input("Expected Yield (%)", min_value=0.0, max_value=100.0, value=85.0, step=0.1)
                    submit_req = st.form_submit_button("Send Pricing Request", type="primary", use_container_width=True)
                    
                    if submit_req:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute('''
                                INSERT INTO requests (sales_username, material_code, request_type, status, actual_yield, created_at, updated_at)
                                VALUES (?, ?, 'Selected Bin', 'Pending Cost', ?, ?, ?)
                            ''', (st.session_state.username, selected_code_sel, yield_val, datetime.datetime.now(), datetime.datetime.now()))
                            conn.commit()
                            st.success(f"Pricing request for '{selected_code_sel}' (Selected Bin) successfully routed to the Pricing Team.")
                        except Exception as e:
                            st.error(f"Failed to submit request: {e}")
                        finally:
                            conn.close()

    with tabs[1]:
        st.subheader("My Request History")
        conn = db.get_connection()
        df_my_reqs = pd.read_sql_query("SELECT id, material_code, request_type, status, actual_yield, base_price, created_at FROM requests WHERE sales_username = ?", conn, params=(st.session_state.username,))
        conn.close()
        
        if df_my_reqs.empty:
            st.info("Historical requests for Cost / Yield Updates sent to the Pricing team will appear here.")
        else:
            st.dataframe(df_my_reqs, use_container_width=True, hide_index=True)
