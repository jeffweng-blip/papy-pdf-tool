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
@st.cache_data 
def load_ini_data():
    ini_filename = 'settings.ini'
    config = configparser.ConfigParser()
    
    default_options = {'items': 'SAKAA57006 三鶯媽祖田, SAKM167005 三鶯AFC, SAKAA53010 環一多元支付'}
    
    # 預設使用者格式：姓名:工號
    default_user = {'payment_method': 'PAPY', 'users': '翁振家:D958, 王大明:D123, 李小華:D456'}
    
    default_checkboxes = {
        'cb1_name': '急件',     'cb1_text': '【備註】：此為急件，請盡速處理。',
        'cb2_name': '附明細',   'cb2_text': '【備註】：已檢附相關明細表。',
        'cb3_name': '需回簽',   'cb3_text': '【備註】：請於確認後簽名回傳。',
        'cb4_name': '已覆核',   'cb4_text': '【備註】：本文件已由主管覆核完畢。',
        'cb5_name': '特殊專案', 'cb5_text': '【備註】：此為特殊專案，請依專案流程辦理。'
    }
    
    if not os.path.exists(ini_filename):
        config['Options'] = default_options
        config['UserInfo'] = default_user
        config['Checkboxes'] = default_checkboxes
        with open(ini_filename, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(ini_filename, encoding='utf-8')
        if 'Checkboxes' not in config:
            config['Checkboxes'] = default_checkboxes
            with open(ini_filename, 'w', encoding='utf-8') as f:
                config.write(f)

    try:
        items_str = config.get('Options', 'items', fallback="找不到選項")
        items_list = [item.strip() for item in items_str.split(',')]
    except:
        items_list = ["資料錯誤"]

    # 解析「姓名:工號」對應表
    users_dict = {}
    try:
        if config.has_option('UserInfo', 'users'):
            users_str = config.get('UserInfo', 'users')
            for pair in users_str.split(','):
                if ':' in pair:
                    name, wid = pair.split(':')
                    users_dict[name.strip()] = wid.strip()
        else:
            # 相容舊版單一格式
            fallback_name = config.get('UserInfo', 'name', fallback='翁振家')
            fallback_wid = config.get('UserInfo', 'work_id', fallback='D958')
            users_dict[fallback_name] = fallback_wid
    except:
        users_dict = {'翁振家': 'D958'}

    user_info = {
        'payment': config.get('UserInfo', 'payment_method', fallback="N/A"),
        'users_dict': users_dict
    }
    
    checkbox_data = []
    for i in range(1, 6):
        cb_name = config.get('Checkboxes', f'cb{i}_name', fallback=f'選項{i}')
        cb_text = config.get('Checkboxes', f'cb{i}_text', fallback='')
        checkbox_data.append({'name': cb_name, 'text': cb_text})
        
    return items_list, user_info, checkbox_data

# --- 2. 產生 PDF 的邏輯 ---
def generate_pdf_buffer(selected_option, selected_name, target_work_id, info_data, final_text):
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
        f"姓名：{selected_name}\n"
        f"工號：{target_work_id}\n"
        f"----------------------------------------\n"
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
st.caption("v2.5 - 姓名與工號自動連動")

items_data, info_data, checkbox_data = load_ini_data()

if "details_text" not in st.session_state:
    st.session_state.details_text = ""

# 初始化各個 checkbox 的狀態
for i in range(len(checkbox_data)):
    if f"cb_{i}" not in st.session_state:
        st.session_state[f"cb_{i}"] = False

# Checkbox 變動時的處理
def on_cb_change(cb_key, cb_text):
    current_text = st.session_state.details_text
    if st.session_state[cb_key]: 
        if cb_text not in current_text:
            if current_text.strip():
                st.session_state.details_text = current_text + "\n" + cb_text
            else:
                st.session_state.details_text = cb_text
    else: 
        # 移除文字時處理換行符
        new_text = current_text.replace("\n" + cb_text, "").replace(cb_text, "").strip()
        st.session_state.details_text = new_text

# 清除所有輸入
def clear_all():
    st.session_state.details_text = ""
    for i in range(len(checkbox_data)):
        st.session_state[f"cb_{i}"] = False

col1, col2 = st.columns([1, 1])

with col2: 
    st.subheader("設定與輸入")
    
    selected_option = st.selectbox("專案名稱", items_data)
    
    # 姓名下拉選單
    users_dict = info_data['users_dict']
    selected_name = st.selectbox("選擇姓名", list(users_dict.keys()))
    
    # 自動抓取工號
    current_work_id = users_dict.get(selected_name, "N/A")
    
    st.markdown(f"**付款方式：** {info_data['payment']} &nbsp;&nbsp;|&nbsp;&nbsp; **自動帶入工號：** `{current_work_id}`")
    
    st.text_area("商品細節", height=150, key="details_text")
    
    st.markdown("##### 📌 附加選項 (可複選)")
    
    cb_cols = st.columns(3)
    checked_names = []
    
    for i, cb in enumerate(checkbox_data):
        cb_key = f"cb_{i}"
        is_checked = cb_cols[i % 3].checkbox(
            cb['name'],
            key=cb_key,
            on_change=on_cb_change,
            args=(cb_key, cb['text'])
        )
        if is_checked:
            checked_names.append(cb['name'])

    st.button("🗑️ 清除內容", on_click=clear_all)

with col1: 
    st.subheader("預覽畫面")
    
    final_details = st.session_state.details_text
    preview_content = (
        f"專案：{selected_option}\n"
        f"付款：{info_data['payment']}\n"
        f"姓名：{selected_name}\n"
        f"工號：{current_work_id}\n"
        f"----------------------------------------\n"
        f"細節：\n{final_details}"
    )
    
    st.info(preview_content.replace('\n', '  \n')) 
    st.divider() 
    
    time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    # 檔名加入勾選的標籤名
    if checked_names:
        cb_names_str = "_".join(checked_names)
        pdf_filename = f"{time_str}_{cb_names_str}.pdf"
    else:
        pdf_filename = f"{time_str}.pdf"
    
    pdf_buffer = generate_pdf_buffer(selected_option, selected_name, current_work_id, info_data, final_details)
    
    if pdf_buffer:
        st.download_button(
            label="📥 下載 PDF 檔",
            data=pdf_buffer,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary"
        )
