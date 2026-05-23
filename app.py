import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 網頁基礎設定
st.set_page_config(page_title="Seeds Hope 多品類庫存管理", page_icon="💐", layout="centered")

# ─── 🔐 全新功能：安全登入機制 ───
def check_password():
    # 檢查是否已經登入過
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # 如果還沒登入，顯示密碼輸入框
    if not st.session_state["password_correct"]:
        st.title("🔒 Seeds Hope 系統登入")
        st.info("💡 請輸入專屬密碼以操作庫存系統")
        
        pwd = st.text_input("專屬密碼", type="password", placeholder="請輸入密碼...")
        
        if st.button("解鎖系統", type="primary", use_container_width=True):
            # 比對 secrets.toml 裡面設定的密碼
            if pwd == st.secrets.get("app_password", ""):
                st.session_state["password_correct"] = True
                st.rerun() # 密碼正確，重新整理網頁載入下方系統
            else:
                st.error("❌ 密碼錯誤，請重新輸入！")
        
        # 讓程式停在這裡，不往下顯示庫存系統
        st.stop()

# 執行密碼檢查
#check_password()

# ─── 🔓 密碼正確後，才會執行以下原本的庫存系統 ───
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
        df = pd.DataFrame(data)
        if not df.empty:
            # 確保不會讀到空白的幽靈行
            df = df[df["款式名稱"].astype(str).str.strip() != ""]
            for col in ["半成品庫存", "可出貨庫存", "累積銷售量"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"❌ 讀取資料表結構錯誤，請確認欄位標題是否正確。錯誤回報: {e}")
        st.stop()

df = load_data()

# ─── 注入自定義 CSS 樣式 ───
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

required_cols = ["種類", "款式名稱", "半成品庫存", "可出貨庫存", "累積銷售量"]
if not df.empty and not all(c in df.columns for c in required_cols):
    st.error("❌ Google 試算表欄位不正確！請確認第一行包含：種類、款式名稱、半成品庫存、可出貨庫存、累積銷售量")
    st.stop()

# ---------------------------------------------------------
# 【核心功能】主動線：切換商品種類
# ---------------------------------------------------------
st.subheader("📁 請選擇商品大類")
if not df.empty:
    existing_categories = [c for c in df["種類"].unique() if str(c).strip()]
    if not existing_categories:
        existing_categories = ["花束"]
else:
    existing_categories = ["花束"]

selected_category = st.radio("當前檢視種類：", existing_categories, horizontal=True)
filtered_df = df[df["種類"] == selected_category] if not df.empty else pd.DataFrame()

# ---------------------------------------------------------
# 2. 即時看板展示
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
                <div class="data-node"><span class="node-icon">🌿</span><span class="node-label">半成品</span><span class="node-value semi-val">{semi}</span></div>
                <div class="data-node"><span class="node-icon">📦</span><span class="node-label">{alert_icon}可出貨</span><span class="node-value ready-val">{ready}</span></div>
                <div class="data-node"><span class="node-icon">🔥</span><span class="node-label">已銷售</span><span class="node-value sales-val">{sales}</span></div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info(f"💡 目前【{selected_category}】分類下暫無任何品項，請在下方新增。")

st.divider()

# ---------------------------------------------------------
# 3. 現場進銷貨與轉化操作介面
# ---------------------------------------------------------
st.subheader("🔄 庫存異動與管理維護")

action = st.radio(
    "步驟 1：請選擇動作", 
    [
        "🛒 現場銷售（扣可出貨）", 
        "🔧 完工包裝（半成品 ➔ 可出貨）", 
        "🌿 追加資材（加半成品）", 
        "📤 其他扣除/出貨（不計入銷售）", 
        "✏️ 銷售錯誤修正（減銷售 ➔ 還可出貨）", 
        "✨ 新增全新款式",
        "🖊️ 修改項目名稱", 
        "🗑️ 刪除舊款式（謹慎使用）" 
    ], 
    horizontal=True
)

deduct_target = None
new_name_input = None
confirm_delete = False

if action == "✨ 新增全新款式":
    st.info("💡 小提醒：建立「新種類」時，必須同時輸入該種類的「第一項商品名稱」才會成功建立喔！")
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
    selected_item = st.selectbox(f"步驟 2:: 選擇【{selected_category}】品項", filtered_df["款式名稱"].tolist())
    
    if "其他扣除" in action:
        deduct_target = st.radio("步驟 2-1：您要扣除哪一種庫存？", ["📦 可出貨庫存", "🌿 半成品庫存"], horizontal=True)
    
    elif "修改項目名稱" in action:
        new_name_input = st.text_input("步驟 3：請輸入「新」的款式名稱", placeholder="例如：改名後的新款式")
        
    elif "刪除舊款式" in action:
        st.warning(f"⚠️ 警告：您即將永久刪除【{selected_category}】中的【{selected_item}】！此操作無法復原。")
        confirm_delete = st.checkbox("我確認要永久刪除此項目", value=False)

    if action not in ["✨ 新增全新款式", "🖊️ 修改項目名稱", "🗑️ 刪除舊款式（謹慎使用）"]:
        qty = st.number_input("步驟 3：輸入執行數量", min_value=1, value=1, step=1)
        # 💡 新增：自動偵測半成品數量，若不足則跳出提示與確認勾選框
        force_convert = False
        if "完工包裝" in action and not filtered_df.empty:
            match_condition = (filtered_df["款式名稱"] == selected_item)
            if not filtered_df[match_condition].empty:
                current_semi_display = int(filtered_df[match_condition]["半成品庫存"].values[0])
                if current_semi_display < qty:
                    st.warning(f"⚠️ 提示：目前半成品僅剩 {current_semi_display}。")
                    force_convert = st.checkbox("☑️ 半成品為0，故非經由半成品完成（確認後直接新增成品）", value=False)

