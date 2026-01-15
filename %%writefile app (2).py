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

# --- HÀM LỌC DỮ LIỆU LỖI ---
def clean_quiz_data(data):
    """Lọc bỏ câu hỏi lỗi và đảm bảo luôn có trường explanation"""
    valid_data = []
    for q in data:
        # 1. Kiểm tra đủ trường bắt buộc
        if "question" in q and "options" in q and "correct_answer" in q:
            # 2. Nếu thiếu explanation thì tự điền mặc định
            if "explanation" not in q or not q["explanation"]:
                q["explanation"] = "AI không tìm thấy giải thích cụ thể."
            valid_data.append(q)
    return valid_data

# --- HÀM ĐỌC FILE TẢI LÊN ---
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
    except Exception as e:
        return None

# --- HÀM CẮT VĂN BẢN ---
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

# --- HÀM TẠO QUIZ TỪ CHỦ ĐỀ ---
def generate_quiz(topic, num, diff):
    key = get_api_key()
    if not key: return []
    try:
        genai.configure(api_key=key)
        # --- SỬA CHUẨN VỀ 1.5 FLASH (Bản này Free Tier rất cao) ---
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        prompt = f"""
        Tạo {num} câu trắc nghiệm JSON về "{topic}", độ khó {diff}.
        Format: [{{"question": "...", "options": ["A. ", "B. "], "correct_answer": "...", "explanation": "..."}}]
        """
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        return clean_quiz_data(data)
    except:
        return []

# --- HÀM XỬ LÝ FILE (ĐÃ FIX MODEL CHUẨN 1.5 FLASH) ---
def process_file_to_quiz(text_content):
    key = get_api_key()
    if not key: return []
    
    # Cắt nhỏ file
    chunks = split_text_into_chunks(text_content, chunk_size=4000)
    all_quizzes = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    debug_box = st.expander("🛠️ Xem chi tiết xử lý (Debug)", expanded=False)
    
    try:
        genai.configure(api_key=key)
        # --- CHẮC CHẮN SỬ DỤNG GEMINI 1.5 FLASH ---
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        for i, chunk in enumerate(chunks):
            status_text.text(f"Đang xử lý phần {i+1}/{len(chunks)}... (AI đang phân tích)")
            
            prompt = f"""
            Task: Extract multiple-choice questions from the text below into a JSON Array.
            TEXT: --- {chunk} ---
            
            RULES:
            1. Output strictly JSON list: [{{"question": "...", "options": [...], "correct_answer": "...", "explanation": "..."}}]
            2. "explanation": Explain based on the text. IMPORTANT: DO NOT use double quotes (") inside the explanation string, use single quotes (') instead.
            3. If no questions found, return [].
            """
            try:
                # Thử gọi API
                response = model.generate_content(prompt)
                txt = response.text
                
                # --- LOGIC CỨU HỘ JSON ---
                try:
                    start = txt.find('[')
                    end = txt.rfind(']')
                    if start != -1 and end != -1:
                        json_str = txt[start : end+1]
                        batch = json.loads(json_str)
                        all_quizzes.extend(batch)
                    else:
                        raise ValueError("Không tìm thấy ngoặc vuông []")
                        
                except Exception as parse_error:
                    # Cứu dữ liệu nếu bị cắt cụt
                    debug_box.warning(f"Phần {i+1} bị lỗi format, đang thử sửa tự động...")
                    try:
                        start = txt.find('[')
                        if start != -1:
                            json_str_fix = txt[start:] 
                            json_str_fix = json_str_fix.strip().rstrip(',').rstrip('}') 
                            json_str_fix += "}]"
                            batch = json.loads(json_str_fix)
                            all_quizzes.extend(batch)
                            debug_box.success(f"-> Đã cứu thành công phần {i+1}!")
                    except:
                        debug_box.error(f"Phần {i+1} lỗi nặng, bỏ qua.")

            except Exception as e:
                # Xử lý lỗi Quota (429) thông minh hơn
                if "429" in str(e):
                    debug_box.warning(f"Google báo bận, đang chờ 5 giây để thử lại phần {i+1}...")
                    time.sleep(5) # Nghỉ 5s
                    try:
                        response = model.generate_content(prompt) # Thử lại lần 2
                        txt = response.text
                        start = txt.find('[')
                        end = txt.rfind(']')
                        if start != -1 and end != -1:
                            batch = json.loads(txt[start : end+1])
                            all_quizzes.extend(batch)
                    except:
                         debug_box.error(f"Vẫn lỗi sau khi thử lại: {e}")
                else:
                    debug_box.error(f"Lỗi kết nối phần {i}: {e}")
            
            progress_bar.progress((i + 1) / len(chunks))
            
            # --- QUAN TRỌNG: THỜI GIAN NGHỈ ---
            # 1.5 Flash cho phép 15 request/phút -> Nghỉ 4s là an toàn tuyệt đối
            time.sleep(4) 
            
        status_text.empty()
        progress_bar.empty()
        
        cleaned_quizzes = clean_quiz_data(all_quizzes)
        return cleaned_quizzes

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
                        st.success(f"Đã tạo {len(file_quiz_data)} câu hỏi kèm lời giải!")
                        st.rerun()
                    else: st.error("Không tìm thấy câu hỏi nào (Kiểm tra mục Debug bên dưới để xem lỗi).")
                else: st.error("File lỗi hoặc quá ngắn.")

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
            
    if total > 0:
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
                    correct_val = q.get('correct_answer', 'N/A')
                    explanation = q.get('explanation', 'Không có lời giải thích.')
                    
                    is_correct = (u_ans == correct_val)
                    
                    with st.expander(f"Câu {i+1}: {q['question']} {'✅' if is_correct else '❌'}"):
                        st.write(f"**Bạn chọn:** {u_ans}")
                        st.write(f"**Đáp án:** {correct_val}")
                        st.info(f"💡 **Giải thích:** {explanation}")
except Exception as e:
    st.info("Chưa có dữ liệu.")

