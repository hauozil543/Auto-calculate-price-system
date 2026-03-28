import streamlit as st
import pandas as pd
import database as db
import datetime

def render():
    st.header("Pricing Team Dashboard 📊")
    
    tabs = st.tabs(["🧮 Quick Calculator", "📨 Special Requests", "⚙️ Database Monitor"])
    
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
        # Headers: 7D, 18D, Name, Reg, Cat, Cost, Yield, Buff1, Buff2, Note2, Action
        cols = st.columns([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1])
        headers = ["7D", "18D", "Name", "Reg", "Cat", "Cost", "Yield", "B1%", "B2%", "Note2", ""]
        for i, h in enumerate(headers):
            cols[i].markdown(f"<span style='font-size:11px'><b>{h}</b></span>", unsafe_allow_html=True)
        
        regions = ["CN", "EU", "IN", "JP", "KR", "NA", "NM"]
        
        for idx, r_id in enumerate(st.session_state[state_key]):
            cols = st.columns([2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1])
            m7d = cols[0].text_input(f"7d_{r_id}", label_visibility="collapsed")
            m18d = cols[1].text_input(f"18d_{r_id}", label_visibility="collapsed")
            name = cols[2].text_input(f"name_{r_id}", label_visibility="collapsed")
            reg = cols[3].selectbox(f"reg_{r_id}", regions, label_visibility="collapsed")
            cat = cols[4].text_input(f"cat_{r_id}", label_visibility="collapsed")
            cost = cols[5].text_input(f"cost_{r_id}", label_visibility="collapsed")
            yld = cols[6].text_input(f"yld_{r_id}", value="85.0", label_visibility="collapsed")
            b1 = cols[7].text_input(f"b1_{r_id}", label_visibility="collapsed")
            b2 = cols[8].text_input(f"b2_{r_id}", value="0.0", label_visibility="collapsed")
            note2 = cols[9].text_input(f"n2_{r_id}", label_visibility="collapsed")
            
            btn_col1, btn_col2 = cols[10].columns(2)
            btn_col1.form_submit_button("➕", on_click=add_row, args=(idx,), key=f"add_p_{r_id}")
            btn_col2.form_submit_button("➖", on_click=del_row, args=(idx,), key=f"del_p_{r_id}")
            
            rows_data.append({
                "7D": m7d, "18D": m18d, "Name": name, "Region": reg, "Category": cat,
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
            
            calc_price = 0.0
            if 0 < target_gm < 1 and final_cost > 0:
                # Base = ((1 + B1) * (Cost / Yield)) / (1 - GM)
                calc_price = ((1 + final_b1) * (final_cost / final_yld)) / (1 - target_gm)
            
            res_row = r.copy()
            res_row["Name"] = final_name
            res_row["Category"] = final_cat
            res_row["Note 1"] = final_note1
            res_row["Cost"] = f"${final_cost:.4f}"
            res_row["Buffer 1"] = f"{final_b1*100:.1f}%"

            res_row["GM Target"] = f"{target_gm*100:.1f}%"
            res_row["GP Base"] = f"${calc_price:.4f}"
            
            if calc_price > 0:
                for i in range(1, 6):
                    # Final Range = Base * (1 + Gap) * (1 + B2)
                    gp_val = calc_price * (1 + gaps.get(f"GP Range {i}", 0.0)) * (1 + final_b2)
                    vp_val = gp_val * 0.95
                    res_row[f"GP Range {i}"] = f"${gp_val:.4f}"
                    res_row[f"VP Range {i}"] = f"${vp_val:.4f}"
                    
                    # Store last VR for GT/ST calculation
                    if i == 5:
                        gt_val = vp_val * 0.95
                        st_val = gt_val * 0.95
                        res_row["GT Price"] = f"${gt_val:.4f}"
                        res_row["ST Price"] = f"${st_val:.4f}"
            
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
    
    tabs = st.tabs(["🧮 Quick Calculator", "📨 Special Requests", "⚙️ Database Monitor"])
    
    with tabs[0]:
        render_pricing_grid()

    with tabs[1]:

        st.subheader("Actionable Sales Requests")
        st.info("Process pending quotation requests and missing cost queries to finalize Base Prices for Sales.")
        
        conn = db.get_connection()
        # Lọc theo Division của người dùng Pricing hiện tại
        df_req = pd.read_sql_query("SELECT id, sales_username, material_code, request_type, region, status, actual_yield, final_price, range_1, range_2, range_3, range_4, range_5, created_at FROM requests WHERE division = ? ORDER BY created_at DESC", conn, params=(st.session_state.division,))
        
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
            
            # 1. Colored Display
            st.dataframe(
                df_req.style.map(style_status_col, subset=['status']),
                use_container_width=True,
                hide_index=True,
            )
            
            # 2. Export Selection
            all_req_ids = df_req['id'].tolist()
            selected_req_ids = st.multiselect("Select IDs to Export:", options=all_req_ids, key="sel_pricing_log")

            # Selection Logic
            df_to_export = df_req[df_req['id'].isin(selected_req_ids)] if selected_req_ids else df_req
            
            csv_pricing = df_to_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 Export {'Selected' if selected_req_ids else 'All'} Pricing Log to CSV",
                data=csv_pricing,
                file_name=f"pricing_log_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )



            
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
                        
                        calc_price = 0.0
                        if target_gm > 0 and target_gm < 1 and final_cost > 0:
                            if req_type == "Selected Bin" and input_yield:
                                # Formula approved by user: Buffer * (Cost / Yield) / (1 - Target GM)
                                calc_price = ((1 + buffer_val) * (final_cost / (input_yield / 100.0))) / (1 - target_gm)
                            else:
                                # Standard Bin Formula: Buffer * Cost / (1 - Target GM)
                                calc_price = ((1 + buffer_val) * final_cost) / (1 - target_gm)
                                
                        gaps = db.get_price_gaps(cat_val)
                        gp_r1 = calc_price * (1 + gaps.get("GP Range 1", 0.0))
                        gp_r2 = calc_price * (1 + gaps.get("GP Range 2", 0.0))
                        gp_r3 = calc_price * (1 + gaps.get("GP Range 3", 0.0))
                        gp_r4 = calc_price * (1 + gaps.get("GP Range 4", 0.0))
                        gp_r5 = calc_price * (1 + gaps.get("GP Range 5", 0.0))
                                
                        try:
                            cursor = conn.cursor()
                            # Update requests table
                            cursor.execute('''
                                UPDATE requests
                                SET status = 'Completed', base_price = ?, actual_yield = ?, final_price = ?, range_1 = ?, range_2 = ?, range_3 = ?, range_4 = ?, range_5 = ?, updated_at = ?
                                WHERE id = ?
                            ''', (final_cost, input_yield if input_yield else 0.0, calc_price, gp_r1, gp_r2, gp_r3, gp_r4, gp_r5, datetime.datetime.now(), int(req_id)))
                            
                            # Note: Per user request, we NO LONGER update the 'costs' table from here.
                            # Manual inputs remain one-time values for this specific request.
                            
                            conn.commit()

                            
                            # Calculate primary VP for display
                            vp_price = calc_price * 0.95
                            vp_r5 = gp_r5 * 0.95
                            
                            success_msg = f"Request #{req_id} processed! **GP: ${calc_price:.4f}** | **VP: ${vp_price:.4f}**"
                            
                            # GT/ST Logic for G team leaders
                            if st.session_state.get('level') == "G team leader":
                                gt_price = vp_r5 * 0.95
                                st_price = gt_price * 0.95
                                success_msg += f" | **GT: ${gt_price:.4f}** | **ST: ${st_price:.4f}**"
                            
                            # Log action
                            db.log_action("System/Pricing", "Process Request", f"{st.session_state.username} processed Request #{req_id} for {sales_user}. GP: ${calc_price:.4f}, VP: ${vp_price:.4f}")
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
