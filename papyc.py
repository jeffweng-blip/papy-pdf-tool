import streamlit as st
import configparser
import os
import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

# --- 1. 讀取 INI 設定檔邏輯 (新增 Checkbox 設定) ---
@st.cache_data 
def load_ini_data():
    ini_filename = 'settings.ini'
    config = configparser.ConfigParser()
    
    # 預設的基本設定
    default_options = {'items': 'SAKAA57006 三鶯媽祖田, SAKM167005 三鶯AFC, SAKAA53010 環一多元支付'}
    default_user = {'payment_method': 'PAPY', 'name': '翁振家', 'work_id': 'D958'}
    
    # 預設的 5 個 Checkbox 設定 (名稱與對應文字)
    default_checkboxes = {
        'cb1_name': '急件',     'cb1_text': '【備註】：此為急件，請盡速處理。',
        'cb2_name': '附明細',   'cb2_text': '【備註】：已檢附相關明細表。',
        'cb3_name': '需回簽',   'cb3_text': '【備註】：請於確認後簽名回傳。',
        'cb4_name': '已覆核',   'cb4_text': '【備註】：本文件已由主管覆核完畢。',
        'cb5_name': '特殊專案', 'cb5_text': '【備註】：此為特殊專案，請依專案流程辦理。'
    }
    
    # 檢查檔案是否存在，不存在則建立全套預設值
    if not os.path.exists(ini_filename):
        config['Options'] = default_options
        config['UserInfo'] = default_user
        config['Checkboxes'] = default_checkboxes
        with open(ini_filename, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(ini_filename, encoding='utf-8')
        # 如果舊檔案沒有 Checkboxes 區塊，幫它補上去並存檔
        if 'Checkboxes' not in config:
            config['Checkboxes'] = default_checkboxes
            with open(ini_filename, 'w', encoding='utf-8') as f:
                config.write(f)

    # 讀取專案與使用者資訊
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
    
    # 讀取 Checkbox 資訊 (裝成一個 List)
    checkbox_data = []
    for i in range(1, 6):
        cb_name = config.get('Checkboxes', f'cb{i}_name', fallback=f'選項{i}')
        cb_text = config.get('Checkboxes', f'cb{i}_text', fallback='')
        checkbox_data.append({'name': cb_name, 'text': cb_text})
        
    return items_list, user_info, checkbox_data

# --- 2. 產生 PDF 的邏輯 ---
def generate_pdf_buffer(selected_option, info_data, final_text):
    font_path = r"C:\Windows\Fonts\msjh.ttc"  
    if not os.path.exists(font_path):
        font_path = "msjh.ttc" 
        
    if not os.path.exists(font_path):
         st.error("找不到中文字型檔！")
         return None

    pdfmetrics.registerFont(TTFont('MyFont', font_path))
    
    content = (
        f"專案：{selected_option}\n"
        f"付款：{info_data['payment']}\n"
        f"姓名：{info_data['name']}\n"
        f"工號：{info_data['work_id']}\n"
        f"-----------------------------------------------------\n"
        f"細節：\n{final_text}"
    )

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont('MyFont', 26) 
    
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
    buffer.seek(0)
    return buffer

# --- 3. Streamlit 網頁介面設計 ---
st.set_page_config(page_title="PAPY輸出文字", page_icon="📄")

st.title("📄 PAPY輸出文字")
st.caption("v2.1 - 支援快速勾選標籤")

# 載入資料
items_data, info_data, checkbox_data = load_ini_data()

# 初始化 session_state
if "details_text" not in st.session_state:
    st.session_state.details_text = ""

col1, col2 = st.columns([1, 1])

with col2: 
    st.subheader("設定與輸入")
    
    selected_option = st.selectbox("專案名稱", items_data)
    
    st.markdown(f"**付款方式：** {info_data['payment']} | **姓名：** {info_data['name']} | **工號：** {info_data['work_id']}")
    
    input_text = st.text_area("商品細節", value=st.session_state.details_text, height=150)
    
    # ---------------- 新增 Checkbox 區塊 ----------------
    st.markdown("##### 📌 附加選項 (可複選)")
    
    # 將五個選項排成一排 (如果覺得太擠，可以把 columns(5) 改成 columns(3) 或換行)
    cb_cols = st.columns(5)
    checked_items = []  # 用來收集被勾選的項目
    
    for i, cb in enumerate(checkbox_data):
        # 建立 Checkbox
        is_checked = cb_cols[i].checkbox(cb['name'], key=f"cb_{i}")
        if is_checked:
            checked_items.append(cb)
    # --------------------------------------------------

    if st.button("🗑️ 清除內容"):
        st.session_state.details_text = ""
        st.rerun()
    else:
        st.session_state.details_text = input_text

with col1: 
    st.subheader("預覽畫面")
    
    # 組合最終文字：自己打的細節 + 勾選產生的文字
    final_details = st.session_state.details_text
    
    # 如果有勾選東西，就把對應的文字加到細節下方
    if checked_items:
        added_text = "\n".join([item['text'] for item in checked_items])
        if final_details.strip(): # 如果原本有打字，加個空行分隔
            final_details += f"\n\n{added_text}"
        else:
            final_details += added_text

    preview_content = (
        f"專案：{selected_option}\n"
        f"付款：{info_data['payment']}\n"
        f"姓名：{info_data['name']}\n"
        f"工號：{info_data['work_id']}\n"
        f"----------------------------------------\n"
        f"細節：\n{final_details}"
    )
    
    st.info(preview_content.replace('\n', '  \n')) 
    st.divider() 
    
    # ---------------- 檔名處理邏輯 ----------------
    time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # 如果有勾選，檔名就加上勾選的名稱 (例如: 20260502-105300_急件_已覆核.pdf)
    if checked_items:
        cb_names_str = "_".join([item['name'] for item in checked_items])
        pdf_filename = f"{time_str}_{cb_names_str}.pdf"
    else:
        pdf_filename = f"{time_str}.pdf"
    # ----------------------------------------------
    
    pdf_buffer = generate_pdf_buffer(selected_option, info_data, final_details)
    
    if pdf_buffer:
        st.download_button(
            label="📥 下載 PDF 檔",
            data=pdf_buffer,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary"
        )
