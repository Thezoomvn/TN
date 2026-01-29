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

# --- [QUAN TRỌNG] HÀM XỬ LÝ JSON THÔNG MINH ---
def parse_json_smart(text):
    """
    Hàm này dùng thuật toán tìm kiếm (Regex) để lôi đúng đoạn JSON ra khỏi văn bản hỗn độn.
    Bất chấp AI có trả về ```json hay lời dẫn, hàm này đều xử lý được.
    """
    try:
        # 1. Thử parse trực tiếp (trường hợp sạch)
        return json.loads(text)
    except:
        # 2. Nếu lỗi, dùng Regex tìm đoạn bắt đầu bằng [ và kết thúc bằng ]
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                json_str = match.group()
                return json.loads(json_str)
            except:
                pass
    return [] # Trả về rỗng nếu bó tay

# --- HÀM LỌC DỮ LIỆU LỖI ---
def clean_quiz_data(data):
    valid_data = []
    if isinstance(data, list):
        for q in data:
            if "question" in q and "options" in q and "correct_answer" in q:
                if "explanation" not in q or not q["explanation"]:
                    q["explanation"] = "AI không tìm thấy giải thích cụ thể."
                valid_data.append(q)
    return valid_data

# --- HÀM ĐỌC FILE ---
def read_uploaded_file(uploaded_file):
    try:
        text = ""
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        elif uploaded_file.type == "text/plain":
            return str(uploaded_file.read(), "utf-8")
        else:
            return None
    except:
        return None

# --- HÀM CẮT TEXT ---
def split_text_into_chunks(text, chunk_size=4000): 
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

# --- HÀM TẠO QUIZ (TAB 1 - AI TỰ TẠO) ---
def generate_quiz(topic, num, diff):
    key = get_api_key()
    if not key: return []
    try:
        genai.configure(api_key=key)
        # Sử dụng 1.5 Flash (Ổn định nhất)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Act as a Quiz Generator. Create {num} multiple-choice questions about "{topic}", difficulty: {diff}.
        
        STRICT OUTPUT RULES:
        1. Return ONLY a valid JSON Array. No Markdown, no text prefix.
        2. Format: [{{"question": "...", "options": ["A. ", "B. "], "correct_answer": "...", "explanation": "Short explanation"}}]
        3. Language: Vietnamese.
        """
        
        response = model.generate_content(prompt)
        # Dùng hàm thông minh để lấy JSON
        data = parse_json_smart(response.text)
        return clean_quiz_data(data)
    except Exception as e:
        st.error(f"Lỗi tạo câu hỏi: {e}")
        return []

# --- HÀM XỬ LÝ FILE (TAB 2 - FILE UPLOAD) ---
def process_file_to_quiz(text_content):
    key = get_api_key()
    if not key: return []
    
    chunks = split_text_into_chunks(text_content, chunk_size=4000)
    all_quizzes = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    debug_box = st.expander("🛠️ Xem chi tiết xử lý (Debug)", expanded=False)
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        for i, chunk in enumerate(chunks):
            status_text.text(f"Đang xử lý phần {i+1}/{len(chunks)}...")
            
            prompt = f"""
            Extract multiple-choice questions from text into JSON Array.
            TEXT: --- {chunk} ---
            
            RULES:
            1. Output ONLY JSON List: [{{"question": "...", "options": [...], "correct_answer": "...", "explanation": "..."}}]
            2. "explanation": Use single quotes (') inside text.
            3. Language: Vietnamese (Translate if needed).
            """
            try:
                response = model.generate_content(prompt)
                
                # Dùng hàm thông minh để lấy JSON
                batch = parse_json_smart(response.text)
                
                if batch:
                    all_quizzes.extend(batch)
                else:
                    debug_box.warning(f"Phần {i+1}: AI không trả về đúng định dạng JSON.")
                    # debug_box.code(response.text) # Mở dòng này nếu muốn xem AI trả về cái gì

            except Exception as e:
                if "429" in str(e):
                    debug_box.warning(f"Google đang bận (Quota), chờ 10s...")
                    time.sleep(10)
                else:
                    debug_box.error(f"Lỗi phần {i}: {e}")
            
            progress_bar.progress((i + 1) / len(chunks))
            time.sleep(4) # Nghỉ để tránh 429
            
        status_text.empty()
        progress_bar.empty()
        return clean_quiz_data(all_quizzes)

    except Exception as e:
        st.error(f"Lỗi hệ thống: {str(e)}")
        return []

# --- GIAO DIỆN ---
MODERN_UI_STYLES = """
    <style>
    @import url('[https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap)');
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

if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {}
if "submitted" not in st.session_state: st.session_state.submitted = False

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
        with col1: num = st.number_input("Số câu:", 1, 50, 5) # Giảm max xuống 50 cho an toàn
        with col2: diff = st.selectbox("Độ khó:", ["Dễ","Trung bình","Khó"])
        if st.button("🚀 Bắt đầu thi (AI)"):
            if not topic: st.warning("Thiếu chủ đề!")
            else:
                with st.spinner("AI đang soạn đề..."):
                    st.session_state.submitted = False
                    st.session_state.user_answers = {}
                    data = generate_quiz(topic, num, diff)
                    if data: 
                        st.session_state.quiz_data = data
                        st.rerun()
                    else:
                        st.error("AI không trả về kết quả. Hãy thử lại sau ít phút (Lỗi Quota).")

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
                else: st.error("File lỗi.")

# --- PHẦN LÀM BÀI ---
if st.session_state.quiz_data:
    st.markdown("---")
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f'<div class="question-card"><h4>Câu {i+1}: {q["question"]}</h4></div>', unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio("Lựa chọn:", q['options'], key=f"rad_{i}", label_visibility="collapsed")
            st.write("") 

        st.markdown("<br>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button("🏆 Nộp Bài & Xem Kết Quả")
        
        if submit_btn:
            st.session_state.submitted = True
            score = 0
            for i, q in enumerate(st.session_state.quiz_data):
                user_choice = st.session_state.user_answers.get(i)
                correct_val = q.get('correct_answer')
                if correct_val and user_choice == correct_val:
                    score += 1
            
            total = len(st.session_state.quiz_data)
            time_now = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            ket_qua = "Đậu" if total > 0 and score >= total/2 else "Rớt"

            try:
                json_quiz = json.dumps(st.session_state.quiz_data, ensure_ascii=False)
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
                st.error(f"Lỗi lưu Sheet: {e}")
            st.rerun()

# --- HIỂN THỊ KẾT QUẢ ---
if st.session_state.submitted:
    st.markdown("---")
    st.subheader("📊 Kết Quả")
    score = 0
    total = len(st.session_state.quiz_data)
    for i, q in enumerate(st.session_state.quiz_data):
        u_ans = st.session_state.user_answers.get(i)
        correct_val = q.get('correct_answer', 'N/A')
        explanation = q.get('explanation', 'Không có lời giải thích.')
        is_correct = (u_ans == correct_val)
        if is_correct: score += 1
        with st.expander(f"Câu {i+1}: {q['question']} {'✅' if is_correct else '❌'}"):
            if is_correct:
                 st.markdown(f"<div class='result-box correct-box'>Bạn chọn: {u_ans} (Chính xác)</div>", unsafe_allow_html=True)
            else:
                 st.markdown(f"<div class='result-box incorrect-box'>Bạn chọn: {u_ans}<br>Đáp án đúng: <b>{correct_val}</b></div>", unsafe_allow_html=True)
            st.info(f"💡 **Giải thích:** {explanation}")
    if total > 0: st.progress(score/total)


