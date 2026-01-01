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
from fpdf import FPDF
import tempfile

def create_pdf(subject, total_marks, exam_time, instructions, content):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ===== FONTS =====
    pdf.add_font("Reg", "", FONT_REG, uni=True)
    pdf.add_font("Bold", "", FONT_BOLD, uni=True)

    page_width = pdf.w - 2 * pdf.l_margin

    # ===== HEADER =====
    pdf.set_font("Bold", "", 16)
    pdf.cell(0, 10, str(subject), ln=True, align="C")
    pdf.ln(2)

    pdf.set_font("Reg", "", 11)
    pdf.cell(page_width / 2, 8, f"Total Marks: {total_marks}", align="L")
    pdf.cell(page_width / 2, 8, f"Time: {exam_time}", ln=True, align="R")

    pdf.ln(4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.l_margin, pdf.get_y())
    pdf.ln(6)

    # ===== INSTRUCTIONS =====
    if instructions:
        pdf.set_font("Bold", "", 12)
        pdf.cell(0, 8, "Instructions:", ln=True)

        pdf.set_font("Reg", "", 11)
        pdf.multi_cell(page_width, 7, str(instructions))
        pdf.ln(5)

    # ===== CONTENT =====
    pdf.set_font("Reg", "", 11)

    for line in str(content).split("\n"):
        line = str(line).strip()

        if not line:
            pdf.ln(4)
            continue

        # SECTION heading
        if line.upper().startswith("SECTION"):
            pdf.ln(3)
            pdf.set_font("Bold", "", 13)
            pdf.cell(0, 8, line, ln=True)
            pdf.set_font("Reg", "", 11)
            pdf.ln(2)

        # Instruction lines
        elif line.lower().startswith("answer"):
            pdf.set_font("Reg", "", 11)
            pdf.multi_cell(page_width, 7, line)
            pdf.set_font("Reg", "", 11)
            pdf.ln(1)

        # Normal text
        else:
            pdf.multi_cell(page_width, 7, line)
            pdf.ln(1)

    # ===== SAVE PDF =====
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# ================= UI =================
st.title("📝 Question Paper Generator")

subject = st.text_input("Title")

exam_time = st.text_input("Exam Duration (e.g. '90 minutes' or '1.5 hours')")

st.subheader("Instructions")
instructions = st.text_area("Enter Exam Instructions here (one instruction per line). Leave blank if none.")

file = st.file_uploader("Upload CSV (unit, topic)", type="csv")

st.subheader("Question Types")
mcq = st.checkbox("MCQ")
short = st.checkbox("Short Answer")
long = st.checkbox("Long Answer")

# ---- MARK INPUT ----
mcq_marks = st.number_input("Marks per MCQ", min_value=1, max_value=10, value=1)
short_marks = st.number_input("Marks per Short Answer Question", min_value=2, max_value=10, value=5)
long_marks = st.number_input("Marks per Long Answer Question", min_value=5, max_value=20, value=10)

optional = st.checkbox("Add Optional Questions (Choice Based)")
total_marks = st.number_input("Total Marks", min_value=20, step=10)


# ================= GENERATE =================
if st.button("Generate Question Paper"):

    if not subject or not file:
        st.error("Subject name and CSV required")
        st.stop()

    if not exam_time.strip():
        st.error("Please enter exam duration.")
        st.stop()

    df = pd.read_csv(file)
    topics = ", ".join(df["topic"].tolist())

    paper = ""
    section = ord("A")

    for qtype in ["MCQ", "Short Answer", "Long Answer"]:
        if qtype == "MCQ" and not mcq:
            continue
        if qtype == "Short Answer" and not short:
            continue
        if qtype == "Long Answer" and not long:
            continue

        # ---- MARKS ----
        if qtype == "MCQ":
            marks_q = mcq_marks
        elif qtype == "Short Answer":
            marks_q = short_marks
        else:
            marks_q = long_marks

        required_q = total_marks // marks_q
        extra_q = 2 if optional else 0
        total_q = required_q + extra_q

        paper += f"\nSECTION {chr(section)} – {qtype}\n"
        if optional:
            paper += f"Answer any {required_q} questions.\n\n"

        response = generate_ai(build_prompt(qtype, topics, total_q, marks_q))
        paper += response + "\n"
        section += 1

    st.subheader("Generated Question Paper")
    st.text(paper)

    pdf = create_pdf(subject, total_marks, exam_time, instructions, paper)
    with open(pdf, "rb") as f:
        st.download_button(
            "⬇ Download PDF",
            f,
            "Question_Paper.pdf",
            "application/pdf"
        )
