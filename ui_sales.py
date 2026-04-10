import streamlit as st
import pandas as pd
import database as db
import datetime
import ui_pcr

def render_grid(tab_type, tab_name):
    st.markdown(f"### {tab_name} Interface")
    
    # Initialize default data for the editor
    user_reg = st.session_state.get('region', 'ALL')
    allowed_regions = ["CN", "EU", "IN", "JP", "KR", "NA", "NM"] if user_reg == 'ALL' else [user_reg]
    divisions = ["HI", "LT", "AM", "IT"]
    try: def_div = st.session_state.get('division', 'HI')
    except: def_div = "HI"

    default_df = pd.DataFrame([{
        "Mat 7D": "", "Mat 18D": "", "Name": "", "Reg": allowed_regions[0], 
        "Div": def_div, "Cat": "", "Qty": "0", "Inco": "", "Ship": "0", "Tgt Price": "0"
    }])

    with st.container(border=True):
        st.markdown(f"<small>Tip: You can copy and paste rows directly from Excel into this table.</small>", unsafe_allow_html=True)
        # Using st.data_editor for high-performance input
        edited_df = st.data_editor(
            default_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Reg": st.column_config.SelectboxColumn("Region", options=allowed_regions, required=True),
                "Div": st.column_config.SelectboxColumn("Division", options=divisions, required=True),
                "Qty": st.column_config.NumberColumn("Qty", min_value=0),
                "Ship": st.column_config.NumberColumn("Ship Fee", min_value=0),
                "Tgt Price": st.column_config.NumberColumn("Target Price", min_value=0),
            },
            key=f"editor_{tab_type}"
        )

        col_void, col_btn = st.columns([2, 1])
        submit_btn_label = "Calculate Standard Prices" if tab_type == 'std' else "Submit Selected BIN Requests"
        btn_icon = "📊" if tab_type == 'std' else "📩"
        submit_calc = col_btn.button(submit_btn_label, type="primary", use_container_width=True, icon=btn_icon)
        
    if submit_calc:
        results = []
        has_error = False
        conn = db.get_connection()
        
        # Mapping editor data back to the original dictionary structure to preserve 100% of the calculation logic
        rows_data = []
        for _, row in edited_df.iterrows():
            rows_data.append({
                "Material code (7D)": str(row["Mat 7D"]), "Material code (18D)": str(row["Mat 18D"]), 
                "Material Name": str(row["Name"]), "Region": str(row["Reg"]), "Division": str(row["Div"]), 
                "Category": str(row["Cat"]), "Quantity": row["Qty"], "Incoterm": str(row["Inco"]), 
                "Shipping fee": row["Ship"], "Target Price (USD)": str(row["Tgt Price"])
            })

        for idx, r in enumerate(rows_data):
            mat7d_val = r["Material code (7D)"].strip()
            mat18d_val = r["Material code (18D)"].strip()
            reg_val = r["Region"].strip()
            
            if not mat7d_val or not mat18d_val or not reg_val:
                st.error(f"Row {idx + 1}: Missing mandatory fields (7D, 18D, Region)!")
                has_error = True
                continue
                
            if not mat18d_val.startswith(mat7d_val[:7]):
                st.error(f"Row {idx + 1}: Validation Error! Code 18D must match Code 7D prefix.")
                has_error = True
                continue
            
            db_lookup_df = pd.read_sql_query("SELECT category, material_name, buffer FROM standard_products WHERE material_code = ?", conn, params=(mat7d_val[:7],))
            buffer_val = 0.0
            if not db_lookup_df.empty:
                true_cat = db_lookup_df['category'].iloc[0]
                true_name = db_lookup_df['material_name'].iloc[0]
                try: buffer_val = float(db_lookup_df['buffer'].iloc[0])
                except: buffer_val = 0.0
                r["Category"] = true_cat
                r["Material Name"] = true_name
                cat_val = true_cat
            else:
                cat_val = r["Category"].strip()
                if not cat_val:
                    st.error(f"Row {idx + 1}: Unrecognized 7D Code! Manual Category required.")
                    has_error = True
                    continue
                cat_val = cat_val

            target_val = 0.0
            try:
                target_str = str(r.get("Target Price (USD)", "")).replace("$", "").replace(",", "").strip()
                target_val = float(target_str)
            except: target_val = 0.0
            
            appr_level = "N/A"

            if tab_type == 'std':
                cost_df = db.get_cost(mat7d_val[:7])
                base_cost = cost_df['cost'].iloc[0] if not cost_df.empty else 0.0
                p_suite = db.calculate_full_pricing_suite(cat_val, reg_val, base_cost, yields=1.0, b1=buffer_val)
                gp_val = p_suite["gp_base"]
                
                if gp_val > 0:
                    if target_val > 0:
                        if target_val >= p_suite['gp_r5']: appr_level = "GP Level (Auto Approved)"
                        elif target_val >= p_suite['vp_r5']: appr_level = "VP Level (Auto Approved)"
                        elif target_val >= p_suite['gt']: appr_level = "GT Leader Approval"
                        else: appr_level = "Pricing Team Approval"
                    
                    r["Target Price (USD)"] = f"${target_val:.4f}" if target_val > 0 else ""
                    r["Approval Level"] = appr_level
                    
                    for i in range(1, 6): r[f"GP Range {i}"] = f"${p_suite[f'gp_r{i}']:.4f}"
                    for i in range(1, 6): r[f"VP Range {i}"] = f"${p_suite[f'vp_r{i}']:.4f}"
                    if st.session_state.get('level') == "G team leader":
                        r["GT Price"] = f"${p_suite['gt']:.4f}"
                        r["ST Price"] = f"${p_suite['st']:.4f}"
                    
                    try:
                        new_id = db.generate_request_id(r["Division"], reg_val)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO requests (custom_id, sales_username, material_code, request_type, status, region, base_price, final_price, range_1, range_2, range_3, range_4, range_5, target_price, approval_level, division, created_at, updated_at) VALUES (?, ?, ?, 'Standard Bin', 'Completed (Auto)', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (new_id, st.session_state.username, mat7d_val[:7], reg_val, base_cost, gp_val, p_suite["gp_r1"], p_suite["gp_r2"], p_suite["gp_r3"], p_suite["gp_r4"], p_suite["gp_r5"], target_val, appr_level, r["Division"], datetime.datetime.now(), datetime.datetime.now()))
                        conn.commit()
                    except Exception as e: st.error(f"Error Saving Record: {e}")
                elif base_cost <= 0:
                    try:
                        new_id = db.generate_request_id(r["Division"], reg_val)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO requests (custom_id, sales_username, material_code, request_type, status, region, division, created_at, updated_at) VALUES (?, ?, ?, 'Standard Bin', 'Pending Cost', ?, ?, ?, ?)", (new_id, st.session_state.username, mat7d_val[:7], reg_val, r["Division"], datetime.datetime.now(), datetime.datetime.now()))
                        conn.commit()
                        st.warning(f"Row {idx+1}: Sent to Pricing for Cost update.")
                    except: pass
            else:
                target_gm = db.get_gm_target(cat_val, reg_val)
                if target_gm <= 0:
                    st.error(f"Row {idx + 1}: Failed to route to Pricing. No GM Target mapping.")
                    has_error = True
                    continue
                cost_df = db.get_cost(mat7d_val[:7])
                base_cost = cost_df['cost'].iloc[0] if not cost_df.empty else 0.0
                status_val = 'Pending Yield' if base_cost > 0 else 'Pending Cost & Yield'
                try:
                    appr_level = "Pending Pricing"
                    new_id = db.generate_request_id(r["Division"], reg_val)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO requests (custom_id, sales_username, material_code, request_type, status, region, target_price, approval_level, division, created_at, updated_at) VALUES (?, ?, ?, 'Selected Bin', ?, ?, ?, ?, ?, ?, ?)", (new_id, st.session_state.username, mat7d_val[:7], status_val, reg_val, target_val, appr_level, r["Division"], datetime.datetime.now(), datetime.datetime.now()))
                    conn.commit()
                except: pass
            results.append(r)
        conn.close()
        
        if not has_error and results:
            st.success("Batch Processing Complete!")
            res_df = pd.DataFrame(results)
            with st.container(border=True):
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                csv = res_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("Download Results as CSV", csv, f"pricing_{datetime.datetime.now().strftime('%Y%m%d')}.csv", "text/csv", icon="📥")

