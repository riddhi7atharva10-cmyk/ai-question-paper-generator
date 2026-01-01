import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
import tempfile
import os

# ================= CONFIG =================
API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

BASE_DIR = os.path.dirname(__file__)
FONT_REG = os.path.join(BASE_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "DejaVuSans-Bold.ttf")

# ================= AI =================
def generate_ai(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    return r.json()["choices"][0]["message"]["content"].strip()

# ================= PROMPT =================
def build_prompt(qtype, topics, num_q, marks_q):
    return f"""
Generate ONLY questions.

Rules:
- No headings
- No explanations
- No markdown
- No topic names
- Start strictly as Q1., Q2., etc.
- End each question with ({marks_q} marks)

Question Type: {qtype}
Topics: {topics}
Number of Questions: {num_q}
"""

# ================= PDF =================
def create_pdf(subject, total_marks, exam_time, instructions, content):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.add_font("Reg", "", FONT_REG, uni=True)
    pdf.add_font("Bold", "", FONT_BOLD, uni=True)

    page_width = pdf.w - 2 * pdf.l_margin

    pdf.set_font("Bold", "", 16)
    pdf.cell(0, 10, subject, ln=True, align="C")

    pdf.set_font("Reg", "", 11)
    pdf.cell(page_width / 2, 8, f"Total Marks: {total_marks}", align="L")
    pdf.cell(page_width / 2, 8, f"Time: {exam_time}", ln=True, align="R")

    pdf.ln(5)

    if instructions:
        pdf.set_font("Bold", "", 12)
        pdf.cell(0, 8, "Instructions:", ln=True)
        pdf.set_font("Reg", "", 11)
        pdf.multi_cell(page_width, 7, instructions)
        pdf.ln(3)

    pdf.set_font("Reg", "", 11)
    for line in content.split("\n"):
        pdf.multi_cell(page_width, 7, line)
        pdf.ln(1)

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# ================= UI =================
st.title("📝 Question Paper Generator")

subject = st.text_input("Title")
exam_time = st.text_input("Exam Duration")

instructions = st.text_area("Instructions (optional)")
file = st.file_uploader("Upload CSV (unit, topic)", type="csv")

st.subheader("Question Types")
mcq = st.checkbox("MCQ")
short = st.checkbox("Short Answer")
long = st.checkbox("Long Answer")

mcq_marks = st.number_input("Marks per MCQ", 1, 10, 1)
short_marks = st.number_input("Marks per Short Question", 2, 10, 5)
long_marks = st.number_input("Marks per Long Question", 5, 20, 10)

optional = st.checkbox("Add Optional Questions")
total_marks = st.number_input("Total Marks", min_value=20, step=10)

# ================= GENERATE =================
if st.button("Generate Question Paper"):

    if not subject or not file or not exam_time:
        st.error("Subject, CSV and Exam Time required")
        st.stop()

    df = pd.read_csv(file)
    topics = ", ".join(df["topic"].tolist())

    # ===== SELECTED TYPES =====
    selected = []
    if mcq: selected.append("MCQ")
    if short: selected.append("Short Answer")
    if long: selected.append("Long Answer")

    if not selected:
        st.error("Select at least one question type")
        st.stop()

    # ===== MARKS DISTRIBUTION =====
    distribution = {}

    if len(selected) == 1:
        distribution[selected[0]] = total_marks

    elif len(selected) == 3:
        distribution = {
            "MCQ": 10,
            "Short Answer": 20,
            "Long Answer": total_marks - 30
        }

    elif len(selected) == 2:
        half = total_marks // 2
        distribution[selected[0]] = half
        distribution[selected[1]] = total_marks - half

    paper = ""
    section = ord("A")

    for qtype in selected:

        marks_q = mcq_marks if qtype == "MCQ" else short_marks if qtype == "Short Answer" else long_marks
        section_marks = distribution[qtype]

        num_q = section_marks // marks_q
        total_q = num_q + (2 if optional else 0)

        paper += f"\nSECTION {chr(section)} – {qtype}\n"
        if optional:
            paper += f"Answer any {num_q} questions.\n\n"

        paper += generate_ai(build_prompt(qtype, topics, total_q, marks_q)) + "\n"
        section += 1

    st.subheader("Generated Question Paper")
    st.text(paper)

    pdf = create_pdf(subject, total_marks, exam_time, instructions, paper)
    with open(pdf, "rb") as f:
        st.download_button("⬇ Download PDF", f, "Question_Paper.pdf")
