import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 網頁基礎設定
st.set_page_config(page_title="Seeds Hope 多品類庫存管理", page_icon="💐", layout="centered")
st.title("💐 Seeds Hope 多品類庫存即時管理系統")

# 1. 初始化 Google Sheets 連線
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = get_gspread_client()
    sh = gc.open("Seeds Hope 庫存管理")
    worksheet = sh.worksheet("Stock")
except Exception as e:
    st.error(f"❌ 無法連線至 Google 試算表，請確認設定。錯誤回報: {e}")
    st.stop()

# 讀取最新庫存資料
def load_data():
    try:
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"❌ 讀取資料表結構錯誤，請確認欄位標題是否正確。錯誤回報: {e}")
        st.stop()

df = load_data()

# ─── 注入自定義 CSS 樣式（適應手機佈局與溫馨色調） ───
ST_CSS_STYLE = """
<style>
[data-testid="stMetricLabel"] { display: none; }
.stock-cards-container { display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; padding: 10px 0; }
.stock-card { background-color: #fdfaf5; border: 1px solid #e2d7cd; border-radius: 14px; box-shadow: 0 3px 8px rgba(0,0,0,0.04); width: calc(100% - 20px); max-width: 450px; padding: 18px; }
@media (min-width: 768px) { .stock-card { width: calc(50% - 15px); } }
.card-header { font-size: 18px; font-weight: bold; color: #5d4037; margin-bottom: 15px; text-align: center; border-bottom: 1px dashed #e2d7cd; padding-bottom: 8px; }
.card-body-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center; }
.data-node { display: flex; flex-direction: column; align-items: center; padding: 8px 4px; background-color: #ffffff; border-radius: 8px; border: 1px solid #f5ebe0; }
.node-icon { font-size: 18px; margin-bottom: 2px; }
.node-label { font-size: 13px; color: #8d6e63; margin-bottom: 4px; }
.node-value { font-size: 20px; font-weight: bold; }
.semi-val { color: #2e7d32; }
.ready-val { color: #1565c0; }
.sales-val { color: #e65100; }
.stock-card.low-stock { background-color: #fffde7; border-color: #ffe082; }
.stock-card.low-stock .ready-val { color: #d84315; }
</style>
"""
st.markdown(ST_CSS_STYLE, unsafe_allow_html=True)

# 安全檢查
required_cols = ["種類", "款式名稱", "半成品庫存", "可出貨庫存", "累積銷售量"]
if not df.empty and not all(c in df.columns for c in required_cols):
    st.error("❌ Google 試算表欄位不正確！請確認第一行包含：種類、款式名稱、半成品庫存、可出貨庫存、累積銷售量")
    st.stop()

# ---------------------------------------------------------
# 【核心功能】主動線：切換商品種類
# ---------------------------------------------------------
st.subheader("📁 請選擇商品大類")
# 自動從試算表撈取所有不重複的種類，若為空則預設提供花束
existing_categories = df["種類"].unique().tolist() if not df.empty else ["花束"]
if not existing_categories:
    existing_categories = ["花束"]

# 讓太太在手機上一鍵勾選切換
selected_category = st.radio("當前檢視種類：", existing_categories, horizontal=True)

# 根據勾選的種類，篩選出對應的商品資料
filtered_df = df[df["種類"] == selected_category] if not df.empty else pd.DataFrame()

