import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="AI Quiz Pro", page_icon="🛡️", layout="centered")

# --- KẾT NỐI GOOGLE SHEETS (MỚI THÊM) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GIAO DIỆN DARK MODE (CHẾ ĐỘ TỐI) ---
MODERN_UI_STYLES = """
    <style>
    /* 1. Nhúng Font chữ hiện đại */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #e0e6ed !important;
    }

    /* 2. Nền trang web */
    .stApp { background-color: #0f1116; }

    /* 3. Thẻ câu hỏi */
    .question-card {
        background-color: #1e2330;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #2e3440;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        margin-bottom: 25px;
    }
    
    .question-card h4 {
        color: #ffffff !important;
        font-weight: 600;
        margin-top: 0;
    }

    /* 4. Ô chọn đáp án */
    .stRadio p { color: #c0caf5 !important; font-size: 16px; }
    .stRadio > div:hover { background-color: #292e42; border-radius: 8px; }

    /* 5. Nút bấm */
    div.stButton > button {
        background: linear-gradient(90deg, #7928ca, #ff0080);
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px rgba(255, 0, 128, 0.5);
    }

    /* 6. Hộp kết quả */
    .result-box { padding: 15px; border-radius: 8px; margin-top: 15px; font-weight: 500; }
    .correct-box { background-color: #052c16; color: #75b798; border: 1px solid #0f5132; }
    .incorrect-box { background-color: #2c0b0e; color: #ea868f; border: 1px solid #842029; }
    
    /* 7. Input */
    .stTextInput input, .stTextArea textarea, .stSelectbox div {
        background-color: #1a1b26 !important;
        color: white !important;
        border: 1px solid #414868 !important;
    }

    /* Tiêu đề chính */
    h1 { color: #ffffff !important; text-align: center; text-shadow: 0 0 10px rgba(255,255,255,0.1); }
    </style>
"""
st.markdown(MODERN_UI_STYLES, unsafe_allow_html=True)

# --- KHỞI TẠO STATE ---
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {}
if "submitted" not in st.session_state: st.session_state.submitted = False

# --- HÀM LẤY KEY ---
def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return ""

# --- HÀM GỌI GEMINI ---
def generate_quiz(topic, num, diff):
    key = get_api_key()
    if not key:
        st.error("Chưa cấu hình API Key trong Secrets!")
        return []
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        
        prompt = f"""
        Bạn là giáo viên Toán/Lý/Hóa giỏi. Hãy tạo {num} câu trắc nghiệm JSON về "{topic}", độ khó {diff}.
        
        QUY TẮC QUAN TRỌNG VỀ ĐỊNH DẠNG (BẮT BUỘC TUÂN THỦ):
        1. Output phải là JSON hợp lệ.
        2. VỚI CÔNG THỨC TOÁN (LATEX):
            - Bắt buộc đặt trong dấu $$.
            - Dùng HAI DẤU GẠCH CHÉO (Double Backslash) cho lệnh LaTeX.
            - Ví dụ ĐÚNG: "$\\frac{{1}}{{2}}$"
        
        OUTPUT FORMAT (JSON Array):
        [
            {{
                "question": "Nội dung câu hỏi...",
                "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
                "correct_answer": "Đáp án đúng (Copy y nguyên text)",
                "explanation": "Giải thích chi tiết..."
            }}
        ]
        """
        response = model.generate_content(prompt)
        text_response = response.text
        
        try:
            return json.loads(text_response)
        except:
            text_response = text_response.replace(r'\frac', r'\\frac').replace(r'\sqrt', r'\\sqrt').replace(r'\times', r'\\times').replace(r'\cdot', r'\\cdot')
            return json.loads(text_response)

    except Exception as e:
        st.error(f"Lỗi khi tạo câu hỏi: {str(e)}")
        return []

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️HNNTĐN")

with st.sidebar:
    st.header("Trạng thái hệ thống")
    if "GEMINI_API_KEY" in st.secrets:
        st.success("✅ Đã kết nối API Key.")
    else:
        st.error("❌ Chưa tìm thấy API Key.")
    
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
if st.session_state.quiz_data:
    st.markdown("---")
    
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown('<div class="question-card">', unsafe_allow_html=True)
            st.markdown(f"#### Câu {i+1}: {q['question']}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.session_state.user_answers[i] = st.radio(
                "Lựa chọn của bạn:", 
                q['options'], 
                key=f"rad_{i}", 
                label_visibility="collapsed"
            )
            st.write("") 

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- NÚT NỘP BÀI & XỬ LÝ LƯU GOOGLE SHEETS ---
        submit_btn = st.form_submit_button("🏆 Nộp Bài & Xem Kết Quả")
        
        if submit_btn:
            st.session_state.submitted = True
            
            # 1. Tính toán điểm số để lưu
            save_score = 0
            for i, q in enumerate(st.session_state.quiz_data):
                u_ans = st.session_state.user_answers.get(i)
                if u_ans == q['correct_answer']: 
                    save_score += 1
            
            total_q = len(st.session_state.quiz_data)
            time_now = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
            ket_qua = "Đậu" if save_score >= total_q/2 else "Rớt"

            # 2. Tạo dữ liệu mới
            new_data = pd.DataFrame([{
                "Thời gian": time_now,
                "Điểm số": f"{save_score}/{total_q}",
                "Kết quả": ket_qua
            }])

            # 3. Gửi lên Google Sheet
            try:
                existing_data = conn.read(worksheet="Sheet1", usecols=list(new_data.keys()), ttl=0)
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("✅ Đã lưu kết quả vĩnh viễn!")
            except Exception as e:
                st.error(f"⚠️ Không lưu được lịch sử (Kiểm tra lại kết nối Sheet): {e}")
            
            st.rerun()

# --- HIỂN THỊ KẾT QUẢ CHI TIẾT ---
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

# --- HIỂN THỊ LỊCH SỬ TỪ GOOGLE SHEET (CUỐI TRANG) ---
st.divider()
st.subheader("📜 Lịch sử làm bài (Lưu vĩnh viễn)")

try:
    # ttl=0 để luôn load dữ liệu mới nhất
    df_history = conn.read(worksheet="Sheet1", ttl=0)
    # Sắp xếp để mới nhất lên đầu (nếu muốn)
    # df_history = df_history.iloc[::-1] 
    st.dataframe(df_history, use_container_width=True)
except:
    st.info("Chưa có dữ liệu hoặc chưa kết nối Google Sheet.")
