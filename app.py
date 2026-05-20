import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 網頁基礎設定
st.set_page_config(page_title="Seeds Hope 庫存管理", page_icon="💐", layout="centered")
st.title("💐 Seeds Hope 庫存即時管理系統")

# 1. 初始化 Google Sheets 連線
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # 從 Streamlit Secrets 中讀取 GCP 憑證資訊
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
    # 確保試算表欄位結構正確 [花束款式, 現有庫存, 累積銷售量]
    try:
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except gspread.exceptions.GSpreadException as e:
        st.error(f"❌ 讀取資料表結構錯誤，請確認工作表名稱為『Stock』且欄位標題正確。錯誤回報: {e}")
        st.stop()

df = load_data()

# ---------------------------------------------------------
# 【極致視覺優化關鍵步驟】注入自定義 CSS 樣式
# 從 dark theme 切換到乾燥花氛圍的柔和米白色調，並優化手機卡片佈局
# ---------------------------------------------------------
ST_CSS_STYLE = """
<style>
/* 隱藏預設 metric 標籤，我們手動做漂亮的 */
[data-testid="stMetricLabel"] { display: none; }

/* 定義卡片容器，啟用 Flexbox 讓卡片在手機上自動換行/縱向排列 */
.stock-cards-container {
    display: flex;
    flex-wrap: wrap; 
    gap: 15px; /* 卡片間距 */
    justify-content: center;
    padding: 10px 0;
}

/* 基礎卡片樣式：米白色背景、香檳金邊框、圓角、微妙陰影 */
.stock-card {
    background-color: #fdfaf5; /* 柔軟米白色 */
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05); /* 微妙陰影 */
    width: calc(100% - 20px); /* 手機上幾乎滿寬，留邊距 */
    max-width: 400px; /* 電腦上不要太大 */
    padding: 15px;
    transition: all 0.3s ease;
}

/* 電腦版螢幕 (寬於 768px) 排版優化：每行兩卡 */
@media (min-width: 768px) {
    .stock-card {
        width: calc(50% - 15px); 
    }
}

/* 卡片頭部：款式名稱 */
.card-header {
    font-size: 18px;
    font-weight: bold;
    color: #5d4037; /* 深棕色文字，溫柔且醒目 */
    margin-bottom: 12px;
    text-align: center;
}

/* 卡片主體：資訊排版 */
.card-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

/* 資訊區塊通用樣式 */
.info-block {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
}

/* 圖示 */
.icon {
    font-size: 20px;
}

/* 標籤文字 */
.label {
    color: #8d6e63; /* 灰棕色標籤文字 */
    width: 80px;
}

/* 數據數值 */
.value {
    font-size: 24px;
    font-weight: bold;
}

/* --- 不同欄位數值的顏色暗示 --- */
.stock-block .value { color: #388e3c; } /* 充足庫存使用綠色 */
.sales-block .value { color: #e65100; } /* 累積銷售使用橙色 */

/* 狀態標籤（庫存狀態） */
.status-msg {
    margin-left: auto; /* 推到最右邊 */
    font-size: 14px;
    color: #4caf50;
    padding: 2px 8px;
    border-radius: 4px;
    background-color: #e8f5e9;
}

/* ⚠️ 低庫存特別樣式（醒目突顯） ⚠️ */
.stock-card.low-stock {
    background-color: #fffde7; /* 淡黃色背景警告 */
    border-color: #fff176;
    border-width: 2px;
    box-shadow: 0 4px 8px rgba(255, 235, 59, 0.2);
}

.stock-card.low-stock .stock-block .value {
    color: #f57f17; /* 醒目的橙黃色 */
}

.stock-card.low-stock .status-msg {
    color: #ff9800;
    background-color: #fff3e0;
}

/* 滾動條樣式，讓手機滾動更順手 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background-color: #e0e0e0; border-radius: 10px; }

</style>
"""
# 將自定義 CSS 注入網頁，改變 Streamlit 預設風格
st.markdown(ST_CSS_STYLE, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 即時庫存與銷售看板展示 (全新 HTML/CSS 卡片)
st.subheader("📊 當前市集庫存與熱銷狀態")
if not df.empty:
    # 確保資料表結構正確
    if "現有庫存" not in df.columns or "累積銷售量" not in df.columns:
        st.error("⚠️ 請確認 Google 試算表中是否已包含『現有庫存』與『累積銷售量』的標題欄位！")
        st.stop()

    # 建立一個隱形的 container 放入所有卡片
    st.markdown('<div class="stock-cards-container">', unsafe_allow_html=True)

    for index, row in df.iterrows():
        stock_val = int(row["現有庫存"])
        is_low_stock = stock_val <= 3
        
        # 決定卡片樣式與狀態文字
        low_stock_class = "low-stock" if is_low_stock else ""
        status_msg = "⚠️ 補貨警告" if is_low_stock else "✅ 庫存充足"
        
        # 使用 HTML f-string 動態生成卡片
        card_html = f"""
        <div class="stock-card {low_stock_class}">
            <div class="card-header">【{row['花束款式']}】</div>
            <div class="card-body">
                <div class="info-block stock-block">
                    <span class="icon">📦</span>
                    <span class="label">現有庫存</span>
                    <span class="value">{stock_val}</span>
                    <span class="status-msg">{status_msg}</span>
                </div>
                <div class="info-block sales-block">
                    <span class="icon">🔥</span>
                    <span class="label">累積銷售</span>
                    <span class="value">{int(row['累積銷售量'])}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    # 關閉 container
    st.markdown('</div>', unsafe_allow_html=True)
    
else:
    st.info("💡 目前暫無庫存資料，請先新增款式。")

st.divider()

# ---------------------------------------------------------
# 3. 現場進銷貨與新增品項操作介面 (維持原本穩定邏輯)
st.subheader("🔄 庫存異動與品項管理")

action = st.radio(
    "步驟 1：請選擇動作", 
    ["🛒 現場銷售（扣庫存）", "📦 每日進貨（加庫存）", "✨ 新增全新款式"], 
    horizontal=True
)

if action == "✨ 新增全新款式":
    new_item_name = st.text_input("步驟 2：請輸入新花束款式名稱", placeholder="例如：永恆愛戀 紫色系花束")
    qty = st.number_input("步驟 3：輸入初始進貨庫存", min_value=0, value=10, step=1)
else:
    if df.empty:
        st.warning("⚠️ 目前沒有任何款式可以選擇，請先選擇『新增全新款式』。")
        st.stop()
    selected_item = st.selectbox("步驟 2：選擇花束款式", df["花束款式"].tolist())
    qty = st.number_input("步驟 3：輸入數量", min_value=1, value=1, step=1)

st.write("")
if st.button("🚀 確認送出更新", type="primary", use_container_width=True):
    # 下方維持原本無誤的處理邏輯
    
    if action == "✨ 新增全新款式":
        cleaned_name = new_item_name.strip()
        if not cleaned_name: st.error("❌ 請填寫新花束的款式名稱！")
        elif cleaned_name in df["花束款式"].tolist(): st.error(f"❌ 款式【{cleaned_name}】已經存在於列表中。")
        else:
            worksheet.append_row([cleaned_name, qty, 0])
            st.success(f"🎉 成功新增全新款式：【{cleaned_name}】（初始庫存 {qty} 束）！")
            st.rerun()
            
    else:
        p_idx = df[df["花束款式"] == selected_item].index[0]
        g_row = p_idx + 2  
        current_stock = int(df.loc[p_idx, "現有庫存"])
        current_sales = int(df.loc[p_idx, "累積銷售量"])

        if "銷售" in action:
            if current_stock < qty: st.error(f"❌ 【{selected_item}】庫存不足！無法販售 {qty} 束。")
            else:
                new_stock = current_stock - qty
                new_sales = current_sales + qty
                worksheet.update_cell(g_row, 2, new_stock)  # 更新B欄
                worksheet.update_cell(g_row, 3, new_sales)  # 更新C欄
                st.success(f"🎉 登記成功！【{selected_item}】售出 {qty} 束（累積銷售 {new_sales}）！")
                st.rerun()
        else:
            new_stock = current_stock + qty
            worksheet.update_cell(g_row, 2, new_stock)
            st.success(f"🎉 登記成功！【{selected_item}】進貨 {qty} 束。")
            st.rerun()