def render():
    st.header("Sales Pricing Tool")
    active_tab = st.radio("Menu", ["Calculator", "My Requests", "PCR Dashboard"], horizontal=True, label_visibility="collapsed", key="sales_main_nav")
    
    if active_tab == "Calculator":
        st.subheader("Batch Request Interface")
        calc_tabs = st.tabs(["Standard Bin", "Selected Bin"])
        with calc_tabs[0]: render_grid('std', 'Standard BIN')
        with calc_tabs[1]: render_grid('sel', 'Selected BIN')

    elif active_tab == "My Requests":
        st.subheader("My Request History")
        conn = db.get_connection()
        df_my = pd.read_sql_query("SELECT id, custom_id, material_code, request_type, region, division, status, target_price, approval_level, actual_yield, final_price, range_1, range_2, range_3, range_4, range_5, created_at FROM requests WHERE sales_username = ? AND division = ? ORDER BY created_at DESC", conn, params=(st.session_state.username, st.session_state.division))
        conn.close()

        if df_my.empty:
            st.info("Historical requests will appear here.")
        else:
            def style_status(val):
                if val in ['Completed', 'Approved', 'Completed (Auto)']: return 'color: #28a745; font-weight: bold;'
                elif 'Pending' in val or val == 'Waiting': return 'color: #fd7e14; font-weight: bold;'
                elif val in ['Rejected', 'Error']: return 'color: #dc3545; font-weight: bold;'
                return ''

            df_my = df_my.rename(columns={'custom_id': 'Request ID'})
            for i in range(1, 6):
                df_my[f'VP Range {i}'] = df_my[f'range_{i}'] * 0.95
                df_my = df_my.rename(columns={f'range_{i}': f'GP Range {i}'})
            if st.session_state.get('level') == "G team leader":
                df_my['GT Price'] = df_my['VP Range 5'] * 0.95
                df_my['ST Price'] = df_my['GT Price'] * 0.95
            
            cols = ['Request ID', 'material_code', 'request_type', 'region', 'status', 'actual_yield'] + [f'GP Range {i}' for i in range(1, 6)] + [f'VP Range {i}' for i in range(1, 6)]
            if st.session_state.get('level') == "G team leader": cols += ['GT Price', 'ST Price']
            cols += ['target_price', 'approval_level', 'created_at']
            
            st.dataframe(df_my.reindex(columns=cols).style.map(style_status, subset=['status']), use_container_width=True, hide_index=True)
            
            id_map = dict(zip(df_my['Request ID'], df_my['id']))
            sel = st.multiselect("Select Request IDs to Export:", options=list(id_map.keys()), key="sel_s_exp")
            sel_ids = [id_map[s] for s in sel]
            df_exp = df_my[df_my['id'].isin(sel_ids)] if sel_ids else df_my
            csv = df_exp.to_csv(index=False).encode('utf-8-sig')
            st.download_button("Export History to CSV", csv, "history.csv", "text/csv")
            
    elif active_tab == "PCR Dashboard":
        ui_pcr.render_pcr_dashboard()
