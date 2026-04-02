import streamlit as st
import pandas as pd
import numpy as np

def generate_ai_advice(overall_pcr, good_df, poor_df):
    """Rule-based pseudo-AI to generate pricing advice based on data."""
    advice = []
    
    advice.append(f"🔍 **Phân tích tổng quan:** Mức độ tuân thủ giá (PCR) tổng thể của hệ thống hiện tại là **{overall_pcr:.2f}%**.")
    if overall_pcr >= 100:
        advice.append("✅ **Đánh giá:** Rất tuyệt vời! Đội ngũ Sales đang chốt được mức giá trung bình vượt hoặc bằng mức khuyến nghị (Target/Guide). Điều này giúp biên lợi nhuận (GP) của công ty vô cùng vững chắc.")
    elif overall_pcr >= 95:
        advice.append("⚠️ **Đánh giá:** Tốt, nhưng vẫn còn dư địa để tối ưu. Đang bám khá sát giá khuyến nghị nhưng một số giao dịch bị hụt giá cần được rà soát lại.")
    else:
        advice.append("🚨 **Đánh giá:** Đang dưới mức kỳ vọng! PCR tổng thể đang dưới 95%. Lời khuyên: Giám đốc kinh doanh cần kiểm tra lại chiến lược đàm phán của Sales hoặc xem xét lại giá Guide có đang quá cao so với thực tế sức mua của thị hiếu/đối thủ không.")

    if not poor_df.empty:
        advice.append("\n📉 **Sản phẩm cần có phương án can thiệp khẩn cấp (Poor Products):**")
        for _, row in poor_df.head(3).iterrows():
            mat = row.get('Material', 'Unknown')
            pcr_val = row.get('PCR', 0)
            advice.append(f"- Mã **{mat}** đang bị bán thấp hơn giá Guide (PCR: {pcr_val:.1f}%). *💡 AI Gợi ý: Hạn chế offer các mức giá ngoại lệ cho mã này trong tương lai trừ trường hợp đơn hàng có Volume đặc biệt lớn.*")

    if not good_df.empty:
        advice.append("\n🌟 **Sản phẩm chốt sale điểm sáng (Good Products):**")
        for _, row in good_df.head(3).iterrows():
            mat = row.get('Material', 'Unknown')
            pcr_val = row.get('PCR', 0)
            advice.append(f"- Mã **{mat}** làm rất tốt (PCR: {pcr_val:.1f}%). *💡 AI Gợi ý: Hãy khen thưởng Sale đẩy mạnh mã này và dùng đó làm Case Study đàm phán thành công cho sản phẩm ngách.*")
            
    return "\n".join(advice)

