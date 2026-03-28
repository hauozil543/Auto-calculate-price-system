import streamlit as st
import pandas as pd
import database as db
import datetime

    
def render_pricing_grid():
    st.write("Add rows to perform multi-line **Pricing Calculations** with manual overrides and Buffer 2.")
    
    state_key = "row_ids_pricing"
    next_key = "next_id_pricing"
    
    if state_key not in st.session_state:
        st.session_state[state_key] = [0]
        st.session_state[next_key] = 1
        
    def add_row(idx):
        st.session_state[state_key].insert(idx + 1, st.session_state[next_key])
        st.session_state[next_key] += 1
        
    def del_row(idx):
        if len(st.session_state[state_key]) > 1:
            st.session_state[state_key].pop(idx)
            
    with st.form("pricing_batch_calc_form"):
        rows_data = []
        # Headers: 7D, 18D, Name, Reg, Div, Cat, Cost, Yield, Buff1, Buff2, Note2, Action
        cols = st.columns([2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        headers = ["7D", "18D", "Name", "Reg", "Div", "Cat", "Cost", "Yield", "B1%", "B2%", "Note2", ""]
        for i, h in enumerate(headers):
            cols[i].markdown(f"<span style='font-size:11px'><b>{h}</b></span>", unsafe_allow_html=True)
        
        regions = ["CN", "EU", "IN", "JP", "KR", "NA", "NM"]
        
        for idx, r_id in enumerate(st.session_state[state_key]):
            cols = st.columns([2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1])
            m7d = cols[0].text_input(f"7d_{r_id}", label_visibility="collapsed")
            m18d = cols[1].text_input(f"18d_{r_id}", label_visibility="collapsed")
            name = cols[2].text_input(f"name_{r_id}", label_visibility="collapsed")
            reg = cols[3].selectbox(f"reg_{r_id}", regions, label_visibility="collapsed")
            
            # Dropdown Division (bắt buộc)
            divisions = ["HI", "LT", "AM", "IT"]
            try: def_div_idx = divisions.index(st.session_state.get('division', 'HI'))
            except: def_div_idx = 0
            div = cols[4].selectbox(f"div_p_{r_id}", divisions, index=def_div_idx, label_visibility="collapsed")
            
            cat = cols[5].text_input(f"cat_{r_id}", label_visibility="collapsed")
            cost = cols[6].text_input(f"cost_{r_id}", label_visibility="collapsed")
            yld = cols[7].text_input(f"yld_{r_id}", value="85.0", label_visibility="collapsed")
            b1 = cols[8].text_input(f"b1_{r_id}", label_visibility="collapsed")
            b2 = cols[9].text_input(f"b2_{r_id}", value="0.0", label_visibility="collapsed")
            note2 = cols[10].text_input(f"n2_{r_id}", label_visibility="collapsed")
            
            btn_col1, btn_col2 = cols[11].columns(2)
            btn_col1.form_submit_button("➕", on_click=add_row, args=(idx,), key=f"add_p_{r_id}")
            btn_col2.form_submit_button("➖", on_click=del_row, args=(idx,), key=f"del_p_{r_id}")
            
            rows_data.append({
                "7D": m7d, "18D": m18d, "Name": name, "Region": reg, "Division": div, "Category": cat,
                "Cost": cost, "Yield": yld, "Buffer 1": b1, "Buffer 2": b2, "Note 2": note2
            })
            
        submit_calc = st.form_submit_button("Calculate All Rows", type="primary", use_container_width=True)
        
    if submit_calc:
        results = []
        conn = db.get_connection()
        for idx, r in enumerate(rows_data):
            m7d_val = r["7D"].strip()
            if not m7d_val: continue
            
            # Auto-referencing via 7D
            db_lookup = pd.read_sql_query("SELECT category, material_name, buffer, note FROM standard_products WHERE material_code = ?", conn, params=(m7d_val[:7],))
            cost_lookup = pd.read_sql_query("SELECT cost_unified FROM costs WHERE material_code = ?", conn, params=(m7d_val[:7],))
            
            # Determine values (DB vs Manual)
            if not db_lookup.empty:
                final_name = db_lookup['material_name'].iloc[0]
                final_cat = db_lookup['category'].iloc[0]
                final_note1 = db_lookup['note'].iloc[0]
            else:
                final_name = r["Name"].strip() if r["Name"].strip() else "N/A"
                final_cat = r["Category"].strip() if r["Category"].strip() else "N/A"
                final_note1 = ""

            
            try:
                final_cost = float(r["Cost"]) if r["Cost"].strip() else (cost_lookup['cost_unified'].iloc[0] if not cost_lookup.empty else 0.0)
            except: final_cost = 0.0
            
            try:
                final_b1 = float(r["Buffer 1"]) if r["Buffer 1"].strip() else (float(db_lookup['buffer'].iloc[0]) if not db_lookup.empty else 0.0)
            except: final_b1 = 0.0
                
            try: final_yld = float(r["Yield"]) / 100.0
            except: final_yld = 0.85
                
            try: final_b2 = float(r["Buffer 2"]) / 100.0
            except: final_b2 = 0.0
            
            # Logic Calculation
            target_gm = db.get_gm_target(final_cat, r["Region"])
            gaps = db.get_price_gaps(final_cat)
            
            # Gọi hàm tính toán tập trung (Mặc định Yield = 100% nếu không nhập)
            try: yld_input = float(r["Yield"])
            except: yld_input = 100.0
            yld_val = yld_input / 100.0
            try: b2_val = float(r["Buffer 2"])
            except: b2_val = 0.0
            
            p_suite = db.calculate_full_pricing_suite(final_cat, r["Region"], final_cost, yields=yld_val, b1=final_b1, b2=b2_val)
            calc_price = p_suite["gp_base"]
            
            res_row = r.copy()
            res_row["Name"] = final_name
            res_row["Category"] = final_cat
            res_row["Note 1"] = final_note1
            res_row["Cost"] = f"${final_cost:.4f}"
            res_row["Buffer 1"] = f"{final_b1*100:.1f}%"
            res_row["GM Target"] = f"{p_suite['target_gm']*100:.1f}%"
            # res_row["GP Base"] = f"${calc_price:.4f}" # Removed per user request
            
            if calc_price > 0:
                # Group GP Ranges 1 -> 5
                for i in range(1, 6):
                    res_row[f"GP Range {i}"] = f"${p_suite[f'gp_r{i}']:.4f}"
                
                # Group VP Ranges 1 -> 5
                for i in range(1, 6):
                    res_row[f"VP Range {i}"] = f"${p_suite[f'vp_r{i}']:.4f}"
                
                # GT/ST Price
                res_row["GT Price"] = f"${p_suite['gt']:.4f}"
                res_row["ST Price"] = f"${p_suite['st']:.4f}"
            
            results.append(res_row)

        conn.close()
        
        if results:
            st.success("Batch Processing Complete!")
            res_df = pd.DataFrame(results)
            st.dataframe(res_df, use_container_width=True)
            csv = res_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Download Results", csv, "pricing_batch_results.csv", "text/csv")

def render():
    st.header("Pricing Team Dashboard 📊")
    
    tabs = st.tabs(["🧮 Quick Calculator", "📨 Special Requests", "⚙️ Database Monitor", "📜 Price History"])
    
    with tabs[0]:
        render_pricing_grid()

    with tabs[1]:

        st.subheader("Actionable Sales Requests")
        st.info("Process pending quotation requests and missing cost queries to finalize Base Prices for Sales.")
        
        conn = db.get_connection()
        # Lọc theo Division của người dùng Pricing hiện tại
        df_req = pd.read_sql_query("SELECT id, custom_id, sales_username, material_code, request_type, region, status, actual_yield, final_price, range_1, range_2, range_3, range_4, range_5, created_at FROM requests WHERE division = ? ORDER BY created_at DESC", conn, params=(st.session_state.division,))
        
        if df_req.empty:
            st.write("No requests pending.")
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
                
            st.write("### All Requests Log Tracker")
            st.write("💡 *Review statuses below. Select IDs to export specific rows.*")
            
            # Rename for display
            df_req = df_req.rename(columns={'custom_id': 'Request ID'})
            df_req = df_req.rename(columns={f'range_{i}': f'GP Range {i}' for i in range(1, 6)})
            
            # Add VP Ranges on the fly for viewing
            for i in range(1, 6):
                df_req[f'VP Range {i}'] = df_req[f'GP Range {i}'] * 0.95
                
            if st.session_state.get('level') == "G team leader":
                df_req['GT Price'] = df_req['VP Range 5'] * 0.95
                df_req['ST Price'] = df_req['GT Price'] * 0.95
            
            # DF hiển thị (đã ẩn id nội bộ)
            cols_to_show_p = ['Request ID', 'sales_username', 'material_code', 'request_type', 'region', 'status', 'actual_yield'] + [f'GP Range {i}' for i in range(1, 6)] + [f'VP Range {i}' for i in range(1, 6)]
            if st.session_state.get('level') == "G team leader":
                cols_to_show_p += ['GT Price', 'ST Price']
            cols_to_show_p += ['created_at']
            
            df_display_p = df_req.reindex(columns=cols_to_show_p)
            
            # 1. Colored Display
            st.dataframe(
                df_display_p.style.map(style_status_col, subset=['status']),
                use_container_width=True,
                hide_index=True,
            )
            
            # 2. Export Selection (Dùng Request ID để hiển thị)
            id_map_p = dict(zip(df_req['Request ID'], df_req['id']))
            selected_display_ids = st.multiselect("Select Request IDs to Export:", options=list(id_map_p.keys()), key="sel_pricing_log")
            selected_internal_ids = [id_map_p[sid] for sid in selected_display_ids]

            # Selection Logic
            df_to_export = df_req[df_req['id'].isin(selected_internal_ids)] if selected_internal_ids else df_req
            
            csv_pricing = df_to_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 Export {'Selected' if selected_display_ids else 'All'} Pricing Log to CSV",
                data=csv_pricing,
                file_name=f"pricing_log_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )



            
            df_pending = df_req[df_req['status'].str.contains('Pending')]
            
            if not df_pending.empty:
                st.markdown("---")
                st.subheader("Process a Pending Ticket")
                
                req_id_display = st.selectbox("Select Request ID", df_pending['Request ID'].tolist())
                req_row = df_pending[df_pending['Request ID'] == req_id_display].iloc[0]
                req_id_internal = req_row['id']
                
                req_type = req_row['request_type']
                req_status = req_row['status']
                mat_code = req_row['material_code']
                reg_val = req_row['region']
                sales_user = req_row['sales_username']
                
                st.write(f"**Target:** `{mat_code}` | **Type:** `{req_type}` | **Region:** `{reg_val}` | **Sales Rep:** `{sales_user}` | **Status:** `{req_status}`")
                
                with st.form("process_ticket_form"):
                    # Always show Cost input (pre-filled from DB if available)
                    c_df = pd.read_sql_query("SELECT cost_unified FROM costs WHERE material_code = ?", conn, params=(mat_code[:7],))
                    db_cost = c_df['cost_unified'].iloc[0] if not c_df.empty else 0.0
                    
                    if db_cost > 0:
                        st.info(f"Current System Cost: **${db_cost:.4f}**")
                        input_cost = st.number_input("Cost ($)", min_value=0.0001, format="%.4f", value=float(db_cost))
                    else:
                        st.warning("⚠️ No Cost found in system for this material.")
                        input_cost = st.number_input("Input Manual Cost ($)", min_value=0.0001, format="%.4f", value=10.0000)
                    
                    # Yield input visibility
                    input_yield = None
                    if "Yield" in req_status or req_type == "Selected Bin":
                        input_yield = st.number_input("Input Production Yield (%)", min_value=0.1, max_value=100.0, value=85.0, step=0.1)

                        
                    submit_process = st.form_submit_button("Submit & Calculate Final Guide Price", type="primary")
                    
                    if submit_process:
                        final_cost = input_cost
                            
                        prod_df = pd.read_sql_query("SELECT category, buffer FROM standard_products WHERE material_code = ?", conn, params=(mat_code[:7],))

                        cat_val = ""
                        buffer_val = 0.0
                        if not prod_df.empty:
                            cat_val = prod_df['category'].iloc[0]
                            try:
                                buffer_val = float(prod_df['buffer'].iloc[0])
                            except:
                                buffer_val = 0.0
                                
                        target_gm = db.get_gm_target(cat_val, reg_val)
                        
                        # Gọi hàm tính toán tập trung
                        try:
                            # Lô-gic: Standard Bin luôn 100%, Selected Bin lấy theo input
                            if req_type == "Standard Bin":
                                cur_yield = 1.0
                            else:
                                cur_yield = input_yield / 100.0 if input_yield else 0.85
                                
                            p_suite = db.calculate_full_pricing_suite(cat_val, reg_val, final_cost, yields=cur_yield, b1=buffer_val)
                            calc_price = p_suite["gp_base"]
                            
                            cursor = conn.cursor()
                            # Update requests table
                            cursor.execute('''
                                UPDATE requests
                                SET status = 'Completed', base_price = ?, actual_yield = ?, final_price = ?, range_1 = ?, range_2 = ?, range_3 = ?, range_4 = ?, range_5 = ?, updated_at = ?
                                WHERE id = ?
                            ''', (final_cost, input_yield if input_yield else 0.0, calc_price, p_suite["gp_r1"], p_suite["gp_r2"], p_suite["gp_r3"], p_suite["gp_r4"], p_suite["gp_r5"], datetime.datetime.now(), int(req_id_internal)))
                            
                            conn.commit()

                            # Calculate primary VP for display
                            vp_price = p_suite["vp_r1"] # VP for Range 1 as reference
                            vp_r5 = p_suite["vp_r5"]
                            
                            gp_r1 = p_suite["gp_r1"]
                            success_msg = f"Request {req_id_display} processed! **GP Range 1: ${gp_r1:.4f}** | **VP Range 1: ${p_suite['vp_r1']:.4f}**"
                            
                            # GT/ST Logic for G team leaders
                            if st.session_state.get('level') == "G team leader":
                                success_msg += f" | **GT: ${p_suite['gt']:.4f}** | **ST: ${p_suite['st']:.4f}**"
                            
                            # Log action
                            db.log_action("System/Pricing", "Process Request", f"{st.session_state.username} processed {req_id_display}. GP: ${calc_price:.4f}")
                            st.success(success_msg)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating request: {e}")
                            
        conn.close()
        
    with tabs[2]:
        st.subheader("Real-time Database Status")
        st.write("Quick monitor of the current database cache configuration (SQLite).")
        conn = db.get_connection()
        
        col1, col2, col3, col4 = st.columns(4)
        try: count_std = pd.read_sql_query("SELECT COUNT(*) FROM standard_products", conn).iloc[0,0]
        except: count_std = 0
        try: count_gm = pd.read_sql_query("SELECT COUNT(*) FROM gm_targets", conn).iloc[0,0]
        except: count_gm = 0
        try: count_gap = pd.read_sql_query("SELECT COUNT(*) FROM price_gaps", conn).iloc[0,0]
        except: count_gap = 0
        try: count_cost = pd.read_sql_query("SELECT COUNT(*) FROM baseline_costs", conn).iloc[0,0]
        except: count_cost = 0
        conn.close()
        
        col1.metric("Standard Products", count_std)
        col2.metric("GM Targets Rules", count_gm)
        col3.metric("Price Gap Rules", count_gap)
        col4.metric("Cost Records", count_cost)
        
        st.divider()
        st.subheader("🚨 Database Master Override")
        st.markdown("Use this tool to re-upload the latest **Price Master Excel** file. This will wipe the old (possibly corrupted) data for regions like **NA** and replace it with clean data.")
        
        uploaded_master = st.file_uploader("Select Price Master Excel File (.xlsx)", type=["xlsx"])
        
        if uploaded_master is not None:
            if st.button("🚨 Overwrite Master Database with Excel", type="primary", use_container_width=True):
                with st.spinner("Processing Excel Master... This may take a minute."):
                    success, msg = db.import_excel_to_sqlite(uploaded_master)
                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)

    with tabs[3]:
        st.subheader("📜 Historical Price Management")
        st.markdown("Use this tab to upload and view historical guide prices across all quarters.")
        
        st.divider()
        st.subheader("📂 Guide Price History Upload (Master)")
        st.markdown("Select a division and upload historical price files (**25.1Q - 26.1Q**).")
        
        h_col1, h_col2 = st.columns([1, 2])
        target_div = h_col1.selectbox("Division", ["HI", "AM", "IT", "LT"], key="hist_upload_div")
        uploaded_hist = h_col2.file_uploader(f"Choose Excel for {target_div}", type=["xlsx"])
        
        if uploaded_hist and st.button(f"📥 Batch Import {target_div} History", use_container_width=True):
            with st.spinner(f"Processing {target_div} historical data..."):
                success, msg = db.import_guide_price_history(uploaded_hist, target_div)
                if success:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)

        st.divider()
        st.subheader("🔍 Historical Price Lookup")
        search_mat = st.text_input("Enter 7D Material Code", placeholder="e.g. 7251744", key="hist_search_input")
        if search_mat:
            with st.spinner("Retrieving history..."):
                df_hist = db.search_guide_price_history(search_mat)
                if not df_hist.empty:
                    st.write(f"Showing results for: **{search_mat}**")
                    st.dataframe(df_hist, use_container_width=True)
                else:
                    st.info(f"No records found for '{search_mat}'.")
