import streamlit as st
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import database as db
import json
import io
import plotly.express as px

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

def generate_ai_advice(df):
    if df.empty: return "No data available for analysis."
    
    overall_pcr = (df['Actual Rev'].sum() / df['Guide Rev'].sum() * 100) if df['Guide Rev'].sum() > 0 else 0
    # Leakage: PCR < 100 and highest revenue impact
    leakage_df = df[df['PCR'] < 100].sort_values(by='Actual Rev', ascending=False).head(3)
    # Champions: PCR >= 100 and highest revenue contribution
    champion_df = df[df['PCR'] >= 100].sort_values(by='Actual Rev', ascending=False).head(3)
    
    advice = []
    
    # 1. Executive Summary
    status_icon = "🟢" if overall_pcr >= 100 else ("🟡" if overall_pcr >= 95 else "🔴")
    advice.append(f"### {status_icon} Executive Performance Summary")
    advice.append(f"The current operational compliance (PCR) is standing at **{overall_pcr:.2f}%**. ")
    
    if overall_pcr >= 100:
        advice.append("Strategic positioning is robust, with average pricing exceeding guide baselines. Focus should shift to volume expansion and high-margin product retention.")
    else:
        gap = 100 - overall_pcr
        advice.append(f"There is a structural price gap of **{gap:.2f}%** compared to the guide baseline. Immediate margin recovery actions are recommended for high-volume accounts.")

    # 2. Critical Revenue Leakage (Revenue-weighted)
    if not leakage_df.empty:
        advice.append("\n### 📉 Top Revenue Leakage (Priority Action)")
        advice.append("The following products represent the highest financial impact due to sub-optimal pricing. **Negotiation audits are mandatory** for these items to recover lost margins:")
        for _, row in leakage_df.iterrows():
            # Handle possible missing 'Product Name' if dataframe was renamed earlier
            p_name = row.get('Product Name', row.get('product_name', 'Unknown'))
            advice.append(f"- **{row['Material 7D']} ({p_name})**: PCR is only **{row['PCR']:.1f}%** at a revenue scale of **${row['Actual Rev']:,.0f}**.")

    # 3. Profit Champions
    if not champion_df.empty:
        advice.append("\n### 🏆 Profit Champions (Best Practices)")
        advice.append("These products are successfully capturing value above the guide benchmarks. Analyze the negotiation tactics used here for replication across other accounts:")
        for _, row in champion_df.iterrows():
            advice.append(f"- **{row['Material 7D']}**: Achieving **{row['PCR']:.1f}%** compliance with **${row['Actual Rev']:,.0f}** in realized revenue.")

    # 4. Strategic Recommendation
    advice.append("\n### 🚀 Recommended Action Plan")
    if overall_pcr < 100:
        advice.append("1. **Price Integrity Audit**: Verify if special price conditions (off-invoice discounts) for 'Leakage' products are still commercially justified.")
        advice.append("2. **Margin-Focused Steering**: Shift sales incentives focus towards the 'Profit Champions' categories to balance the overall portfolio margin.")
    else:
        advice.append("1. **Market Share Defense**: Maintain current pricing for High-PCR products while monitoring competitor movements in the 'Leakage' areas.")
        advice.append("2. **Sustainability Check**: Ensure that High-PCR items are not at risk of substitution due to pricing being significantly above market averages.")

    return "\n".join(advice)

