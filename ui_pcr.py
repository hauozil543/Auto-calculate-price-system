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
    except:
        return None

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
    advice.append(f"🔍 **Overall Analysis:** The overall Price Compliance Rate (PCR) for Division HI is **{overall_pcr:.2f}%**.")
    if overall_pcr >= 100:
        advice.append("✅ **Assessment:** Excellent! Operations are preserving strict margin compliance across dynamic Range brackets.")
    elif overall_pcr >= 95:
        advice.append("⚠️ **Assessment:** Good, but minor underpricing detected compared to the required volume-specific range baseline.")
    else:
        advice.append("🚨 **Assessment:** Below expectations! Significant drops below authorized volume-based Guide Prices. Recommend negotiation audits.")

    if not poor_df.empty:
        advice.append("\n📉 **Products requiring intervention (Poor PCR vs Volume Bracket):**")
        for _, row in poor_df.head(3).iterrows():
            advice.append(f"- Material **{row['Material 7D']}** was pushed below {row['Assigned Range']} pricing baselines (PCR: {row['PCR']:.1f}%).")

    if not good_df.empty:
        advice.append("\n🌟 **Top performing products:**")
        for _, row in good_df.head(3).iterrows():
            advice.append(f"- Material **{row['Material 7D']}** outperformed {row['Assigned Range']} expectations (PCR: {row['PCR']:.1f}%).")
            
    return "\n".join(advice)

