import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import PyPDF2
import docx
import time
import re 

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

# --- HÀM XỬ LÝ FILE (PHIÊN BẢN FIX LỖI MẠNH NHẤT) ---
def process_file_to_quiz(text_content):
    key = get_api_key()
    if not key: return []
    
    chunks = split_text_into_chunks(text_content)
    all_quizzes = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Debug expander để xem AI trả lời gì nếu lỗi
    debug_box = st.expander("🛠️ Xem chi tiết xử lý (Nếu lỗi thì mở cái này)", expanded=False)
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        for i, chunk in enumerate(chunks):
            status_text.text(f"Đang xử lý phần {i+1}/{len(chunks)}... (AI đang đọc)")
            
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
                
                # In ra log ẩn để debug
                debug_box.write(f"Phần {i+1} AI trả lời: {txt[:200]}...")

                # --- CÁCH TÌM JSON THỦ CÔNG (TRÂU BÒ HƠN REGEX) ---
                # Tìm dấu [ đầu tiên và dấu ] cuối cùng
                start_idx = txt.find("[")
                end_idx = txt.rfind("]")
                
                if start_idx != -1 and end_idx != -1:
                    json_str = txt[start_idx : end_idx+1]
                    batch_questions = json.loads(json_str)
                    
                    if isinstance(batch_questions, list):
                        all_quizzes.extend(batch_questions)
                else:
                    debug_box.warning(f"Phần {i+1}: Không tìm thấy JSON (Mất dấu ngoặc []).")
                    
            except Exception as e:
                debug_box.error(f"Lỗi phần {i}: {e}")
            
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
                    else: st.error("Không tìm thấy câu hỏi nào (Mở mục 'Xem chi tiết xử lý' để xem lỗi).")
                else: st.error("File quá ngắn hoặc lỗi đọc.")

# --- PHẦN LÀM BÀI ---
if st.session_state.quiz_data:
    st.markdown("---")
    with st.form("quiz_form"):
        # Vòng lặp hiển thị câu hỏi
        for i, q in enumerate(st.session_state.quiz_data):
            # 1. Hiển thị nội dung câu hỏi
            st.markdown(f'<div class="question-card"><h4>Câu {i+1}: {q["question"]}</h4></div>', unsafe_allow_html=True)
            
            # 2. Hiển thị các lựa chọn
            st.session_state.user_answers[i] = st.radio(
                "Lựa chọn:", 
                q['options'], 
                key=f"rad_{i}", 
                label_visibility="collapsed"
            )
            st.write("") 

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 3. Nút nộp bài
        submit_btn = st.form_submit_button("🏆 Nộp Bài & Xem Kết Quả")
        
        if submit_btn:
            st.session_state.submitted = True
            
            # Tính điểm
            score = 0
            for i, q in enumerate(st.session_state.quiz_data):
                if st.session_state.user_answers.get(i) == q['correct_answer']: score += 1
            
            total = len(st.session_state.quiz_data)
            time_now = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            ket_qua = "Đậu" if score >= total/2 else "Rớt"

            # Lưu vào Google Sheets
            try:
                # Đóng gói JSON
                json_quiz = json.dumps(st.session_state.quiz_data, ensure_ascii=False)
                # Sửa lỗi lưu key answers: chuyển int key sang string
                json_answers = json.dumps({str(k): v for k, v in st.session_state.user_answers.items()}, ensure_ascii=False)

                new_data = pd.DataFrame([{
                    "Thời gian": time_now, "Điểm số": f"{score}/{total}", "Kết quả": ket_qua,
                    "Chi tiết đề": json_quiz, "Bài làm": json_answers
                }])
                
                conn.reset()
                existing = conn.read(worksheet="Sheet1", usecols=list(new_data.keys()), ttl=0)
                updated = pd.concat([existing, new_data], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated)
                st.success("✅ Đã lưu kết quả vĩnh viễn!")
            except Exception as e:
                st.error(f"Lỗi lưu Sheet (Kiểm tra lại tên cột trong Sheet): {e}")
            
            st.rerun()

# --- HIỂN THỊ KẾT QUẢ ---
if st.session_state.submitted:
    st.markdown("---")
    st.subheader("📊 Kết Quả")
    score = 0
    total = len(st.session_state.quiz_data)
    for i, q in enumerate(st.session_state.quiz_data):
        u_ans = st.session_state.user_answers.get(i)
        is_correct = (u_ans == q['correct_answer'])
        if is_correct: score += 1
        
        with st.expander(f"Câu {i+1}: {q['question']} {'✅' if is_correct else '❌'}"):
            if is_correct:
                 st.markdown(f"<div class='result-box correct-box'>Bạn chọn: {u_ans} (Chính xác)</div>", unsafe_allow_html=True)
            else:
                 st.markdown(f"<div class='result-box incorrect-box'>Bạn chọn: {u_ans}<br>Đáp án đúng: <b>{q['correct_answer']}</b></div>", unsafe_allow_html=True)
            st.write(f"💡 Giải thích: {q['explanation']}")
            
    st.progress(score/total)

# --- XEM LẠI LỊCH SỬ ---
st.divider()
st.subheader("📜 Kho Lưu Trữ Bài Thi")
try:
    df_history = conn.read(worksheet="Sheet1", ttl=0)
    st.dataframe(df_history[["Thời gian", "Điểm số", "Kết quả"]], use_container_width=True)
    
    st.write("### 🔍 Xem lại bài cũ")
    if not df_history.empty and "Thời gian" in df_history.columns:
        options = df_history["Thời gian"].tolist()
        selected_time = st.selectbox("Chọn bài thi:", options[::-1])
        
        if st.button("Mở lại bài thi này"):
            record = df_history[df_history["Thời gian"] == selected_time].iloc[0]
            if "Chi tiết đề" in record and "Bài làm" in record:
                old_quiz = json.loads(record["Chi tiết đề"])
                old_ans = json.loads(record["Bài làm"])
                
                st.info(f"Đang xem: {selected_time} - Điểm: {record['Điểm số']}")
                for i, q in enumerate(old_quiz):
                    u_ans = old_ans.get(str(i))
                    is_correct = (u_ans == q['correct_answer'])
                    with st.expander(f"Câu {i+1}: {q['question']} {'✅' if is_correct else '❌'}"):
                        st.write(f"**Bạn chọn:** {u_ans}")
                        st.write(f"**Đáp án:** {q['correct_answer']}")
except Exception as e:
    st.info("Chưa có dữ liệu.")

