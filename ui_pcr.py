import streamlit as st
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import database as db
import json
import io

def get_material_category(mat7d):
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT category FROM standard_products WHERE material_code = ?", conn, params=(mat7d,))
    conn.close()
    return str(df['category'].iloc[0]).strip() if not df.empty else "UNKNOWN"

def get_guide_price(mat7d, region, quarter, target_range):
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT pricing_data FROM guide_price_historical WHERE material_code = ? AND region = ? AND division = 'HI' AND quarter LIKE ?", conn, params=(mat7d, region, f"%{quarter}%"))
    conn.close()
    if df.empty: return None
    try:
        data = json.loads(df['pricing_data'].iloc[0])
        mapped_key = f"GP R{target_range[-1]}"
        if mapped_key in data: return float(data[mapped_key])
        for i in range(int(target_range[-1])-1, 0, -1):
            if f"GP R{i}" in data: return float(data[f"GP R{i}"])
        return None
    except: return None

def determine_range(volume, category, df_range):
    cdf = df_range[df_range['Category'] == category]
    if cdf.empty: return "Range 1"
    row = cdf.iloc[0]
    try:
        r2 = float(row.get('Range 2', float('inf')))
        r3 = float(row.get('Range 3', float('inf')))
        r4 = float(row.get('Range 4', float('inf')))
        r5 = float(row.get('Range 5', float('inf')))
    except: return "Range 1"
    if volume < r2: return "Range 1"
    if volume < r3: return "Range 2"
    if volume < r4: return "Range 3"
    if volume < r5: return "Range 4"
    return "Range 5"

def generate_ai_advice(overall_pcr, good_df, poor_df):
    advice = []
    advice.append(f"🔍 **Analysis:** Overall PCR for HI is **{overall_pcr:.2f}%**.")
    if overall_pcr >= 100: advice.append("✅ **Positive:** Margin compliance is being maintained.")
    elif overall_pcr >= 95: advice.append("⚠️ **Notice:** Small deviations detected in some volume tiers.")
    else: advice.append("🚨 **Warning:** Significant compliance gap detected.")
    if not poor_df.empty:
        advice.append("\n**Low PCR Items (Bottom 3):**")
        for _, row in poor_df.head(3).iterrows():
            advice.append(f"- {row['Material 7D']} (PCR: {row['PCR']:.1f}%)")
    return "\n".join(advice)