def render_pcr_dashboard():
    st.header("Advanced Price Compliance Rate (PCR) - Division HI")
    
    uploaded_file = st.file_uploader("Upload PCR.xlsx (Contains Monthly Input, Quantity Range, Forecast)", type=["xlsx"])
    
    if uploaded_file:
        if "pcr_file" not in st.session_state or st.session_state.pcr_file != uploaded_file.name:
            with st.spinner("Loading Excel into memory..."):
                xl = pd.ExcelFile(uploaded_file)
                df_act = pd.read_excel(xl, sheet_name='Monthly Input', keep_default_na=False)
                df_fcst = pd.read_excel(xl, sheet_name='Forecast', keep_default_na=False)
                df_range = pd.read_excel(xl, sheet_name='Quantity Range', keep_default_na=False)
                
                df_act.columns = df_act.columns.str.strip()
                df_fcst.columns = df_fcst.columns.str.strip()
                df_range.columns = df_range.columns.str.strip()
                
                df_act['Created on(S/O)(date)'] = pd.to_datetime(df_act['Created on(S/O)(date)'], errors='coerce')
                df_act['Net price (KRW)'] = pd.to_numeric(df_act['Net price (KRW)'], errors='coerce').fillna(0)
                df_act['Order qty.(A)'] = pd.to_numeric(df_act['Order qty.(A)'], errors='coerce').fillna(0)
                df_act['Ext_7D'] = df_act['Material'].astype(str).str.strip().str[:7]
                
                df_fcst['FCST balance'] = pd.to_numeric(df_fcst['FCST balance'], errors='coerce').fillna(0)
                df_fcst['Ext_7D'] = df_fcst['Material'].astype(str).str.strip().str[:7]
                
                st.session_state.df_act = df_act
                st.session_state.df_fcst = df_fcst
                st.session_state.df_range = df_range
                st.session_state.pcr_file = uploaded_file.name
                
        df_act = st.session_state.df_act
        df_fcst = st.session_state.df_fcst
        df_range = st.session_state.df_range
        
        # Deduplicate FCST
        act_sales_orders = df_act['Sales order'].dropna().astype(str).tolist()
        df_fcst = df_fcst[~df_fcst['FCST Number'].astype(str).isin(act_sales_orders)]
        
        # Build selectbox options dynamically from dates
        valid_dates = df_act['Created on(S/O)(date)'].dropna()
        if valid_dates.empty:
            st.error("Could not find any valid dates in 'Created on(S/O)(date)' column.")
            return
            
        months_list = valid_dates.dt.strftime('%B %Y').unique()
        # Sort months chronologically
        months_list = sorted(months_list, key=lambda x: datetime.datetime.strptime(x, '%B %Y'))

        with st.expander("Calculation Settings", expanded=True):
            col1, col2, col3 = st.columns(3)
            target_ui_month = col1.selectbox("Target Evaluation Month", ["ALL"] + list(months_list))
            guide_quarter = col2.text_input("Guide Price Baseline Quarter", value="26.1Q")
            forecast_week = col3.text_input("Forecast Registration Week (e.g. 2026.05)", value="2026.05")
        
        if st.button("Process & Calculate PCR", type="primary"):
            
            # --- STRICT VALIDATIONS ---
            valid_fcst_weeks = df_fcst['Registration week'].dropna().astype(str).unique()
            if forecast_week not in valid_fcst_weeks:
                st.error(f"Lỗi Ràng Buộc: Tuần Forecast '{forecast_week}' KHÔNG TỒN TẠI trong bảng Forecast. Các mốc hiện có: {', '.join(valid_fcst_weeks)}")
                return
                
            if target_ui_month != "ALL":
                tgt_dt = datetime.datetime.strptime(target_ui_month, '%B %Y')
                tgt_q = (tgt_dt.month - 1) // 3 + 1
                tgt_yr = str(tgt_dt.year)[-2:]
                expected_guide = f"{tgt_yr}.{tgt_q}Q"
                
                if expected_guide not in guide_quarter:
                    st.error(f"Lỗi Ràng Buộc: Bạn chọn đánh giá '{target_ui_month}' (thuộc {expected_guide}) nhưng Quý Guide Price lại là '{guide_quarter}'. Dữ liệu tham chiếu không khớp thời gian!")
                    return
                    
                target_month_start = tgt_dt.replace(day=1)
                ten_months_ago = (target_month_start - relativedelta(months=9))
                min_date_in_db = df_act['Created on(S/O)(date)'].min()
                if ten_months_ago < min_date_in_db.replace(day=1):
                    st.warning(f"⚠️ Cảnh Báo Data L12M: Dữ liệu Actuals cũ nhất trong file là {min_date_in_db.strftime('%B %Y')}. Sẽ không tích lũy đủ 10 tháng lùi về trước từ '{target_ui_month}'. Phần mềm vẫn sẽ tính tổng các tháng khả dụng.")

            with st.spinner("Compiling rolling arrays..."):
                try:
                    df_fcst_target = df_fcst[df_fcst['Registration week'].astype(str) == forecast_week]
                    
                    if target_ui_month != "ALL":
                        # Filter eval slice
                        selected_dt_str = datetime.datetime.strptime(target_ui_month, '%B %Y').strftime('%Y-%m')
                        df_eval = df_act[df_act['Created on(S/O)(date)'].dt.strftime('%Y-%m') == selected_dt_str].copy()
                    else:
                        df_eval = df_act.copy()
                        
                    success_log = []
                    final_results = []
                    
                    progress = st.progress(0)
                    eval_total = len(df_eval)
                    processed = 0
                    
                    for idx, row in df_eval.iterrows():
                        processed += 1
                        if processed % max(1, int(eval_total/10)) == 0:
                            progress.progress(processed/eval_total)
                            
                        mat_7d = row['Ext_7D']
                        mat_name = str(row.get('Material name', ''))
                        region = str(row.get('Region', 'UNKNOWN')).strip()
                        end_cust = str(row.get('End customer', '')).strip()
                        end_cust_name = str(row.get('End customer name', ''))
                        sales_emp = str(row.get('Sales employee name', '')).strip()
                        sales_qty = row['Order qty.(A)']
                        net_price_krw = row['Net price (KRW)']
                        
                        if sales_qty <= 0 or net_price_krw <= 0: continue
                        net_price_usd = net_price_krw / 1350.0
                        
                        # Dynamically calculate L10M based on the row's specific transaction date
                        target_dt = row['Created on(S/O)(date)']
                        target_month_end = target_dt + pd.offsets.MonthEnd(0)
                        ten_months_ago = (target_dt - relativedelta(months=9)).replace(day=1)
                        
                        # Compute L10M Actual specifically for this End customer + Material
                        hist_vol = df_act[(df_act['Created on(S/O)(date)'] >= ten_months_ago) & 
                                          (df_act['Created on(S/O)(date)'] <= target_month_end) & 
                                          (df_act['End customer'].astype(str).str.strip() == end_cust) & 
                                          (df_act['Ext_7D'] == mat_7d)]['Order qty.(A)'].sum()
                        
                        # Compute F2M Forecast exactly as before
                        futu_vol = df_fcst_target[(df_fcst_target['Sales District'].astype(str).str.strip() == end_cust) & (df_fcst_target['Ext_7D'] == mat_7d)]['FCST balance'].sum()
                        
                        total_l12m = hist_vol + futu_vol
                        
                        # Match Range
                        cat = get_material_category(mat_7d)
                        assigned_range = determine_range(total_l12m, cat, df_range)
                        
                        # Match Guide
                        guide_prc = get_guide_price(mat_7d, region, guide_quarter, assigned_range)
                        
                        if guide_prc is None:
                            continue # IGNORING Missing 
                            
                        pcr_val = (net_price_usd / guide_prc) * 100
                        
                        final_results.append({
                            "Sales Order": row.get('Sales order', ''),
                            "Sales Employee": sales_emp,
                            "Material 7D": mat_7d,
                            "Product Name": mat_name,
                            "End Customer Code": end_cust,
                            "End Customer Name": end_cust_name,
                            "Region": region,
                            "Category": cat,
                            "L12M Volume": total_l12m,
                            "Assigned Range": assigned_range,
                            "Target Qty": sales_qty,
                            "Net Price (USD)": net_price_usd,
                            "Guide Price Applied": guide_prc,
                            "Sales Rev (USD)": net_price_usd * sales_qty,
                            "Guide Rev (USD)": guide_prc * sales_qty,
                            "PCR": pcr_val
                        })
                    
                    progress.empty()
                    
                    if not final_results:
                        st.warning("No records matched the criteria (Check Division HI historical availability or matching dates).")
                        return
                    
                    rdf = pd.DataFrame(final_results)
                    
                    total_s_rev = rdf['Sales Rev (USD)'].sum()
                    total_g_rev = rdf['Guide Rev (USD)'].sum()
                    overall = (total_s_rev/total_g_rev)*100 if total_g_rev > 0 else 0
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("OVERALL PCR (Dynamic Tier)", f"{overall:.2f}%")
                    c2.metric("Total Evaluated Sales Rev", f"${total_s_rev:,.0f}")
                    c3.metric("Total Equivalent Guide Rev", f"${total_g_rev:,.0f}")
                    
                    st.write("### Target Transactions Overview")
                    st.dataframe(rdf.style.format({"PCR": "{:.2f}%", "L12M Volume": "{:,.0f}", "Net Price (USD)": "${:.4f}", "Guide Price Applied": "${:.4f}"}), use_container_width=True)

                    st.write("---")
                    col_tab1, col_tab2 = st.columns(2)
                    
                    with col_tab1:
                        st.write("### PCR by Region")
                        g_reg = rdf.groupby("Region").agg({"Sales Rev (USD)": "sum", "Guide Rev (USD)": "sum"}).reset_index()
                        g_reg["PCR"] = np.where(g_reg["Guide Rev (USD)"] > 0, (g_reg["Sales Rev (USD)"] / g_reg["Guide Rev (USD)"]) * 100, 0)
                        st.dataframe(g_reg[["Region", "PCR"]].style.format({"PCR": "{:.2f}%"}), use_container_width=True, hide_index=True)
                        
                    with col_tab2:
                        st.write("### PCR by Salesperson")
                        g_sales = rdf.groupby(["Region", "Sales Employee"]).agg({"Sales Rev (USD)": "sum", "Guide Rev (USD)": "sum"}).reset_index()
                        g_sales["PCR"] = np.where(g_sales["Guide Rev (USD)"] > 0, (g_sales["Sales Rev (USD)"] / g_sales["Guide Rev (USD)"]) * 100, 0)
                        st.dataframe(g_sales[["Region", "Sales Employee", "PCR"]].style.format({"PCR": "{:.2f}%"}), use_container_width=True, hide_index=True)

                    g_prod = rdf.groupby("Material 7D").agg({
                        "Sales Rev (USD)": "sum", 
                        "Guide Rev (USD)": "sum", 
                        "Assigned Range": "first"
                    }).reset_index()
                    
                    g_prod["PCR"] = np.where(g_prod["Guide Rev (USD)"] > 0, (g_prod["Sales Rev (USD)"] / g_prod["Guide Rev (USD)"]) * 100, 0)
                    
                    good_products = g_prod[g_prod["PCR"] >= 100].sort_values(by="PCR", ascending=False)
                    poor_products = g_prod[(g_prod["PCR"] < 100) & (g_prod["PCR"] > 0)].sort_values(by="PCR", ascending=True)

                    st.write("---")
                    st.subheader("Export Report")
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        rdf.to_excel(writer, sheet_name='Chi Tiet (Transactions)', index=False)
                        g_prod.to_excel(writer, sheet_name='Tong (By Material)', index=False)
                        g_reg.to_excel(writer, sheet_name='Theo Region', index=False)
                        g_sales.to_excel(writer, sheet_name='Theo Sales', index=False)
                        
                    excel_data = output.getvalue()
                    safe_month = target_ui_month.replace(' ', '_').replace('/', '_')
                    st.download_button(
                        label="Download Excel Report",
                        data=excel_data,
                        file_name=f"PCR_Report_HI_{safe_month}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    st.write("---")
                    st.subheader("AI Analysis (Smart Advisor)")
                    with st.container(border=True):
                        st.markdown(generate_ai_advice(overall, good_products, poor_products).replace("🔍", "").replace("✅", "").replace("⚠️", "").replace("🚨", "").replace("📉", "").replace("🌟", ""))

                    
                except Exception as e:
                    st.error(f"Execution Engine Error: {e}")
