import streamlit as st
import google.generativeai as genai
import json

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Quiz Pro", page_icon="🛡️", layout="centered")

# ==============================================================================
# --- ĐOẠN CODE GIAO DIỆN HIỆN ĐẠI (CSS) ---
# Copy và dán đoạn này vào file app.py của bạn
# ==============================================================================
# ==============================================================================
# --- GIAO DIỆN TƯƠNG PHẢN CAO (HIGH CONTRAST) ---
# Dễ đọc, rõ ràng, sắc nét
# ==============================================================================
MODERN_UI_STYLES = """
    <style>
    /* 1. Nhúng Font chữ Inter (ưu tiên nét đậm 600) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #000000 !important; /* Bắt buộc chữ màu ĐEN tuyệt đối */
    }

    /* 2. Nền trang web (Màu sáng nhẹ để dịu mắt nhưng vẫn tôn chữ) */
    .stApp {
        background-color: #f0f2f6;
    }

    /* 3. Thẻ câu hỏi (Nền Trắng Tinh - Chữ Đen Đậm) */
    .question-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        border: 2px solid #000000; /* Viền đen bao quanh cho rõ */
        box-shadow: 4px 4px 0px #000000; /* Hiệu ứng bóng cứng (Retro) rất dễ nhìn */
        margin-bottom: 25px;
    }
    
    .question-card h4 {
        color: #000000 !important;
        font-weight: 800 !important; /* Chữ siêu đậm */
        font-size: 20px !important;
        line-height: 1.5;
    }

    /* 4. Ô chọn đáp án (Radio) */
    .stRadio p {
        font-size: 18px !important; /* Tăng cỡ chữ đáp án */
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* 5. Nút bấm (Màu đen - Chữ trắng -> Tương phản cực cao) */
    div.stButton > button {
        background-color: #000000 !important; /* Nút màu đen */
        color: #ffffff !important; /* Chữ trắng */
        border: 2px solid #000000;
        padding: 12px 30px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 16px;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #333333 !important; /* Di chuột vào thì xám đi chút */
        transform: translateY(-2px);
    }

    /* 6. Hộp kết quả */
    .result-box {
        padding: 20px;
        border-radius: 8px;
        margin-top: 15px;
        font-weight: bold;
        color: #000000; /* Chữ đen trong hộp kết quả */
        border: 2px solid #000000;
    }
    .correct-box {
        background-color: #a3ffac; /* Xanh lá sáng */
    }
    .incorrect-box {
        background-color: #ffadad; /* Đỏ sáng */
    }
    
    /* Tiêu đề chính */
    h1 {
        color: #000000 !important;
        text-transform: uppercase;
        text-align: center;
        font-weight: 900;
        letter-spacing: 2px;
    }
    </style>
"""

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
# --- 5. KHUNG LÀM BÀI (Dán vào cuối file) ---
if st.session_state.quiz_data:
    st.markdown("---")
    
    # Mở Form
    with st.form("quiz_form"):
        # Vòng lặp hiện câu hỏi
        for i, q in enumerate(st.session_state.quiz_data):
            # Hiển thị câu hỏi dạng thẻ (Card)
            st.markdown(f"""
            <div class="question-card">
                <h4>Câu {i+1}: {q['question']}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Hiện ô chọn đáp án
            st.session_state.user_answers[i] = st.radio(
                "Lựa chọn của bạn:", 
                q['options'], 
                key=f"rad_{i}", 
                label_visibility="collapsed"
            )
            st.write("") # Khoảng cách cho thoáng

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- ĐÂY LÀ CÁI NÚT BẠN ĐANG THIẾU ---
        # Nó phải nằm TRONG form (thụt vào 1 tab), nhưng NGOÀI vòng lặp for
        submit_btn = st.form_submit_button("🏆 Nộp Bài & Xem Kết Quả")
        
        if submit_btn:
            st.session_state.submitted = True
            st.rerun()

# --- 6. KẾT QUẢ ---
if st.session_state.submitted:
    st.markdown("---")
    st.subheader("📊 Kết Quả Phân Tích")
    
    score = 0
    total = len(st.session_state.quiz_data)
    
    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_answers.get(i)
        is_correct = (user_choice == q['correct_answer'])
        if is_correct: score += 1
        
        with st.expander(f"Câu {i+1}: {q['question']} {'✅' if is_correct else '❌'}"):
            if is_correct:
                st.markdown(f"<div class='result-box correct-box'>Chính xác! Bạn chọn: {user_choice}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='result-box incorrect-box'>Sai rồi!<br>Bạn chọn: {user_choice}<br>Đáp án đúng: <b>{q['correct_answer']}</b></div>", unsafe_allow_html=True)
            
            st.info(f"💡 Giải thích: {q['explanation']}")

    st.progress(score / total)
    if score == total:
        st.balloons()
        st.markdown(f"<h2 style='text-align:center; color:#28a745;'>Xuất sắc! {score}/{total}</h2>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 style='text-align:center;'>Bạn đạt {score}/{total} điểm</h3>", unsafe_allow_html=True)




