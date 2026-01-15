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

# --- HÀM CẮT VĂN BẢN (GIẢM SIZE ĐỂ TRÁNH TRUNCATE) ---
# Đã giảm từ 15000 xuống 4000 để đảm bảo AI đủ chỗ viết giải thích
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
        model = genai.GenerativeModel('gemini-2.5