def render_pcr_dashboard():
    st.header("Advanced Price Compliance Analytics")
    
    current_role = st.session_state.get('role', 'Sales')
    current_level = st.session_state.get('level', 'Staff')
    
    mode_options = ["View Released Reports"]
    if current_role in ["Pricing", "Admin"]:
        mode_options.append("Calculate New PCR")
    
    pcr_mode = st.radio("Analytics Mode", mode_options, horizontal=True, label_visibility="collapsed")
    
    # --- Mode: CALCULATE (Pricing Only) ---
    if pcr_mode == "Calculate New PCR":
        with st.container(border=True):
            uploaded_file = st.file_uploader("Upload Monthly Performance Data (XLSX)", type=["xlsx"])
            if uploaded_file:
                if "pcr_file" not in st.session_state or st.session_state.pcr_file != uploaded_file.name:
                    with st.spinner("Compiling database for analysis..."):
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
                
                df_act['Created on(S/O)(date)'] = pd.to_datetime(df_act['Created on(S/O)(date)'], errors='coerce')
                valid_dates = df_act['Created on(S/O)(date)'].dropna()
                months = sorted(valid_dates.dt.strftime('%B %Y').unique(), key=lambda x: datetime.datetime.strptime(x, '%B %Y'))
                quarters = sorted(list(valid_dates.dt.to_period('Q').dt.strftime('Q%q %Y').unique()))
                
                st.write("---")
                c1, c2, c3 = st.columns(3)
                sel_period = c1.selectbox("Evaluation Period", ["ALL"] + quarters + months)
                sel_guide = c2.text_input("Guide Price Baseline", value="26.1Q")
                sel_week = c3.text_input("Forecast Lock Week", value="2026.05")

                if st.button("Generate Performance Analysis", type="primary", use_container_width=True, icon="📈"):
                    with st.spinner("Processing L12M complex arrays..."):
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
                        else: st.warning("No matched criteria for analysis.")

        # --- Calculation Result Preview ---
        if "last_pcr_rdf" in st.session_state:
            res_df = st.session_state.last_pcr_rdf
            st.write("---")
            st.subheader(f"Analysis Preview: {st.session_state.last_pcr_month}")
            s_rev, g_rev = res_df['Sales Rev (USD)'].sum(), res_df['Guide Rev (USD)'].sum()
            ovr_pcr = (s_rev/g_rev)*100 if g_rev > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            with m1: st.container(border=True).metric("OVERALL PCR", f"{ovr_pcr:.2f}%")
            with m2: st.container(border=True).metric("Total Sales Rev", f"${s_rev:,.0f}", delta=f"+ ₩{s_rev*1350:,.0f}")
            with m3: st.container(border=True).metric("Total Guide Rev", f"${g_rev:,.0f}", delta=f"+ ₩{g_rev*1350:,.0f}")
            

            # Moved to bottom
            
            if st.button("RELEASE PERFORMANCE REPORT", type="primary", use_container_width=True, icon="🚀"):
                success, msg = db.save_released_pcr(st.session_state.last_pcr_month, st.session_state.username, "HI", res_df)
                if success:
                    st.success("Report successfully released to Sales hierarchy.")
                    del st.session_state.last_pcr_rdf
                    st.rerun()
                else: st.error(msg)
            
            with st.expander("🔍 Show Detailed Transaction Audit", expanded=False):
                st.dataframe(res_df.style.format({"PCR": "{:.2f}%", "Net Price (USD)": "${:.4f}"}), use_container_width=True, hide_index=True)

    # --- Mode: VIEW (Everyone) ---
    elif pcr_mode == "View Released Reports":
        df_reps = db.get_released_reports_list("HI")
        if df_reps.empty:
            st.info("Performance reports are pending release by Pricing Team.")
        else:
            rep_options = {f"{r['period_name']} (Finalized: {r['created_at']})": r['id'] for _, r in df_reps.iterrows()}
            selected_rep = st.selectbox("Select Published Report", list(rep_options.keys()))
            
            with st.spinner("Decoding secured data..."):
                ctx = {'role': current_role, 'level': current_level, 'username': st.session_state.username, 'region': st.session_state.get('region', 'ALL')}
                rdf = db.get_released_report_details(rep_options[selected_rep], ctx)
                
                if rdf.empty:
                    st.warning("No data corresponds to your regional access level.")
                else:
                    rdf = rdf.rename(columns={
                        'sales_order':'Sales Order', 
                        'sales_employee_name':'Salesperson', 
                        'region':'Region',
                        'material_7d':'Material 7D', 
                        'net_price_usd':'Net Price (USD)', 
                        'guide_price':'Guide Price', 
                        'sales_rev':'Actual Rev', 
                        'guide_rev':'Guide Rev', 
                        'pcr':'PCR', 
                        'target_qty':'Target Qty'
                    })
                    s_r, g_r = rdf['Actual Rev'].sum(), rdf['Guide Rev'].sum()
                    ovr = (s_r/g_r)*100 if g_r > 0 else 0
                    
                    st.subheader(f"Published Performance Metrics")
                    m1, m2, m3 = st.columns(3)
                    with m1: st.container(border=True).metric("COMPLIANCE RATE", f"{ovr:.2f}%", delta=f"{ovr-100:.1f}%")
                    with m2: st.container(border=True).metric("Actual Revenue", f"${s_r:,.0f}", delta=f"+ ₩{s_r*1350:,.0f}")
                    with m3: st.container(border=True).metric("Baseline Guide", f"${g_r:,.0f}", delta=f"+ ₩{g_r*1350:,.0f}")
                    

                    # Moved to bottom
                    
                    st.write("---")
                    
                    # 1. Full-row Summary Table
                    gr = rdf.groupby("Region").agg({"Actual Rev":"sum", "Guide Rev":"sum"}).reset_index()
                    gr["PCR"] = (gr["Actual Rev"]/gr["Guide Rev"])*100
                    
                    st.write("**Regional Performance Summary**")
                    def color_pcr_text(val):
                        # Simple Green/Red text color based on 100% threshold
                        color = '#2e7d32' if val >= 100 else '#d32f2f'
                        return f'color: {color}; font-weight: bold;'

                    st.dataframe(gr.style.set_properties(**{
                        'text-align': 'center',
                        'font-size': '18px',
                        'font-weight': 'bold'
                    }).set_table_styles([
                        {'selector': 'th', 'props': [('text-align', 'center'), ('font-size', '20px'), ('font-weight', 'bold')]}
                    ]).format({
                        "Actual Rev": "${:,.0f}", 
                        "Guide Rev": "${:,.0f}", 
                        "PCR": "{:.2f}%"
                    }).applymap(color_pcr_text, subset=['PCR']), use_container_width=True, hide_index=True)

                    # 2. Charts in two columns below the table
                    c1, c2 = st.columns(2)
                    with c1:
                        fig_reg = px.pie(gr, values='Actual Rev', names='Region', title="Revenue Contribution by Region", hole=.4, color_discrete_sequence=px.colors.sequential.Greens_r)
                        st.plotly_chart(fig_reg, use_container_width=True)
                    with c2:
                        gs = rdf.groupby("Salesperson").agg({"Actual Rev":"sum", "Guide Rev":"sum"}).reset_index()
                        gs["PCR"] = (gs["Actual Rev"]/gs["Guide Rev"])*100
                        fig_sales = px.bar(gs, x='Salesperson', y='Actual Rev', title="Revenue by Salesperson", color='PCR', color_continuous_scale='RdYlGn', text_auto='.2s')
                        st.plotly_chart(fig_sales, use_container_width=True)
                    
                    g_p = rdf.groupby("Material 7D").agg({"Actual Rev":"sum", "Guide Rev":"sum"}).reset_index()
                    g_p["PCR"] = (g_p["Actual Rev"]/g_p["Guide Rev"])*100
                    st.write("---")
                    with st.container(border=True):
                        st.subheader("💡 Strategic Intelligence Analysis")
                        st.markdown(generate_ai_advice(rdf))
                    
                    with st.expander("🔍 Show Detailed Transaction Audit", expanded=False):
                        st.dataframe(rdf.style.format({"PCR": "{:.2f}%", "Net Price (USD)": "${:.4f}", "Guide Price": "${:.4f}"}), use_container_width=True, hide_index=True)