st.write("")

# 動態改變按鈕文字，避免報錯
button_text = "🚨 確認永久刪除" if "刪除" in action else "🚀 確認送出更新"

if st.button(button_text, type="primary", use_container_width=True):
    
    # ─── 狀況 A：新增全新款式 ───
    if action == "✨ 新增全新款式":
        if not target_category:
            st.error("❌ 種類名稱不能為空！")
            st.stop()
        cleaned_name = new_item_name.strip()
        if not cleaned_name:
            st.error("❌ 請務必填寫「商品款式名稱」！")
            st.stop()
            
        if not df.empty and cleaned_name in df[df["種類"] == target_category]["款式名稱"].tolist():
            st.error(f"❌ 在【{target_category}】分類中，款式【{cleaned_name}】已經存在。")
        else:
            # 確保寫入試算表的庫存數是標準 Python int
            worksheet.append_row([target_category, cleaned_name, int(init_semi), int(init_ready), 0])
            st.success(f"🎉 成功新增商品：【{target_category}】 ➔ 【{cleaned_name}】！")
            st.rerun()
            
    # ─── 狀況 B：庫存異動與管理 ───
    else:
        match_condition = (df["種類"] == selected_category) & (df["款式名稱"] == selected_item)
        p_idx = df[match_condition].index[0]
        
        # 💡 核心安全修正：將 g_row 轉換為標準 Python 內建整數
        g_row = int(p_idx) + 2  
        
        current_semi = int(df.loc[p_idx, "半成品庫存"])
        current_ready = int(df.loc[p_idx, "可出貨庫存"])
        current_sales = int(df.loc[p_idx, "累積銷售量"])

        # ─── 管理功能 ───
        if "修改項目名稱" in action:
            cleaned_new_name = new_name_input.strip()
            if not cleaned_new_name: st.error("❌ 新名稱不能為空！")
            elif cleaned_new_name == selected_item: st.info("💡 新名稱與舊名稱相同，無需修改。")
            elif cleaned_new_name in df[df["種類"] == selected_category]["款式名稱"].tolist():
                st.error(f"❌ 分類【{selected_category}】中已存在名為【{cleaned_new_name}】的項目。")
            else:
                worksheet.update_cell(g_row, 2, cleaned_new_name)
                st.success(f"🎉 成功！項目已更名為【{cleaned_new_name}】。")
                st.rerun()

        elif "刪除舊款式" in action:
            if not confirm_delete: st.warning("⚠️ 請先勾選『我確認要永久刪除此項目』後方可送出。")
            else:
                worksheet.delete_rows(g_row) # 這裡傳入標準 Python int，不再報錯
                st.success(f"💥 項目【{selected_item}】及其所有紀錄已永久刪除。")
                st.rerun()

        # ─── 原有的庫存異動邏輯（數值更新全部包裝 int() 確保安全） ───
        elif "現場銷售" in action:
            if current_ready < qty: st.error(f"❌ 庫存不足！可出貨僅剩 {current_ready}。")
            else:
                worksheet.update_cell(g_row, 4, int(current_ready - qty))  
                worksheet.update_cell(g_row, 5, int(current_sales + qty))  
                st.success(f"🎉 登記成功！【{selected_item}】成功售出 {qty}。")
                st.rerun()
                
        elif "完工包裝" in action:
            if current_semi < qty:
                # 判斷是否有勾選強制新增
                if force_convert:
                    # 只增加可出貨成品，不去扣半成品
                    worksheet.update_cell(g_row, 4, int(current_ready + qty))
                    st.success(f"🎉 成功！半成品為0，故非經由半成品完成，已直接新增 {qty} 件成品。")
                    st.rerun()
                else:
                    st.error(f"❌ 轉化失敗！半成品僅剩 {current_semi}。若要強制新增，請勾選上方的確認框。")
            else:
                # 正常轉換：扣除半成品、增加成品
                worksheet.update_cell(g_row, 3, int(current_semi - qty))   
                worksheet.update_cell(g_row, 4, int(current_ready + qty))  
                st.success(f"🎉 轉化成功！已轉換 {qty} 件為可出貨狀態！")
                st.rerun()
                
        elif "追加資材" in action:
            worksheet.update_cell(g_row, 3, int(current_semi + qty))       
            st.success(f"🎉 登記成功！【{selected_item}】追加材料 {qty}。")
            st.rerun()

        elif "其他扣除" in action:
            if "可出貨" in deduct_target:
                if current_ready < qty: st.error(f"❌ 扣除失敗！可出貨庫存僅剩 {current_ready}。")
                else:
                    worksheet.update_cell(g_row, 4, int(current_ready - qty))
                    st.success(f"🎉 成功扣除！已將 {qty} 件移出成品庫存。")
                    st.rerun()
            elif "半成品" in deduct_target:
                if current_semi < qty: st.error(f"❌ 扣除失敗！半成品庫存僅剩 {current_semi}。")
                else:
                    worksheet.update_cell(g_row, 3, int(current_semi - qty))
                    st.success(f"🎉 成功扣除！已將 {qty} 件移出材料庫存。")
                    st.rerun()

        elif "銷售錯誤修正" in action:
            if current_sales < qty: st.error(f"❌ 修正失敗！目前銷售量僅有 {current_sales}。")
            else:
                worksheet.update_cell(g_row, 4, int(current_ready + qty))
                worksheet.update_cell(g_row, 5, int(current_sales - qty))
                st.success(f"🎉 修正成功！錯誤的銷售紀錄已扣除，商品已退還庫存。")
                st.rerun()
