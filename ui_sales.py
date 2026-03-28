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
            
        submit_btn_label = "Calculate Standard Guide Prices" if tab_type == 'std' else "Send Batch Selected BIN Requests to Pricing"
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
            db_lookup_df = pd.read_sql_query("SELECT category, material_name, buffer FROM standard_products WHERE material_code = ?", conn, params=(mat7d_val[:7],))
            buffer_val = 0.0
            if not db_lookup_df.empty:
                # OVERRIDE user input with correct DB category and name!
                true_cat = db_lookup_df['category'].iloc[0]
                true_name = db_lookup_df['material_name'].iloc[0]
                try:
                    buffer_val = float(db_lookup_df['buffer'].iloc[0])
                except:
                    buffer_val = 0.0
                    
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
                    gp_val = ((1 + buffer_val) * base_cost) / (1 - target_gm)
                    guide_price = f"${gp_val:.4f}"
                    
                    gaps = db.get_price_gaps(cat_val)
                    gp_r1 = gp_val * (1 + gaps.get("GP Range 1", 0.0))
                    gp_r2 = gp_val * (1 + gaps.get("GP Range 2", 0.0))
                    gp_r3 = gp_val * (1 + gaps.get("GP Range 3", 0.0))
                    gp_r4 = gp_val * (1 + gaps.get("GP Range 4", 0.0))
                    gp_r5 = gp_val * (1 + gaps.get("GP Range 5", 0.0))
                    
                    r["GP Range 1"] = f"${gp_r1:.4f}"
                    r["GP Range 2"] = f"${gp_r2:.4f}"
                    r["GP Range 3"] = f"${gp_r3:.4f}"
                    r["GP Range 4"] = f"${gp_r4:.4f}"
                    r["GP Range 5"] = f"${gp_r5:.4f}"
                    
                    # Calculate VP Prices (VP = GP * 0.95)
                    r["VP Range 1"] = f"${gp_r1 * 0.95:.4f}"
                    r["VP Range 2"] = f"${gp_r2 * 0.95:.4f}"
                    r["VP Range 3"] = f"${gp_r3 * 0.95:.4f}"
                    r["VP Range 4"] = f"${gp_r4 * 0.95:.4f}"
                    vp_r5 = gp_r5 * 0.95
                    r["VP Range 5"] = f"${vp_r5:.4f}"
                    
                    # GT/ST Logic (Only for G team leaders)
                    if st.session_state.get('level') == "G team leader":
                        gt_price = vp_r5 * 0.95
                        st_price = gt_price * 0.95
                        r["GT Price"] = f"${gt_price:.4f}"
                        r["ST Price"] = f"${st_price:.4f}"
                    
                    # Save the successfully auto-calculated Standard BIN request into history
                    try:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO requests (sales_username, material_code, request_type, status, region, base_price, final_price, range_1, range_2, range_3, range_4, range_5, division, created_at, updated_at)
                            VALUES (?, ?, 'Standard Bin', 'Completed (Auto)', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (st.session_state.username, mat7d_val[:7], reg_val, base_cost, gp_val, gp_r1, gp_r2, gp_r3, gp_r4, gp_r5, st.session_state.division, datetime.datetime.now(), datetime.datetime.now()))
                        conn.commit()
                        db.log_action(st.session_state.username, "Standard BIN Calc", f"Auto-calculated Guide Price for {mat7d_val[:7]} at ${gp_val:.4f}")
                    except Exception as req_db_e:
                        pass
                        
                elif base_cost <= 0:
                    try:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO requests (sales_username, material_code, request_type, status, region, division, created_at, updated_at)
                            VALUES (?, ?, 'Standard Bin', 'Pending Cost', ?, ?, ?, ?)
                        ''', (st.session_state.username, mat7d_val[:7], reg_val, st.session_state.division, datetime.datetime.now(), datetime.datetime.now()))
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
                # Selected BIN Logic Workflow (Send Request to Pricing)
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
                        INSERT INTO requests (sales_username, material_code, request_type, status, region, division, created_at, updated_at)
                        VALUES (?, ?, 'Selected Bin', ?, ?, ?, ?, ?)
                    ''', (st.session_state.username, mat7d_val[:7], status_val, reg_val, st.session_state.division, datetime.datetime.now(), datetime.datetime.now()))
                    conn.commit()
                    r["Submission Status"] = f"Success ({status_val})"
                    db.log_action(st.session_state.username, "New Request", f"Sales requested Selected BIN for {mat7d_val}")
                except Exception as e:
                    r["Submission Status"] = f"Failed DB Error"
                    st.error(f"Row {idx+1} Failed: {e}")
                    has_error = True
            
            results.append(r)
        conn.close()
        
        if not has_error and results:
            st.success("Batch Processing Complete!")
            res_df = pd.DataFrame(results)
            st.dataframe(res_df, use_container_width=True)
            
            # Export functionality
            csv = res_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name=f"pricing_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )


def render():
    st.header("Sales Pricing Tool 💰")
    
    tabs = st.tabs(["Calculator", "My Requests"])
    
    with tabs[0]:
        st.subheader("Batch Request Interface")
        
        calc_tabs = st.tabs(["Standard Bin", "Selected Bin"])
        
        with calc_tabs[0]:
            render_grid('std', 'Standard BIN')

        with calc_tabs[1]:
            render_grid('sel', 'Selected BIN')

    with tabs[1]:
        st.subheader("My Request History")
        conn = db.get_connection()
        df_my_reqs = pd.read_sql_query("SELECT id, material_code, request_type, region, division, status, actual_yield, final_price, range_1, range_2, range_3, range_4, range_5, created_at FROM requests WHERE sales_username = ? AND division = ? ORDER BY created_at DESC", conn, params=(st.session_state.username, st.session_state.division))
        conn.close()

        if df_my_reqs.empty:
            st.info("Historical requests for Cost / Yield Updates sent to the Pricing team will appear here.")
        else:
            # Status color styling function
            def style_status_col(val):
                if val in ['Completed', 'Approved', 'Completed (Auto)']:
                    return 'color: #28a745; font-weight: bold;' # Green
                elif 'Pending' in val or val == 'Waiting':
                    return 'color: #fd7e14; font-weight: bold;' # Orange
                elif val in ['Rejected', 'Error']:
                    return 'color: #dc3545; font-weight: bold;' # Red
                return ''

            # Calculate VP Ranges on the fly for history view
            rename_dict = {}
            for i in range(1, 6):
                df_my_reqs[f'VP Range {i}'] = df_my_reqs[f'range_{i}'] * 0.95
                rename_dict[f'range_{i}'] = f'GP Range {i}'
            
            # Rename all GP columns at once
            df_my_reqs = df_my_reqs.rename(columns=rename_dict)

            # Privileged Pricing (GT/ST)
            if st.session_state.get('level') == "G team leader":
                df_my_reqs['GT Price'] = df_my_reqs['VP Range 5'] * 0.95
                df_my_reqs['ST Price'] = df_my_reqs['GT Price'] * 0.95
            
            st.write("💡 *Review statuses below (colored text). To export specific items, select their IDs in the box below.*")
            
            # 1. Colored Display (STABLE)
            st.dataframe(
                df_my_reqs.style.map(style_status_col, subset=['status']),
                use_container_width=True,
                hide_index=True,
            )
            
            # 2. Selection for Export
            all_ids = df_my_reqs['id'].tolist()
            selected_ids = st.multiselect("Select Request IDs to Export:", options=all_ids, placeholder="Leave empty to export all", key="sel_sales_hist")

            # Selection Logic
            df_to_export = df_my_reqs[df_my_reqs['id'].isin(selected_ids)] if selected_ids else df_my_reqs

            # Export History
            csv_hist = df_to_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 Export {'Selected' if selected_ids else 'All'} History to CSV",
                data=csv_hist,
                file_name=f"request_history_{st.session_state.username}_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="dl_btn_sales_final"
            )