def render_pcr_dashboard():
    st.header("Advanced PCR Dashboard - Division HI")
    
    current_role = st.session_state.get('role', 'Sales')
    current_level = st.session_state.get('level', 'Staff')
    
    mode_options = ["View Released Reports"]
    if current_role in ["Pricing", "Admin"]:
        mode_options.append("Calculate New PCR")
    
    pcr_mode = st.radio("Dashboard Mode", mode_options, horizontal=True)
    
    # --- Mode: CALCULATE (Pricing Only) ---
    if pcr_mode == "Calculate New PCR":
        uploaded_file = st.file_uploader("Upload PCR Dataset (XLSX)", type=["xlsx"])
        if uploaded_file:
            if "pcr_file" not in st.session_state or st.session_state.pcr_file != uploaded_file.name:
                with st.spinner("Processing file..."):
                    xl = pd.ExcelFile(uploaded_file)
                    st.session_state.df_act = pd.read_excel(xl, sheet_name='Monthly Input', keep_default_na=False)
                    st.session_state.df_fcst = pd.read_excel(xl, sheet_name='Forecast', keep_default_na=False)
                    st.session_state.df_range = pd.read_excel(xl, sheet_name='Quantity Range', keep_default_na=False)
                    st.session_state.pcr_file = uploaded_file.name
                    for k in ['df_act', 'df_fcst', 'df_range']:
                        st.session_state[k].columns = st.session_state[k].columns.str.strip()
            
            df_act = st.session_state.df_act
            df_fcst = st.session_state.df_fcst
            df_range = st.session_state.df_range
            
            # Prep calculation inputs
            df_act['Created on(S/O)(date)'] = pd.to_datetime(df_act['Created on(S/O)(date)'], errors='coerce')
            valid_dates = df_act['Created on(S/O)(date)'].dropna()
            months = sorted(valid_dates.dt.strftime('%B %Y').unique(), key=lambda x: datetime.datetime.strptime(x, '%B %Y'))
            quarters = sorted(list(valid_dates.dt.to_period('Q').dt.strftime('Q%q %Y').unique()))
            
            with st.expander("Settings", expanded=True):
                c1, c2, c3 = st.columns(3)
                sel_period = c1.selectbox("Period", ["ALL"] + quarters + months)
                sel_guide = c2.text_input("Guide Quarter", value="26.1Q")
                sel_week = c3.text_input("Forecast Week", value="2026.05")

            if st.button("Run Calculation", type="primary"):
                with st.spinner("Running complex calculation..."):
                    df_act['Ext_7D'] = df_act['Material'].astype(str).str[:7]
                    df_act['Net price (KRW)'] = pd.to_numeric(df_act['Net price (KRW)'], errors='coerce').fillna(0)
                    df_act['Order qty.(A)'] = pd.to_numeric(df_act['Order qty.(A)'], errors='coerce').fillna(0)
                    
                    df_fcst['Ext_7D'] = df_fcst['Material'].astype(str).str[:7]
                    df_fcst['FCST balance'] = pd.to_numeric(df_fcst['FCST balance'], errors='coerce').fillna(0)
                    df_fcst_target = df_fcst[df_fcst['Registration week'].astype(str) == sel_week]

                    if sel_period == "ALL": df_eval = df_act
                    elif "Q" in sel_period:
                        q, y = sel_period.split(" ")
                        df_eval = df_act[(df_act['Created on(S/O)(date)'].dt.quarter == int(q[1])) & (df_act['Created on(S/O)(date)'].dt.year == int(y))]
                    else:
                        m_str = datetime.datetime.strptime(sel_period, '%B %Y').strftime('%Y-%m')
                        df_eval = df_act[df_act['Created on(S/O)(date)'].dt.strftime('%Y-%m') == m_str]

                    results = []
                    for _, row in df_eval.iterrows():
                        mat = row['Ext_7D']
                        qty = row['Order qty.(A)']
                        if qty <= 0 or row['Net price (KRW)'] <= 0: continue
                        
                        dt = row['Created on(S/O)(date)']
                        start = (dt - relativedelta(months=9)).replace(day=1)
                        end = dt + pd.offsets.MonthEnd(0)
                        
                        hist = df_act[(df_act['Created on(S/O)(date)'] >= start) & (df_act['Created on(S/O)(date)'] <= end) & (df_act['End customer'] == row['End customer']) & (df_act['Ext_7D'] == mat)]['Order qty.(A)'].sum()
                        futu = df_fcst_target[(df_fcst_target['Sales District'] == row['End customer']) & (df_fcst_target['Ext_7D'] == mat)]['FCST balance'].sum()
                        l12m = hist + futu
                        
                        cat = get_material_category(mat)
                        rng = determine_range(l12m, cat, df_range)
                        guide = get_guide_price(mat, str(row['Region']), sel_guide, rng)
                        if guide:
                            results.append({
                                "Sales Order": row['Sales order'], "Sales Employee": row['Sales employee name'], "Sales Employee ID": str(row['Sales employee']),
                                "Material 7D": mat, "Product Name": row['Material name'], "Region": row['Region'], "Category": cat,
                                "End Customer Code": row['End customer'], "End Customer Name": row['End customer name'],
                                "L12M Volume": l12m, "Assigned Range": rng, "Target Qty": qty, "Net Price (USD)": row['Net price (KRW)']/1350.0,
                                "Guide Price Applied": guide, "Sales Rev (USD)": (row['Net price (KRW)']/1350.0)*qty, "Guide Rev (USD)": guide*qty, "PCR": ((row['Net price (KRW)']/1350.0)/guide)*100
                            })
                    if results:
                        st.session_state.last_pcr_rdf = pd.DataFrame(results)
                        st.session_state.last_pcr_month = sel_period
                        st.rerun()
                    else: st.warning("No valid transactions found.")

            # --- Calculation Result Preview ---
            if "last_pcr_rdf" in st.session_state:
                res_df = st.session_state.last_pcr_rdf
                st.subheader(f"Reviewing: {st.session_state.last_pcr_month}")
                s_rev, g_rev = res_df['Sales Rev (USD)'].sum(), res_df['Guide Rev (USD)'].sum()
                ovr_pcr = (s_rev/g_rev)*100 if g_rev > 0 else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("OVERALL PCR", f"{ovr_pcr:.1f}%")
                m2.metric("Total Sales Rev", f"${s_rev:,.0f}")
                m3.metric("Total Guide Rev", f"${g_rev:,.0f}")
                st.dataframe(res_df.style.format({"PCR": "{:.1f}%", "Net Price (USD)": "${:.4f}"}), use_container_width=True, hide_index=True)
                
                if st.button("🚀 RELEASE REPORT TO SALES", type="primary", use_container_width=True):
                    success, msg = db.save_released_pcr(st.session_state.last_pcr_month, st.session_state.username, "HI", res_df)
                    if success:
                        st.success("Report successfully published to the team!")
                        del st.session_state.last_pcr_rdf
                        st.rerun()
                    else: st.error(msg)

    # --- Mode: VIEW (Everyone) ---
    elif pcr_mode == "View Released Reports":
        df_reps = db.get_released_reports_list("HI")
        if df_reps.empty:
            st.info("No reports released yet.")
        else:
            rep_options = {f"{r['period_name']} (at {r['created_at']})": r['id'] for _, r in df_reps.iterrows()}
            selected_rep = st.selectbox("Select History Report", list(rep_options.keys()))
            
            with st.spinner("Fetching data..."):
                ctx = {'role': current_role, 'level': current_level, 'username': st.session_state.username, 'region': st.session_state.get('region', 'ALL')}
                rdf = db.get_released_report_details(rep_options[selected_rep], ctx)
                
                if rdf.empty:
                    st.warning("No data found for your access level.")
                else:
                    # Rename to standard
                    rdf = rdf.rename(columns={'sales_order':'SO', 'sales_employee_name':'Sales Name', 'region':'Region', 'material_7d':'Material', 'net_price_usd':'Price', 'guide_price':'Guide', 'sales_rev':'Sales Rev', 'guide_rev':'Guide Rev', 'pcr':'PCR', 'target_qty':'Qty'})
                    s_r, g_r = rdf['Sales Rev'].sum(), rdf['Guide Rev'].sum()
                    ovr = (s_r/g_r)*100 if g_r > 0 else 0
                    
                    st.subheader("Published Report Data")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("PCR", f"{ovr:.1f}%")
                    m2.metric("Sales Rev", f"${s_r:,.0f}")
                    m3.metric("Guide Rev", f"${g_r:,.0f}")
                    # Remove technical IDs and use hide_index for a cleaner view
                    display_cols = [c for c in rdf.columns if c not in ['id', 'report_id', 'Sales Employee ID']]
                    st.dataframe(rdf[display_cols].style.format({"PCR": "{:.1f}%", "Price": "${:.4f}", "Guide": "${:.4f}"}), use_container_width=True, hide_index=True)
                    
                    st.write("---")
                    c1, c2 = st.columns(2)
                    with c1:
                        gr = rdf.groupby("Region").agg({"Sales Rev":"sum", "Guide Rev":"sum"}).reset_index()
                        gr["PCR"] = (gr["Sales Rev"]/gr["Guide Rev"])*100
                        st.write("**By Region**")
                        st.dataframe(gr[["Region", "PCR"]].style.format({"PCR":"{:.1f}%"}), use_container_width=True, hide_index=True)
                    with c2:
                        gs = rdf.groupby("Sales Name").agg({"Sales Rev":"sum", "Guide Rev":"sum"}).reset_index()
                        gs["PCR"] = (gs["Sales Rev"]/gs["Guide Rev"])*100
                        st.write("**By Salesperson**")
                        st.dataframe(gs[["Sales Name", "PCR"]].style.format({"PCR":"{:.1f}%"}), use_container_width=True, hide_index=True)