# ---------------------------------------------------------
# 2. 即時看板展示（僅顯示篩選後的種類）
# ---------------------------------------------------------
st.subheader(f"📊 【{selected_category}】當前庫存與熱銷狀態")
if not filtered_df.empty:
    st.markdown('<div class="stock-cards-container">', unsafe_allow_html=True)
    for index, row in filtered_df.iterrows():
        semi = int(row["半成品庫存"])
        ready = int(row["可出貨庫存"])
        sales = int(row["累積銷售量"])
        
        low_stock_class = "low-stock" if ready <= 3 else ""
        alert_icon = "⚠️ " if ready <= 3 else ""
        
        card_html = f"""
        <div class="stock-card {low_stock_class}">
            <div class="card-header">{row['款式名稱']}</div>
            <div class="card-body-grid">
                <div class="data-node">
                    <span class="node-icon">🌿</span>
                    <span class="node-label">半成品</span>
                    <span class="node-value semi-val">{semi}</span>
                </div>
                <div class="data-node">
                    <span class="node-icon">📦</span>
                    <span class="node-label">{alert_icon}可出貨</span>
                    <span class="node-value ready-val">{ready}</span>
                </div>
                <div class="data-node">
                    <span class="node-icon">🔥</span>
                    <span class="node-label">已銷售</span>
                    <span class="node-value sales-val">{sales}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info(f"💡 目前【{selected_category}】分類下暫無任何品項，請在下方新增。")

st.divider()

# ---------------------------------------------------------
# 3. 現場進銷貨與轉化操作介面（自動連動種類）
# ---------------------------------------------------------
st.subheader("🔄 庫存異動與流程登記")

action = st.radio(
    "步驟 1：請選擇動作", 
    ["🛒 現場銷售（扣可出貨）", "🔧 完工包裝（半成品 ➔ 可出貨）", "🌿 追加資材（加半成品）", "✨ 新增全新款式"], 
    horizontal=True
)

if action == "✨ 新增全新款式":
    # 新增商品時，可以選擇加入現有種類，或手動輸入全新的大分類
    cat_option = st.selectbox("步驟 2-1：將新商品歸類至...", existing_categories + ["+ 建立全新種類"])
    if cat_option == "+ 建立全新種類":
        target_category = st.text_input("請輸入全新種類名稱", placeholder="例如：過年小物").strip()
    else:
        target_category = cat_option
        
    new_item_name = st.text_input("步驟 2-2：請輸入新商品款式名稱", placeholder="例如：手寫特大紅包袋")
    init_semi = st.number_input("步驟 3-1：輸入初始「半成品」庫存", min_value=0, value=0, step=1)
    init_ready = st.number_input("步驟 3-2：輸入初始「可出貨」庫存", min_value=0, value=10, step=1)
else:
    if filtered_df.empty:
        st.warning(f"⚠️ 目前【{selected_category}】沒有任何品項可供操作，請先選擇『新增全新款式』。")
        st.stop()
    # 下拉選單只會帶出當前勾選種類下的商品，防止點錯
    selected_item = st.selectbox(f"步驟 2：選擇【{selected_category}】品項", filtered_df["款式名稱"].tolist())
    qty = st.number_input("步驟 3：輸入執行數量", min_value=1, value=1, step=1)

st.write("")
if st.button("🚀 確認送出更新", type="primary", use_container_width=True):
    
    # ─── 狀況 A：新增全新款式 ───
    if action == "✨ 新增全新款式":
        if not target_category:
            st.error("❌ 種類名稱不能為空！")
            st.stop()
        cleaned_name = new_item_name.strip()
        if not cleaned_name:
            st.error("❌ 請填寫新款式名稱！")
            st.stop()
            
        # 檢查在同一個分類下是否已有同名商品
        if not df.empty and cleaned_name in df[df["種類"] == target_category]["款式名稱"].tolist():
            st.error(f"❌ 在【{target_category}】分類中，款式【{cleaned_name}】已經存在。")
        else:
            # 寫入格式：[種類, 款式名稱, 半成品, 可出貨, 累積銷售]
            worksheet.append_row([target_category, cleaned_name, init_semi, init_ready, 0])
            st.success(f"🎉 成功新增商品：【{target_category}】 ➔ 【{cleaned_name}】！")
            st.rerun()
            
    # ─── 狀況 B：庫存異動（利用「種類」+「款式名稱」進行精準定位） ───
    else:
        # 精準定位：同時符合當前選定種類與款式的列
        match_condition = (df["種類"] == selected_category) & (df["款式名稱"] == selected_item)
        p_idx = df[match_condition].index[0]
        g_row = p_idx + 2  # 加上標頭與索引偏置
        
        current_semi = int(df.loc[p_idx, "半成品庫存"])
        current_ready = int(df.loc[p_idx, "可出貨庫存"])
        current_sales = int(df.loc[p_idx, "累積銷售量"])

        if "現場銷售" in action:
            if current_ready < qty:
                st.error(f"❌ 庫存不足！可出貨僅剩 {current_ready}，無法銷售 {qty}。")
            else:
                worksheet.update_cell(g_row, 4, current_ready - qty)  # 更新第4欄 (D:可出貨庫存)
                worksheet.update_cell(g_row, 5, current_sales + qty)  # 更新第5欄 (E:累積銷售量)
                st.success(f"🎉 登記成功！【{selected_item}】成功售出 {qty}。")
                st.rerun()
                
        elif "完工包裝" in action:
            if current_semi < qty:
                st.error(f"❌ 轉化失敗！半成品僅剩 {current_semi}，不足以綁製 {qty}。")
            else:
                worksheet.update_cell(g_row, 3, current_semi - qty)   # 更新第3欄 (C:半成品庫存)
                worksheet.update_cell(g_row, 4, current_ready + qty)  # 更新第4欄 (D:可出貨庫存)
                st.success(f"🎉 轉化成功！已將 {qty} 件【{selected_item}】轉換為可出貨狀態！")
                st.rerun()
                
        elif "追加資材" in action:
            worksheet.update_cell(g_row, 3, current_semi + qty)       # 更新第3欄 (C:半成品庫存)
            st.success(f"🎉 登記成功！【{selected_item}】已追加半成品庫存 {qty}。")
            st.rerun()