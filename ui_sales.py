import streamlit as st
import pandas as pd
import database as db

def render():
    st.header("Sales Pricing Tool 💰")
    
    tabs = st.tabs(["Calculator", "My Requests"])
    
    with tabs[0]:
        st.subheader("Guide Price Calculation")
        
        conn = db.get_connection()
        df_products = pd.read_sql_query("SELECT material_code, material_name, category FROM standard_products", conn)
        conn.close()
        
        if df_products.empty:
            st.error("Lỗi: Không tìm thấy sản phẩm nào trong CSDL.")
            return

        selected_code = st.selectbox(
            "Select Product (Material Code)", 
            df_products['material_code'].tolist(),
            format_func=lambda x: f"{x} - {df_products[df_products['material_code'] == x]['material_name'].iloc[0]}"
        )
        
        if selected_code:
            product_info = df_products[df_products['material_code'] == selected_code].iloc[0]
            cat = product_info['category']
            st.caption(f"Category: `{cat}`")
            
            with st.form("calc_form"):
                region = st.selectbox("Target Region (ví dụ)", ["CN", "EU", "IN", "JP", "KR"])
                
                # Truy xuất từ DB
                target_gm = db.get_gm_target(cat, region)
                cost_df = db.get_cost(selected_code)
                base_cost = cost_df['cost_unified'].iloc[0] if not cost_df.empty else 0.0
                
                # Tính giá (Guide Price = Cost / (1 - GM))
                guide_price = 0.0
                if target_gm > 0 and target_gm < 1:
                    guide_price = base_cost / (1 - target_gm)
                
                st.write(f"**Unified Base Cost**: `${base_cost:.4f}`")
                st.write(f"**Target GM**: `{target_gm * 100:.1f}%`")
                
                submit = st.form_submit_button("Calculate Guide Price", use_container_width=True)
                
                if submit:
                    if target_gm <= 0:
                        st.error("Chưa có chỉ tiêu GM cho Khu vực/Danh mục này (hoặc GM = 0)!")
                    elif base_cost <= 0:
                        st.error("Chưa có Baseline Cost! (Cost <= 0). Vui lòng gửi Request Sang Pricing.")
                    else:
                        st.success(f"### Est. Guide Price: **${guide_price:.4f}**")
                        
                        # Load thêm thông tin Price Gap để Sale tham khảo
                        gaps = db.get_price_gaps(cat)
                        if gaps:
                            with st.expander("📊 Phân bổ khoảng giá (Price Gaps Analytics)"):
                                for r_name, ratio in gaps.items():
                                    st.write(f"- Thêm chiết khấu **{r_name}**: `${guide_price * (1 - ratio):.4f}` (Gap: {ratio*100:.1f}%)")

    with tabs[1]:
        st.subheader("My Request History")
        st.info("Lịch sử các phiên yêu cầu Cost / Update Yield gửi sang Pricing sẽ nằm ở đây.")
