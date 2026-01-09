import streamlit as st
import google.generativeai as genai
import json

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Quiz Pro", page_icon="🛡️", layout="centered")

# ==============================================================================
# --- ĐOẠN CODE GIAO DIỆN HIỆN ĐẠI (CSS) ---
# Copy và dán đoạn này vào file app.py của bạn
# ==============================================================================
MODERN_UI_STYLES = """
    <style>
    /* 1. Nhúng Font chữ hiện đại (Inter) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* Áp dụng font cho toàn bộ trang web */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* 2. Nền trang web (Gradient nhẹ nhàng) */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* 3. Thẻ chứa câu hỏi (Card UI) */
    .question-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 16px; /* Bo tròn góc */
        box-shadow: 0 8px 20px rgba(0,0,0,0.06); /* Đổ bóng mềm */
        border: 1px solid rgba(255, 255, 255, 0.5); /* Viền mờ */
        margin-bottom: 20px;
        transition: all 0.3s ease; /* Hiệu ứng mượt khi di chuột */
    }
    .question-card:hover {
        transform: translateY(-3px); /* Nổi lên nhẹ khi di chuột vào */
        box-shadow: 0 12px 25px rgba(0,0,0,0.1);
    }
    .question-card h4 {
        color: #2d3436;
        font-weight: 600;
        margin-top: 0;
    }

    /* 4. Nút bấm (Button) đẹp mắt */
    div.stButton > button {
        background: linear-gradient(to right, #6a11cb 0%, #2575fc 100%); /* Màu gradient tím xanh */
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 50px; /* Nút hình con nhộng */
        font-weight: 600;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(106, 17, 203, 0.3);
        transition: all 0.3s ease;
        width: 100%; /* Nút rộng full */
    }
    div.stButton > button:hover {
        transform: scale(1.02); /* Phóng to nhẹ khi di chuột */
        box-shadow: 0 6px 20px rgba(106, 17, 203, 0.5);
        color: #fff;
    }

    /* 5. Khu vực chọn đáp án (Radio) */
    .stRadio {
        background-color: rgba(255,255,255,0.6);
        padding: 15px;
        border-radius: 12px;
        backdrop-filter: blur(5px); /* Hiệu ứng kính mờ */
    }

    /* 6. Hộp kết quả (Đúng/Sai) */
    .result-box {
        padding: 20px;
        border-radius: 12px;
        margin-top: 15px;
        font-weight: 500;
    }
    .correct-box {
        background-color: #d4edda;
        color: #155724;
        border-left: 5px solid #28a745;
    }
    .incorrect-box {
        background-color: #f8d7da;
        color: #721c24;
        border-left: 5px solid #dc3545;
    }
    
    /* Tiêu đề chính */
    h1 {
        color: #2d3436;
        text-align: center;
        font-weight: 700;
    }
    </style>
"""

# Kích hoạt giao diện
st.markdown(MODERN_UI_STYLES, unsafe_allow_html=True)
# ==============================================================================

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
    with col1: num = st.number_input("Số câu:", 1, 60, 5)
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
      # Ví dụ cách dùng trong vòng lặp (Bạn tự sửa vào code của mình):
        for i, q in enumerate(st.session_state.quiz_data):
    # Bọc câu hỏi vào thẻ div có class="question-card"
            st.markdown(f"""
    <div class="question-card">
        <h4>Câu {i+1}: {q['question']}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # (Phần radio button giữ nguyên...)

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



