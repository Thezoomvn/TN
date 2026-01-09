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
# ==============================================================================
# --- GIAO DIỆN DARK MODE (CHẾ ĐỘ TỐI) ---
# Bảo vệ mắt, êm dịu, tương phản tốt
# ==============================================================================
MODERN_UI_STYLES = """
    <style>
    /* 1. Nhúng Font chữ hiện đại */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #e0e6ed !important; /* Chữ màu trắng xám nhạt (dịu mắt) */
    }

    /* 2. Nền trang web (Màu Xám Than Đậm - Deep Charcoal) */
    .stApp {
        background-color: #0f1116; 
    }

    /* 3. Thẻ câu hỏi (Màu nền sáng hơn nền web một chút để nổi bật) */
    .question-card {
        background-color: #1e2330; /* Xanh đen nhạt */
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #2e3440; /* Viền xám mờ */
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); /* Bóng đổ tối */
        margin-bottom: 25px;
    }
    
    .question-card h4 {
        color: #ffffff !important; /* Tiêu đề câu hỏi màu trắng tinh */
        font-weight: 600;
        margin-top: 0;
    }

    /* 4. Ô chọn đáp án (Radio) */
    .stRadio p {
        color: #c0caf5 !important; /* Màu chữ đáp án hơi xanh nhạt */
        font-size: 16px;
    }
    /* Làm sáng ô radio khi di chuột vào */
    .stRadio > div:hover {
        background-color: #292e42;
        border-radius: 8px;
    }

    /* 5. Nút bấm (Gradient Neon - Nổi bật trên nền tối) */
    div.stButton > button {
        background: linear-gradient(90deg, #7928ca, #ff0080); /* Tím hồng Neon */
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px rgba(255, 0, 128, 0.5); /* Hiệu ứng phát sáng */
    }

    /* 6. Hộp kết quả (Tối ưu cho nền đen) */
    .result-box {
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
        font-weight: 500;
    }
    .correct-box {
        background-color: #052c16; /* Nền xanh lá cực đậm */
        color: #75b798; /* Chữ xanh lá sáng */
        border: 1px solid #0f5132;
    }
    .incorrect-box {
        background-color: #2c0b0e; /* Nền đỏ cực đậm */
        color: #ea868f; /* Chữ đỏ hồng sáng */
        border: 1px solid #842029;
    }
    
    /* 7. Các khung nhập liệu (Input) */
    .stTextInput input, .stTextArea textarea, .stSelectbox div {
        background-color: #1a1b26 !important;
        color: white !important;
        border: 1px solid #414868 !important;
    }

    /* Tiêu đề chính */
    h1 {
        color: #ffffff !important;
        text-align: center;
        text-shadow: 0 0 10px rgba(255,255,255,0.1);
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
# --- HÀM GỌI GEMINI (ĐÃ SỬA LỖI JSON LATEX) ---
def generate_quiz(topic, num, diff):
    key = get_api_key()
    if not key:
        st.error("Chưa cấu hình API Key trong Secrets!")
        return []
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
        
        # --- CÂU LỆNH ĐÃ SỬA ĐỔI ĐỂ KHẮC PHỤC LỖI \ESCAPE ---
        prompt = f"""
        Bạn là giáo viên Toán/Lý/Hóa giỏi. Hãy tạo {num} câu trắc nghiệm JSON về "{topic}", độ khó {diff}.
        
        QUY TẮC QUAN TRỌNG VỀ ĐỊNH DẠNG (BẮT BUỘC TUÂN THỦ):
        1.  Output phải là JSON hợp lệ.
        2.  VỚI CÔNG THỨC TOÁN (LATEX):
            - Bắt buộc đặt trong dấu $$.
            - **QUAN TRỌNG:** Vì đây là định dạng JSON, bạn phải dùng **HAI DẤU GẠCH CHÉO** (Double Backslash) cho các lệnh LaTeX.
            - Ví dụ SAI: "$\frac{{1}}{{2}}$" (Sẽ gây lỗi JSON)
            - Ví dụ ĐÚNG: "$\\frac{{1}}{{2}}$" (Phải có 2 dấu \\)
            - Tương tự: $\\sqrt{{x}}$, $x^2$, $\\pi$, $\\approx$.

        OUTPUT FORMAT (JSON Array):
        [
            {{
                "question": "Nội dung câu hỏi (Ví dụ: Tính giá trị của biểu thức $\\frac{{a}}{{b}}$)...",
                "options": ["A. $x^2$", "B. $\\sqrt{{x}}$", "C. $100\\%$", "D. $\\pi$"],
                "correct_answer": "Đáp án đúng (Copy y nguyên text)",
                "explanation": "Giải thích chi tiết (Dùng 2 dấu gạch chéo cho LaTeX: $\\Delta = b^2 - 4ac$)."
            }}
        ]
        """
        
        response = model.generate_content(prompt)
        
        # Xử lý trường hợp Gemini vẫn trả về lỗi (Phòng ngừa)
        text_response = response.text
        # Nếu model lỡ trả về 1 dấu \, ta thử replace thủ công một số lệnh phổ biến (Mẹo fix nhanh)
        ifInvalid = False
        try:
            return json.loads(text_response)
        except:
            # Nếu lỗi, thử sửa chuỗi string thủ công trước khi parse
            text_response = text_response.replace(r'\frac', r'\\frac') \
                                         .replace(r'\sqrt', r'\\sqrt') \
                                         .replace(r'\times', r'\\times') \
                                         .replace(r'\cdot', r'\\cdot')
            return json.loads(text_response)

    except Exception as e:
        st.error(f"Lỗi khi tạo câu hỏi: {str(e)}")
        # In ra text gốc để debug nếu cần
        # st.text(response.text) 
        return []

# --- GIAO DIỆN ---
st.title("🛡️HNNTĐN")

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
    with col2: diff = st.selectbox("Độ khó:", ["Dễ","Trung bình","Khó"])
    
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









