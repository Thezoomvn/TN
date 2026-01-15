import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import PyPDF2
import docx
import time
import re # <--- BẮT BUỘC CÓ ĐỂ SỬA LỖI TÌM CÂU HỎI

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Quiz Pro", page_icon="🛡️", layout="centered")

# --- KẾT NỐI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HÀM ĐỌC FILE TẢI LÊN ---
def read_uploaded_file(uploaded_file):
    try:
        text = ""
        # 1. Nếu là PDF
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
            
        # 2. Nếu là Word (.docx)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
            
        # 3. Nếu là Text (.txt)
        elif uploaded_file.type == "text/plain":
            return str(uploaded_file.read(), "utf-8")
        else:
            return None
    except Exception as e:
        return None

# --- HÀM CẮT VĂN BẢN (CHUNKING) ---
def split_text_into_chunks(text, chunk_size=15000):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            last_newline = text.rfind('\n', start, end)
            if last_newline != -1:
                end = last_newline
        chunks.append(text[start:end])
        start = end
    return chunks

# --- HÀM LẤY KEY ---
def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return ""

# --- HÀM GỌI GEMINI TẠO QUIZ (THEO CHỦ ĐỀ) ---
def generate_quiz(topic, num, diff):
    key = get_api_key()
    if not key: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        prompt = f"""
        Tạo {num} câu trắc nghiệm JSON về "{topic}", độ khó {diff}.
        Output Format: [{{"question": "...", "options": ["A. ", "B. "], "correct_answer": "...", "explanation": "..."}}]
        Dùng $$ cho Latex.
        """
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except:
        return []

# --- HÀM XỬ LÝ FILE (PHIÊN BẢN SỬA LỖI & MẠNH MẼ) ---
def process_file_to_quiz(text_content):
    key = get_api_key()
    if not key: return []
    
    chunks = split_text_into_chunks(text_content)
    all_quizzes = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        for i, chunk in enumerate(chunks):
            status_text.text(f"Đang xử lý phần {i+1}/{len(chunks)}... (AI đang đọc)")
            
            # Prompt ngắn gọn, hiệu quả
            prompt = f"""
            Extract multiple-choice questions from the text below into a JSON Array.
            TEXT:
            ---
            {chunk}
            ---
            RULES:
            1. Output strictly a JSON list: [{{"question": "...", "options": [...], "correct_answer": "...", "explanation": "..."}}]
            2. If no questions found, return [].
            """
            
            try:
                response = model.generate_content(prompt)
                txt = response.text
                
                # --- THUẬT TOÁN TÌM JSON (REGEX) ---
                # Giúp tìm đúng đoạn JSON dù AI có nói nhảm ở đầu/cuối
                match = re.search(r'\[.*\]', txt, re.DOTALL)
                if match:
                    json_str = match.group()
                    batch_questions = json.loads(json_str)
                    if isinstance(batch_questions, list):
                        all_quizzes.extend(batch_questions)
            except Exception as e:
                print(f"Lỗi phần {i}: {e}")
            
            progress_bar.progress((i + 1) / len(chunks))
            time.sleep(1)
            
        status_text.empty()
        progress_bar.empty()
        return all_quizzes

    except Exception as e:
        st.error(f"Lỗi hệ thống: {str(e)}")
        return []

# --- GIAO DIỆN DARK MODE ---
MODERN_UI_STYLES = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #e0e6ed !important; }
    .stApp { background-color: #0f1116; }
    .question-card { background-color: #1e2330; padding: 25px; border-radius: 15px; border: 1px solid #2e3440; margin-bottom: 25px; }
    .question-card h4 { color: #ffffff !important; margin-top: 0; }
    .stRadio p { color: #c0caf5 !important; font-size: 16px; }
    div.stButton > button { background: linear-gradient(90deg, #7928ca, #ff0080); color: white !important; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; }
    .result-box { padding: 15px; border-radius: 8px; margin-top: 15px; }
    .correct-box { background-color: #052c16; color: #75b798; border: 1px solid #0f5132; }
    .incorrect-box { background-color: #2c0b0e; color: #ea868f; border: 1px solid #842029; }
    h1 { color: #ffffff !important; text-align: center; }
    </style>
"""
st.markdown(MODERN_UI_STYLES, unsafe_allow_html=True)

# --- KHỞI TẠO STATE ---
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {}
if "submitted" not in st.session_state: st.session_state.submitted = False

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️HNNTĐN")

with st.sidebar:
    st.header("Trạng thái hệ thống")
    if "GEMINI_API_KEY" in st.secrets:
        st.success("✅ Đã kết nối API Key.")
    else:
        st.error("❌ Chưa tìm thấy API Key.")
    
    st.divider()
    tab1, tab2 = st.tabs(["🤖 AI Tự Tạo", "📂 Tải File"])
    
    with tab1:
        topic = st.text_area("Chủ đề:", height=100)
        col1, col2 = st.columns(2)
        with col1: num = st.number_input("Số câu:", 1, 500, 5)
        with col2: diff = st.selectbox("Độ khó:", ["Dễ","Trung bình","Khó"])
        if st.button("🚀 Bắt đầu thi (AI)"):
            if not topic: st.warning("Thiếu chủ đề!")
            else:
                st.session_state.submitted = False
                st.session_state.user_answers = {}
                data = generate_quiz(topic, num, diff)
                if data: 
                    st.session_state.quiz_data = data
                    st.rerun()

    with tab2:
        st.info("Hỗ trợ: PDF, Word, TXT")
        uploaded_file = st.file_uploader("Chọn tài liệu:", type=['txt', 'pdf', 'docx'])
        if uploaded_file and st.button("📝 Tạo đề từ File"):
            with st.spinner("Đang đọc file..."):
                raw_text = read_uploaded_file(uploaded_file)
                if raw_text and len(raw_text) > 50:
                    file_quiz_data = process_file_to_quiz(raw_text)
                    if file_quiz_data:
                        st.session_state.submitted = False
                        st.session_state.user_answers = {}
                        st.session_state.quiz_data = file_quiz_data
                        st.success(f"Đã tạo {len(file_quiz_data)} câu hỏi!")
                        st.rerun()
                    else: st.error("Không tìm thấy câu hỏi nào.")
                else: st.error("File quá ngắn hoặc lỗi đọc.")

# --- PHẦN LÀM BÀI ---
if st.session_state.quiz_data:
    st.markdown("---")
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="question-card"><h4>Câu {i+1}: {q["question"]}</h4></div>',
