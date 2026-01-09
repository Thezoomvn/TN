import streamlit as st
import google.generativeai as genai
import json

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Quiz Pro", page_icon="🛡️", layout="centered")

# --- CSS GIAO DIỆN ---
st.markdown("""
    <style>
    .stApp {background-color: #f0f2f6;}
    .success-box {padding:15px; background:#d1e7dd; color:#0f5132; border-radius:10px; margin-bottom:10px;}
    .error-box {padding:15px; background:#f8d7da; color:#842029; border-radius:10px; margin-bottom:10px;}
    .question-card {background:white; padding:20px; border-radius:15px; box-shadow:0 2px 5px rgba(0,0,0,0.05); margin-bottom:20px;}
    </style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO STATE ---
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {}
if "submitted" not in st.session_state: st.session_state.submitted = False

# --- HÀM LẤY KEY AN TOÀN TỪ SECRETS ---
def get_api_key():
    # Ưu tiên lấy từ Secrets (Cấu hình trên Streamlit Cloud)
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    # Nếu chạy cục bộ hoặc chưa cấu hình, trả về rỗng
    return ""

# --- HÀM GỌI GEMINI ---
def generate_quiz(topic, num, diff):
    key = get_api_key()
    if not key:
        st.error("Chưa cấu hình API Key trong Secrets!")
        return []
    
    try:
        genai.configure(api_key=key)
        # Dùng model chuẩn 1.5 flash
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        
        prompt = f"""Tạo {num} câu trắc nghiệm JSON về "{topic}", độ khó {diff}. 
        Format: [{{ "question": "...", "options": ["A","B"], "correct_answer": "A", "explanation": "..." }}]"""
        
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Lỗi: {str(e)}")
        return []

# --- GIAO DIỆN ---
st.title("🛡️ Trắc Nghiệm (Secure Mode)")

with st.sidebar:
    st.header("Trạng thái hệ thống")
    
    # Kiểm tra xem đã kết nối được với Két sắt Secrets chưa
    if "GEMINI_API_KEY" in st.secrets:
        st.success("✅ Đã kết nối API Key bảo mật.")
        st.caption("Key đang được bảo vệ trong Streamlit Secrets.")
    else:
        st.error("❌ Chưa tìm thấy API Key.")
        st.info("Vui lòng vào Settings -> Secrets trên Streamlit để thêm Key.")
    
    st.divider()
    topic = st.text_area("Chủ đề:", height=100)
    col1, col2 = st.columns(2)
    with col1: num = st.number_input("Số câu:", 1, 20, 5)
    with col2: diff = st.selectbox("Độ khó:", ["Dễ", "Khó"])
    
    if st.button("🚀 Bắt đầu thi"):
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Vui lòng cấu hình Key trước!")
        elif not topic:
            st.warning("Thiếu chủ đề!")
        else:
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            data = generate_quiz(topic, num, diff)
            if data: st.session_state.quiz_data = data

# --- PHẦN LÀM BÀI ---
if st.session_state.quiz_data:
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"<div class='question-card'><b>Câu {i+1}:</b> {q['question']}</div>", unsafe_allow_html=True)
            st.session_state.user_answers[i] = st.radio("Chọn:", q['options'], key=f"rad_{i}", label_visibility="collapsed")
        
        if st.form_submit_button("Nộp bài"):
            st.session_state.submitted = True
            st.rerun()

# --- KẾT QUẢ ---
if st.session_state.submitted:
    score = 0
    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_answers.get(i)
        is_correct = (user_choice == q['correct_answer'])
        if is_correct: score += 1
        
        with st.expander(f"Xem giải thích câu {i+1} ({'Đúng' if is_correct else 'Sai'})"):
            st.info(f"Giải thích: {q['explanation']}")

    st.metric("Kết quả:", f"{score}/{len(st.session_state.quiz_data)}")
