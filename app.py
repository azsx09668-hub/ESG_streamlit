import io

import pandas as pd
import requests
import streamlit as st
import urllib3

# ---------------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------------
st.set_page_config(page_title="TWSE 公開資料檢視器", page_icon="📊", layout="wide")

DEFAULT_URL = "https://mopsfin.twse.com.tw/opendata/t187ap46_O_1.csv"  # 換連結


# ---------------------------------------------------------------------------
# 資料讀取（快取 1 小時，避免每次互動都重新下載）
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="資料下載中...")
def load_data(url: str) -> tuple[pd.DataFrame, bool]:
    """下載 CSV 並回傳 (DataFrame, 是否略過 SSL 驗證)。"""
    skipped_ssl = False
    try:
        response = requests.get(url, timeout=30)
    except requests.exceptions.SSLError:
        # 部分政府/交易所網站憑證在雲端環境會驗證失敗，退而求其次略過驗證
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(url, verify=False, timeout=30)
        skipped_ssl = True

    response.raise_for_status()

    # 直接在記憶體中解析，不寫入磁碟（Streamlit Cloud 檔案系統為暫存性質）
    df = pd.read_csv(io.BytesIO(response.content), encoding="utf-8-sig")  # 繁體中文
    df = df.dropna()
    return df, skipped_ssl


# ---------------------------------------------------------------------------
# 介面
# ---------------------------------------------------------------------------
st.title("📊 TWSE 公開資料檢視器")

with st.sidebar:
    st.header("設定")
    url = st.text_input("CSV 連結", value=DEFAULT_URL)
    if st.button("🔄 重新下載資料"):
        load_data.clear()
        st.rerun()

try:
    df, skipped_ssl = load_data(url)
except requests.exceptions.RequestException as e:
    st.error(f"下載資料失敗：{e}")
    st.stop()
except Exception as e:
    st.error(f"解析資料失敗：{e}")
    st.stop()

if skipped_ssl:
    st.warning("SSL 憑證驗證失敗，已略過驗證下載資料（verify=False）。")

# 關鍵字搜尋：在所有欄位中尋找
keyword = st.text_input("🔍 關鍵字搜尋（搜尋所有欄位）")
if keyword:
    mask = df.astype(str).apply(
        lambda col: col.str.contains(keyword, case=False, na=False)
    ).any(axis=1)
    view_df = df[mask]
else:
    view_df = df

col1, col2 = st.columns(2)
col1.metric("總筆數（已去除空值）", f"{len(df):,}")
col2.metric("目前顯示筆數", f"{len(view_df):,}")

st.dataframe(view_df, use_container_width=True, hide_index=True)

# 下載按鈕（utf-8-sig 讓 Excel 開啟中文不亂碼）
csv_bytes = view_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ 下載目前結果 (CSV)",
    data=csv_bytes,
    file_name="data01.csv",
    mime="text/csv",
)
