import streamlit as st
import google.generativeai as genai
import json

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Quiz Master", page_icon="🎓", layout="centered")

# ==========================================
# ⚠️ CẤU HÌNH API KEY CỦA BẠN Ở ĐÂY ⚠️
# Dán key của bạn vào giữa dấu ngoặc kép bên dưới
# Ví dụ: FIXED_API_KEY = "AIzaSy..."
FIXED_API_KEY = "AIzaSyCOJwl3rojppSYj6k8NW9j6R9S7Sv3baR4"
# ==========================================

# --- CSS TÙY CHỈNH (GIAO DIỆN ĐẸP) ---
st.markdown("""
    <style>
    .stRadio p {font-size: 16px !important;}
    .success-msg {
        padding: 15px; border-radius: 10px;
        background-color: #d4edda; color: #155724;
        border: 1px solid #c3e6cb; margin-top: 10px;
    }
    .error-msg {
        padding: 15px; border-radius: 10px;
        background-color: #f8d7da; color: #721c24;
        border: 1px solid #f5c6cb; margin-top: 10px;
    }
    .explanation {
        margin-top: 10px; padding: 15px;
        background-color: #e2e3e5; border-radius: 10px;
        border-left: 5px solid #383d41; font-style: italic;
    }
    </style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO SESSION STATE ---
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# --- HÀM GỌI GEMINI API ---
def get_quiz_from_gemini(api_key, topic, num_questions, difficulty):
    try:
        genai.configure(api_key=api_key)

        # Cấu hình trả về JSON
        generation_config = {
            "temperature": 0.9,
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)

        prompt = f"""
        Đóng vai một giáo viên giỏi. Hãy tạo một bài trắc nghiệm về chủ đề: "{topic}".
        - Số lượng: {num_questions} câu.
        - Độ khó: {difficulty}.
        - Ngôn ngữ: Tiếng Việt.

        YÊU CẦU OUTPUT LÀ MỘT DANH SÁCH JSON (Array of Objects) với cấu trúc:
        [
            {{
                "question": "Nội dung câu hỏi?",
                "options": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
                "correct_answer": "Đáp án đúng (Copy y nguyên từ options)",
                "explanation": "Giải thích chi tiết tại sao đáp án này đúng và các đáp án khác sai."
            }}
        ]
        """

        with st.spinner('🤖 Gemini đang soạn đề và viết lời giải...'):
            response = model.generate_content(prompt)
            return json.loads(response.text)

    except Exception as e:
        st.error(f"Lỗi kết nối API: {str(e)}")
        return []

# --- GIAO DIỆN SIDEBAR (CẤU HÌNH) ---

   # --- GIAO DIỆN SIDEBAR (CẤU HÌNH) ---
with st.sidebar:
    st.title("⚙️ Cấu Hình")

    # --- PHẦN XỬ LÝ API KEY AN TOÀN (CHỐNG F12) ---
    # Kiểm tra xem Key cứng có hợp lệ không
    has_fixed_key = len(FIXED_API_KEY) > 10

    if has_fixed_key:
        # TRƯỜNG HỢP 1: Đã có Key trong code
        # -> Gán trực tiếp, KHÔNG tạo ô nhập liệu (text_input)
        # -> Key không bao giờ được gửi xuống trình duyệt
        api_key = FIXED_API_KEY
        st.success("✅ Đã kích hoạt API Key bản quyền.")
        st.info("Key được bảo mật an toàn trên Server (F12 không thể thấy).")
    else:
        # TRƯỜNG HỢP 2: Chưa có Key -> Mới hiện ô nhập để người dùng tự điền
        api_key = st.text_input("Nhập Gemini API Key:", type="password")
        st.caption("Lấy key miễn phí tại [Google AI Studio](https://aistudio.google.com/)")
    # ----------------------------------

    st.divider()

    topic = st.text_area("Chủ đề hoặc nội dung:", placeholder="VD: Thì hiện tại đơn, Lịch sử VN, hoặc paste một đoạn văn bản...")

    col1, col2 = st.columns(2)
    with col1:
        num_q = st.number_input("Số câu:", 1, 50, 5)
    with col2:
        diff = st.selectbox("Độ khó:", ["Dễ", "Trung bình", "Khó", "Cực khó"])

    if st.button("🚀 Tạo Đề Thi", use_container_width=True):
        if not api_key:
            st.warning("Vui lòng nhập API Key hoặc điền vào trong code!")
        elif not topic:
            st.warning("Vui lòng nhập chủ đề!")
        else:
            # Reset trạng thái cũ
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            # Lấy dữ liệu mới
            data = get_quiz_from_gemini(api_key, topic, num_q, diff)
            if data:
                st.session_state.quiz_data = data
                st.session_state.submitted = False # Reset lại trạng thái nộp bài khi tạo đề mới
                st.success(f"Đã tạo {len(data)} câu hỏi thành công!")

# --- GIAO DIỆN CHÍNH (LÀM BÀI) ---
st.title("📝 Trắc Nghiệm Kiến Thức")

if not st.session_state.quiz_data:
    if len(FIXED_API_KEY) > 10:
        st.info("👈 Hãy nhập chủ đề và bấm 'Tạo Đề Thi' (Key đã có sẵn).")
    else:
        st.info("👈 Hãy nhập API Key và Chủ đề để bắt đầu.")
else:
    # Form làm bài
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.subheader(f"Câu {i+1}: {q['question']}")

            # Lưu lựa chọn vào session_state
            st.session_state.user_answers[i] = st.radio(
                "Chọn đáp án:",
                q['options'],
                key=f"radio_{i}",
                index=None, # Mặc định không chọn gì
                label_visibility="collapsed"
            )
            st.markdown("---")

        # Nút nộp bài
        submitted = st.form_submit_button("✅ Nộp Bài & Xem Kết Quả")
        if submitted:
            st.session_state.submitted = True

    # --- PHẦN CHẤM ĐIỂM & BÀI SỬA ---
    if st.session_state.submitted:
        st.header("📊 Kết Quả Chi Tiết")
        score = 0
        total = len(st.session_state.quiz_data)

        for i, q in enumerate(st.session_state.quiz_data):
            user_choice = st.session_state.user_answers.get(i)
            correct_answer = q['correct_answer']

            with st.expander(f"Câu {i+1}: {q['question']}", expanded=True):
                # Kiểm tra đúng sai
                if user_choice == correct_answer:
                    score += 1
                    st.markdown(f"""<div class="success-msg">
                        <b>✅ Chính xác!</b> Bạn chọn: {user_choice}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="error-msg">
                        <b>❌ Sai rồi!</b><br>
                        Bạn chọn: {user_choice if user_choice else 'Chưa chọn'}<br>
                        👉 <b>Đáp án đúng:</b> {correct_answer}
                    </div>""", unsafe_allow_html=True)

                # Hiển thị giải thích (Bài sửa)
                st.markdown(f"""<div class="explanation">
                    💡 <b>Giải thích:</b> {q['explanation']}
                </div>""", unsafe_allow_html=True)

        # Tổng kết điểm
        final_score = round((score / total) * 10, 1)
        st.metric(label="Điểm số của bạn", value=f"{final_score}/10", delta=f"Đúng {score}/{total} câu")

        if score == total:

            st.balloons()

