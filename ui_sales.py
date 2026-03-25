import streamlit as st
import pandas as pd
import database as db
import datetime

def render_grid(tab_type, tab_name):
    st.write(f"Add rows to submit multi-line **{tab_name}** pricing calculations.")
    
    state_key = f"row_ids_{tab_type}"
    next_key = f"next_id_{tab_type}"
    
    if state_key not in st.session_state:
        st.session_state[state_key] = [0]
        st.session_state[next_key] = 1
        
    def add_row(idx):
        st.session_state[state_key].insert(idx + 1, st.session_state[next_key])
        st.session_state[next_key] += 1
        
    def del_row(idx):
        if len(st.session_state[state_key]) > 1:
            st.session_state[state_key].pop(idx)
            
    with st.form(f"multi_calc_form_{tab_type}"):
        rows_data = []
        cols = st.columns([3, 3, 3, 2, 2, 1, 2, 2, 2, 1])
        headers = ["Mat 7D", "Mat 18D", "Name", "Reg", "Cat", "Qty", "Inco", "Ship", "Tgt Price", ""]
        
        for i, h in enumerate(headers):
            cols[i].markdown(f"<span style='font-size:13px'><b>{h}</b></span>", unsafe_allow_html=True)
        
        user_reg = st.session_state.get('region', 'ALL')
        allowed_regions = ["CN", "EU", "IN", "JP", "KR", "NA", "NM"] if user_reg == 'ALL' else [user_reg]
        
        for idx, r_id in enumerate(st.session_state[state_key]):
            cols = st.columns([3, 3, 3, 2, 2, 1, 2, 2, 2, 1])
            mat_7d = cols[0].text_input(f"7D_{tab_type}_{r_id}", label_visibility="collapsed")
            mat_18d = cols[1].text_input(f"18D_{tab_type}_{r_id}", label_visibility="collapsed")
            mat_name = cols[2].text_input(f"Name_{tab_type}_{r_id}", label_visibility="collapsed")
            region = cols[3].selectbox(f"Reg_{tab_type}_{r_id}", allowed_regions, label_visibility="collapsed")
            cat = cols[4].text_input(f"Cat_{tab_type}_{r_id}", placeholder="Auto/Manual", label_visibility="collapsed")
            qty = cols[5].text_input(f"Qty_{tab_type}_{r_id}", label_visibility="collapsed")
            incoterm = cols[6].text_input(f"Inco_{tab_type}_{r_id}", label_visibility="collapsed")
            shipping = cols[7].text_input(f"Ship_{tab_type}_{r_id}", label_visibility="collapsed")
            target = cols[8].text_input(f"Tgt_{tab_type}_{r_id}", label_visibility="collapsed")
            
            btn_col1, btn_col2 = cols[9].columns(2)
            btn_col1.form_submit_button("➕", on_click=add_row, args=(idx,), key=f"add_{tab_type}_{r_id}")
            btn_col2.form_submit_button("➖", on_click=del_row, args=(idx,), key=f"del_{tab_type}_{r_id}")
            
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
            
        submit_btn_label = "Calculate Standard Guide Prices" if tab_type == 'std' else "Send Batch Single BIN Requests to Pricing"
        submit_calc = st.form_submit_button(submit_btn_label, type="primary", use_container_width=True)
        
        if submit_calc:
            results = []
            has_error = False
            conn = db.get_connection()
            for idx, r in enumerate(rows_data):
                mat7d_val = r["Material code (7D)"].strip()
                mat18d_val = r["Material code (18D)"].strip()
                reg_val = r["Region"].strip()
                
                if not mat7d_val or not mat18d_val or not reg_val:
                    st.error(f"Row {idx + 1}: Missing mandatory fields (7D, 18D, Region)!")
                    has_error = True
                    continue
                    
                if not mat18d_val.startswith(mat7d_val[:7]):
                    st.error(f"Row {idx + 1}: Validation Error! First 7 characters of Code 18D must exactly match Code 7D.")
                    has_error = True
                    continue
                
                # Smart Category & Name Resolution!
                db_lookup_df = pd.read_sql_query("SELECT category, material_name FROM standard_products WHERE material_code = ?", conn, params=(mat7d_val[:7],))
                if not db_lookup_df.empty:
                    # OVERRIDE user input with correct DB category and name!
                    true_cat = db_lookup_df['category'].iloc[0]
                    true_name = db_lookup_df['material_name'].iloc[0]
                    
                    if r["Category"].strip() != "" and r["Category"].strip() != true_cat:
                        st.info(f"Row {idx + 1}: Category was auto-corrected from '{r['Category']}' to '{true_cat}' based on Database match.")
                    if r["Material Name"].strip() != "" and r["Material Name"].strip() != true_name:
                        st.info(f"Row {idx + 1}: Material Name was auto-corrected from '{r['Material Name']}' to '{true_name}' based on Database match.")
                        
                    r["Category"] = true_cat
                    r["Material Name"] = true_name
                    cat_val = true_cat
                else:
                    cat_val = r["Category"].strip()
                    mat_name_val = r["Material Name"].strip()
                    if not cat_val:
                        st.error(f"Row {idx + 1}: Unrecognized 7D Code! You must manually input the Category into the 'Cat' column.")
                        has_error = True
                        continue
                    if not mat_name_val:
                        st.warning(f"Row {idx + 1}: Unrecognized 7D Code. Please consider inputting a manual Name as well.")
                
                guide_price = "N/A"
                if tab_type == 'std':
                    # Standard BIN Logic
                    target_gm = db.get_gm_target(cat_val, reg_val)
                    cost_df = db.get_cost(mat7d_val[:7])
                    base_cost = cost_df['cost_unified'].iloc[0] if not cost_df.empty else 0.0
                    
                    if target_gm > 0 and target_gm < 1 and base_cost > 0:
                        gp_val = base_cost / (1 - target_gm)
                        guide_price = f"${gp_val:.4f}"
                    elif base_cost <= 0:
                        try:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO requests (sales_username, material_code, request_type, status, region, created_at, updated_at)
                                VALUES (?, ?, 'Standard Bin', 'Pending Cost', ?, ?, ?)
                            ''', (st.session_state.username, mat7d_val[:7], reg_val, datetime.datetime.now(), datetime.datetime.now()))
                            conn.commit()
                            db.log_action(st.session_state.username, "New Request", f"Auto-Sent pending cost request for {mat7d_val}")
                            st.warning(f"Row {idx+1}: Missing Baseline Cost! A 'Pending Cost' request was automatically sent to the Pricing Team.")
                        except Exception:
                            pass
                        guide_price = "Pending Cost"
                    else:
                        guide_price = "No GM Target"
                        
                    r["Guide Price"] = guide_price
                else:
                    # Single BIN Logic Workflow (Send Request to Pricing)
                    target_gm = db.get_gm_target(cat_val, reg_val)
                    if target_gm <= 0:
                        st.error(f"Row {idx + 1}: Failed to route to Pricing. No GM Target mapping found for Category '{cat_val}' and Region '{reg_val}'.")
                        has_error = True
                        continue
                        
                    cost_df = db.get_cost(mat7d_val[:7])
                    base_cost = cost_df['cost_unified'].iloc[0] if not cost_df.empty else 0.0
                    status_val = 'Pending Yield' if base_cost > 0 else 'Pending Cost & Yield'
                    
                    try:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO requests (sales_username, material_code, request_type, status, region, created_at, updated_at)
                            VALUES (?, ?, 'Single Bin', ?, ?, ?, ?)
                        ''', (st.session_state.username, mat7d_val[:7], status_val, reg_val, datetime.datetime.now(), datetime.datetime.now()))
                        conn.commit()
                        r["Submission Status"] = f"Success ({status_val})"
                        db.log_action(st.session_state.username, "New Request", f"Sales requested Single BIN for {mat7d_val}")
                    except Exception as e:
                        r["Submission Status"] = f"Failed DB Error"
                        st.error(f"Row {idx+1} Failed: {e}")
                        has_error = True
                
                results.append(r)
            conn.close()
            
            if not has_error and results:
                st.success("Batch Processing Complete!")
                st.dataframe(pd.DataFrame(results), use_container_width=True)


def render():
    st.header("Sales Pricing Tool 💰")
    
    tabs = st.tabs(["Calculator", "My Requests"])
    
    with tabs[0]:
        st.subheader("Batch Request Interface")
        
        calc_tabs = st.tabs(["Standard Bin", "Single Bin"])
        
        with calc_tabs[0]:
            render_grid('std', 'Standard BIN')

        with calc_tabs[1]:
            render_grid('sel', 'Single BIN')

    with tabs[1]:
        st.subheader("My Request History")
        conn = db.get_connection()
        df_my_reqs = pd.read_sql_query("SELECT id, material_code, request_type, region, status, actual_yield, final_price, created_at FROM requests WHERE sales_username = ? ORDER BY created_at DESC", conn, params=(st.session_state.username,))
        conn.close()
        
        if df_my_reqs.empty:
            st.info("Historical requests for Cost / Yield Updates sent to the Pricing team will appear here.")
        else:
            st.dataframe(df_my_reqs, use_container_width=True, hide_index=True)