def render_pcr_dashboard():
    st.header("📊 Price Compliance Rate (PCR) Dashboard")
    st.markdown("**Hướng dẫn:** Tải lên file Data Bán Hàng theo tháng. File cần có ít nhất các cột: `Sales Name`, `Region`, `Material`, `Order Quantity`, `Sales Price`, `Guide Price`.")
    
    uploaded_file = st.file_uploader("📥 Tải lên Monthly Sales Data (Excel/CSV)", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
                
            # Chuẩn hóa tên cột
            df.columns = df.columns.str.strip()
            
            # Kiểm tra cột bắt buộc
            req_cols = ["Sales Name", "Region", "Material", "Order Quantity", "Sales Price", "Guide Price"]
            missing = [c for c in req_cols if c not in df.columns]
            if missing:
                st.error(f"❌ File thiếu các cột bắt buộc sau: {', '.join(missing)}")
                return
            
            # Ép kiểu dữ liệu
            df["Order Quantity"] = pd.to_numeric(df["Order Quantity"], errors='coerce').fillna(0)
            df["Sales Price"] = pd.to_numeric(df["Sales Price"], errors='coerce').fillna(0)
            df["Guide Price"] = pd.to_numeric(df["Guide Price"], errors='coerce').fillna(0)
            
            # Filter bar
            st.subheader("Bảng điều khiển (Filters)")
            col1, col2 = st.columns(2)
            with col1:
                regions = ["ALL"] + list(df["Region"].dropna().unique())
                sel_region = st.selectbox("Lọc theo Region (Khu vực)", regions)
            with col2:
                sales = ["ALL"] + list(df["Sales Name"].dropna().unique())
                sel_sale = st.selectbox("Lọc theo Sales Name (Tên NV)", sales)
                
            filtered_df = df.copy()
            if sel_region != "ALL":
                filtered_df = filtered_df[filtered_df["Region"] == sel_region]
            if sel_sale != "ALL":
                filtered_df = filtered_df[filtered_df["Sales Name"] == sel_sale]
                
            if filtered_df.empty:
                st.warning("Không có dữ liệu cho bộ lọc này!")
                return
                
            # Tính chỉ số PCR tổng thể
            total_sales_revenue = (filtered_df["Sales Price"] * filtered_df["Order Quantity"]).sum()
            total_guide_revenue = (filtered_df["Guide Price"] * filtered_df["Order Quantity"]).sum()
            
            pcr_overall = 0
            if total_guide_revenue > 0:
                pcr_overall = (total_sales_revenue / total_guide_revenue) * 100
                
            col_metric1, col_metric2, col_metric3 = st.columns(3)
            col_metric1.metric("💡 Overall PCR (Độ Tuân Thủ Giá)", f"{pcr_overall:.2f}%", 
                               f"{pcr_overall - 100:.2f}% so với Guide" if pcr_overall > 0 else "")
            col_metric2.metric("💰 Doanh Thu Thực (Actual Revenue)", f"${total_sales_revenue:,.0f}")
            col_metric3.metric("🎯 Doanh Thu Chuẩn (Guide Revenue)", f"${total_guide_revenue:,.0f}")
            
            # Tính PCR theo từng Material
            df_g = df.groupby("Material").apply(
                lambda x: pd.Series({
                    "Total Quantity": x["Order Quantity"].sum(),
                    "Total Sales Rev": (x["Sales Price"] * x["Order Quantity"]).sum(),
                    "Total Guide Rev": (x["Guide Price"] * x["Order Quantity"]).sum()
                })
            ).reset_index()
            
            df_g["PCR"] = np.where(df_g["Total Guide Rev"] > 0, 
                                   (df_g["Total Sales Rev"] / df_g["Total Guide Rev"]) * 100, 
                                   0)
                                   
            good_products = df_g[df_g["PCR"] >= 100].sort_values(by="PCR", ascending=False)
            poor_products = df_g[(df_g["PCR"] < 100) & (df_g["PCR"] > 0)].sort_values(by="PCR", ascending=True)

            st.write("---")
            col_prod1, col_prod2 = st.columns(2)
            with col_prod1:
                st.success(f"🌟 Good Products (PCR >= 100%)")
                st.dataframe(good_products[["Material", "PCR", "Total Quantity", "Total Sales Rev"]].style.format({"PCR": "{:.2f}%", "Total Quantity": "{:.0f}", "Total Sales Rev": "${:,.0f}"}), use_container_width=True, hide_index=True)
                
            with col_prod2:
                st.error(f"📉 Poor Products (PCR < 100%)")
                st.dataframe(poor_products[["Material", "PCR", "Total Quantity", "Total Guide Rev"]].style.format({"PCR": "{:.2f}%", "Total Quantity": "{:.0f}", "Total Guide Rev": "${:,.0f}"}), use_container_width=True, hide_index=True)

            st.write("---")
            st.subheader("Phân Tích Bằng AI (Smart Advisor)")
            with st.container(border=True):
                st.markdown(generate_ai_advice(pcr_overall, good_products, poor_products))
            
        except Exception as e:
            st.error(f"Lỗi đọc file hoặc tính toán: {e}")
