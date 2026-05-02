import streamlit as st
import configparser
import os
import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

# --- 1. 讀取 INI 設定檔邏輯 ---
@st.cache_data # 使用 cache 避免每次重新整理網頁都重讀檔案
def load_ini_data():
    ini_filename = 'settings.ini'
    config = configparser.ConfigParser()
    
    if not os.path.exists(ini_filename):
        config['Options'] = {
            'items': 'SAKAA57006 三鶯媽祖田, SAKM167005 三鶯AFC, SAKAA53010 環一多元支付'
        }
        config['UserInfo'] = {
            'payment_method': 'PAPY',
            'name': '翁振家',
            'work_id': 'D958'
        }
        with open(ini_filename, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(ini_filename, encoding='utf-8')

    try:
        items_str = config.get('Options', 'items', fallback="找不到選項")
        items_list = [item.strip() for item in items_str.split(',')]
    except:
        items_list = ["資料錯誤"]

    user_info = {
        'payment': config.get('UserInfo', 'payment_method', fallback="N/A"),
        'name': config.get('UserInfo', 'name', fallback="N/A"),
        'work_id': config.get('UserInfo', 'work_id', fallback="N/A")
    }
    return items_list, user_info

# --- 2. 產生 PDF 的邏輯 (改為在記憶體中產生，方便網頁下載) ---
def generate_pdf_buffer(selected_option, info_data, input_text):
    # 準備字型 (注意：如果要上傳到雲端，字型檔必須放在同一個資料夾)
    font_path = r"C:\Windows\Fonts\msjh.ttc"  # Windows 本機測試用
    if not os.path.exists(font_path):
        font_path = "msjh.ttc" # 雲端備用路徑 (請將字型檔複製到程式同資料夾)
        
    if not os.path.exists(font_path):
         st.error("找不到中文字型檔！如果您要部署到雲端，請將 msjh.ttc 放在與 app.py 相同的資料夾中。")
         return None

    pdfmetrics.registerFont(TTFont('MyFont', font_path))
    
    # 組合預覽文字
    content = (
        f"專案：{selected_option}\n"
        f"付款：{info_data['payment']}\n"
        f"姓名：{info_data['name']}\n"
        f"工號：{info_data['work_id']}\n"
        f"-----------------------------------------------------\n"
        f"細節：\n{input_text}"
    )

    # 建立一個記憶體緩衝區來存放 PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont('MyFont', 26) 
    
    # 逐行寫入 PDF
    x_position = 50   
    y_position = 780  
    line_spacing = 35 
    
    for line in content.split('\n'):
        c.drawString(x_position, y_position, line)
        y_position -= line_spacing  
        
        if y_position < 50:
            c.showPage()
            c.setFont('MyFont', 26) 
            y_position = 780
            
    c.save()
    buffer.seek(0) # 將指標移回檔案開頭
    return buffer

# --- 3. Streamlit 網頁介面設計 ---
st.set_page_config(page_title="PAPY輸出文字", page_icon="📄")

st.title("📄 PAPY輸出文字")
st.caption("v2.0 - 網頁版")

# 載入資料
items_data, info_data = load_ini_data()

# 初始化 session_state (用來處理清除文字框的功能)
if "details_text" not in st.session_state:
    st.session_state.details_text = ""

# 介面佈局：分為左右兩欄
col1, col2 = st.columns([1, 1])

with col2: # 右半部 (輸入區)
    st.subheader("設定與輸入")
    
    # 下拉選單
    selected_option = st.selectbox("專案名稱", items_data)
    
    # 顯示使用者資訊 (Markdown 格式)
    st.markdown(f"""
    **付款方式：** {info_data['payment']} | **姓名：** {info_data['name']} | **工號：** {info_data['work_id']}
    """)
    
    # 商品細節輸入
    input_text = st.text_area("商品細節", value=st.session_state.details_text, height=200)
    
    # 清除按鈕
    if st.button("🗑️ 清除內容"):
        # Streamlit 無法直接清空 text_area，需透過重新載入頁面來清空 (透過 key 或實驗性功能，這裡用簡單的重載體驗)
        st.session_state.details_text = ""
        st.rerun()
    else:
        # 即時將輸入文字存入 session_state
        st.session_state.details_text = input_text

with col1: # 左半部 (預覽與輸出)
    st.subheader("預覽畫面")
    
    preview_content = (
        f"專案：{selected_option}\n"
        f"付款：{info_data['payment']}\n"
        f"姓名：{info_data['name']}\n"
        f"工號：{info_data['work_id']}\n"
        f"----------------------------------------\n"
        f"細節：\n{st.session_state.details_text}"
    )
    
    # 用一個有底色的框框顯示預覽
    st.info(preview_content.replace('\n', '  \n')) 
    
    st.divider() # 分隔線
    
    # 產生 PDF 按鈕與下載按鈕
    time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    pdf_filename = f"{time_str}.pdf"
    
    # 呼叫產生 PDF 的函式
    pdf_buffer = generate_pdf_buffer(selected_option, info_data, st.session_state.details_text)
    
    if pdf_buffer:
        st.download_button(
            label="📥 下載 PDF 檔",
            data=pdf_buffer,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary"
        )