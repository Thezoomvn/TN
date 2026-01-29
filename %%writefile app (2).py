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

# --- HÀM XỬ LÝ JSON THÔNG MINH ---
def parse_json_smart(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                json_str = match.group()
                return json.loads(json_str)
            except:
                pass
    return []

# --- HÀM LỌC DỮ LIỆU ---
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
def generate_quiz(topic, num
