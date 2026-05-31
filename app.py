import streamlit as st
import json
import os
import re
import pandas as pd
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Advanced CV Analysis Panel", layout="wide")

POSITIONS = [
    # --- IT, Software and Technology ---
    "Backend Developer", "Frontend Developer", "Full Stack Developer", "Mobile Application Developer",
    "DevOps Engineer", "Data Scientist", "Data Analyst", "Data Engineer",
    "QA / Software Test Engineer", "Cyber Security Specialist", "Cloud Engineer",
    "Embedded Systems Developer", "Game Developer", "Database Administrator (DBA)",
    "System Administrator", "IT Support Specialist", "Machine Learning Engineer",
    "AI / Prompt Engineer", "Blockchain Developer", "Network Engineer",
    "IT Project Manager", "Solutions Architect", "Site Reliability Engineer (SRE)",
    "Technical Writer", "IT Security Analyst",

    # --- Product, Project and Management ---
    "Project Manager", "Product Manager", "Scrum Master / Agile Coach",
    "Business Analyst", "Team Lead / Technical Lead", "CTO (Chief Technology Officer)",
    "Program Manager", "Portfolio Manager", "Change Management Specialist",

    # --- Design and Creative ---
    "UI/UX Designer", "Graphic Designer", "Video Editor / Motion Designer", "Art Director",
    "3D Artist / Modeler", "Product Designer", "Brand Identity Designer",
    "Illustrator", "UX Researcher", "Creative Director",

    # --- Marketing, E-Commerce and Growth ---
    "Marketing Specialist", "Digital Marketing Specialist", "E-commerce Specialist",
    "SEO Specialist", "Growth Hacker", "Content Creator",
    "Social Media Manager", "Brand Manager", "Performance Marketing Specialist",
    "Email Marketing Specialist", "Affiliate Marketing Manager", "PR & Communications Specialist",
    "Market Research Analyst", "Event Planner / Event Manager",

    # --- Sales and Customer Relations ---
    "Sales Representative", "Account Manager",
    "Business Development Specialist", "Customer Success Specialist",
    "Call Center / Customer Representative", "Inside Sales Representative",
    "Key Account Manager", "Pre-Sales Engineer / Solutions Consultant",
    "Sales Manager", "Channel Sales Manager",

    # --- Human Resources and Administration ---
    "HR Specialist", "Talent Acquisition Specialist",
    "HR Business Partner (HRBP)", "Office Manager / Executive Assistant",
    "Administrative Affairs Specialist", "HR Manager", "HR Generalist",
    "Compensation & Benefits Specialist", "Learning & Development (L&D) Specialist",
    "Employee Relations Specialist", "DEI (Diversity & Inclusion) Specialist",
    "Employer Branding Specialist", "Payroll Specialist",

    # --- Finance, Accounting and Legal ---
    "Accountant", "Certified Public Accountant (CPA)", "Financial Analyst",
    "Budgeting and Reporting Specialist", "Legal Counsel / Lawyer", "Internal Auditor",
    "Risk Manager", "Compliance Officer", "Tax Specialist",
    "Treasury Analyst", "CFO (Chief Financial Officer)",
    "Investment Analyst", "Credit Analyst", "Paralegal / Legal Assistant",
    "Insurance Specialist / Underwriter",

    # --- Engineering (Non-IT) ---
    "Civil Engineer", "Mechanical Engineer", "Electrical Engineer",
    "Structural Engineer", "Chemical Engineer", "Environmental Engineer",
    "Industrial Engineer", "Aerospace Engineer", "Biomedical Engineer",
    "Geotechnical Engineer", "Process Engineer", "Facilities Engineer",
    "Health & Safety Engineer / HSE Specialist", "Automation / Robotics Engineer",
    "Renewable Energy Engineer", "Telecommunications Engineer",

    # --- Architecture, Construction and Real Estate ---
    "Architect", "Landscape Architect", "Interior Designer",
    "Construction Project Manager", "Site Engineer / Construction Engineer",
    "Building Inspector / Quality Control Engineer",
    "Real Estate Agent / Property Consultant", "Property Manager",
    "Urban Planner", "BIM Specialist", "Cost Estimator / Quantity Surveyor",

    # --- Healthcare and Medical ---
    "General Practitioner / Medical Doctor", "Surgeon",
    "Registered Nurse", "Pharmacist", "Dentist",
    "Physical Therapist / Physiotherapist", "Occupational Therapist",
    "Radiologist / Radiology Technician", "Medical Laboratory Technician",
    "Paramedic / Emergency Medical Technician (EMT)",
    "Healthcare Administrator / Hospital Manager",
    "Optometrist", "Nutritionist / Dietitian",

    # --- Health, Education and Social Sciences ---
    "Psychologist", "Clinical Psychologist", "Corporate HR Psychologist",
    "Special Education Teacher", "Corporate Trainer",
    "Primary / Secondary School Teacher", "University Lecturer / Academic",
    "Curriculum Developer / Instructional Designer",
    "School Counselor / Guidance Counselor", "Social Worker",
    "Speech-Language Therapist",

    # --- Media, Communications and Journalism ---
    "Journalist / Reporter", "Copywriter / Content Writer",
    "Editor / Chief Editor", "Podcast Producer",
    "Public Relations (PR) Manager", "Communications Manager",
    "Translator / Interpreter", "Photographer", "Broadcast Producer",

    # --- Hospitality, Tourism and Food & Beverage ---
    "Hotel Manager", "Restaurant Manager", "Front Office Manager",
    "Food & Beverage Manager", "Chef / Head Chef",
    "Event Coordinator / Hospitality Coordinator",
    "Tourism Specialist / Travel Agent",
    "Concierge", "Revenue Manager (Hospitality)",

    # --- Operations, Logistics and Manufacturing ---
    "Operations Manager", "Logistics and Supply Chain Specialist",
    "Procurement Specialist", "Production / Factory Engineer",
    "Quality Assurance Engineer (Manufacturing)", "Warehouse / Inventory Specialist",
    "Import / Export Specialist", "Fleet Manager",
    "Manufacturing Plant Manager", "ERP / SAP Specialist",

    # --- Science, Research and Environment ---
    "Research Scientist", "Data Research Analyst",
    "Environmental Consultant", "Chemist / Laboratory Scientist",
    "Biotechnologist", "Geologist / Geoscientist",
    "Agricultural Engineer / Agronomist",

    # --- Executive and C-Suite ---
    "CEO (Chief Executive Officer)", "COO (Chief Operating Officer)",
    "CMO (Chief Marketing Officer)", "CHRO (Chief Human Resources Officer)",
    "General Manager", "Managing Director",
]

CV_CHAR_LIMIT = 12000

st.title("Scoring System")
selected_position = st.selectbox("Select Target Position:", options=POSITIONS)
st.markdown("Upload candidate **PDF** resumes; the system will analyze them based on the selected role.")
st.write("---")

groq_key = os.getenv("GROQ_API_KEY", "") or st.secrets.get("GROQ_API_KEY", "")
MODEL_NAME = "llama-3.3-70b-versatile"

if "analiz_sonuclari" not in st.session_state:
    st.session_state.analiz_sonuclari = None


def extract_pdf_text(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        pages_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
        return "\n".join(pages_text).strip()
    except Exception:
        return None


def truncate_cv(text, char_limit=CV_CHAR_LIMIT):
    if len(text) > char_limit:
        return text[:char_limit] + "\n\n[...CV truncated for length...]"
    return text


def extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON object found in response: {raw[:300]}")


def analyze_cv(cv_text, api_key, target_position):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    cv_text = truncate_cv(cv_text)

    prompt = f"""You are an expert HR evaluator. Evaluate the CV below for the position: "{target_position}".

INSTRUCTIONS:
- If the candidate's background is completely unrelated to "{target_position}", assign a score below 40.
- Assign an integer score from 0 to 100.
- If score >= 60, set rejection_reason to null.
- If score < 60, explain the rejection reason briefly.
- Write a professional competency analysis covering technical skills and soft skills.
- All text MUST be in English only.

You MUST respond with ONLY a valid JSON object. No explanation, no markdown, no code fences. Just raw JSON.

Required format:
{{"score": <integer>, "rejection_reason": <string or null>, "detailed_analysis_report": "<analysis>"}}

CV:
{cv_text}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()
        data = extract_json(raw)

        score = int(data.get("score", 0))
        if score >= 60:
            data["rejection_reason"] = "—"
            data["status"] = "Passed"
        else:
            data["status"] = "Rejected"
            if not data.get("rejection_reason"):
                data["rejection_reason"] = "Role mismatch or low score."
        data["score"] = score
        return data, None

    except Exception as e:
        return None, str(e)


# ==========================================
# UI AND ANALYSIS
# ==========================================
if not groq_key:
    st.error("API Key is not defined.")
else:
    uploaded_files = st.file_uploader("Drop CVs here:", type=["pdf"], accept_multiple_files=True)

    if uploaded_files and st.button("Start Analysis"):
        results = []
        progress = st.progress(0)
        status_placeholder = st.empty()

        for i, file in enumerate(uploaded_files):
            status_placeholder.info(f"Analyzing {i+1}/{len(uploaded_files)}: **{file.name}**")
            text = extract_pdf_text(file)

            if not text:
                results.append({
                    "File Name": file.name, "Score": 0, "Status": "⚠️ Error",
                    "Rejection Reason": "Could not extract text from PDF.",
                    "report": "PDF could not be read. It may be scanned/image-based."
                })
            else:
                result, error = analyze_cv(text, groq_key, selected_position)
                if result:
                    results.append({
                        "File Name": file.name, "Score": result["score"],
                        "Status": result["status"],
                        "Rejection Reason": result.get("rejection_reason", "—"),
                        "report": result.get("detailed_analysis_report", "")
                    })
                else:
                    results.append({
                        "File Name": file.name, "Score": 0, "Status": "⚠️ Error",
                        "Rejection Reason": "AI response parse error.",
                        "report": f"Debug info: {error}"
                    })

            progress.progress((i + 1) / len(uploaded_files))

        status_placeholder.empty()
        st.session_state.analiz_sonuclari = pd.DataFrame(results)
        st.success("All CVs analyzed based on the selected role!")

    if st.session_state.analiz_sonuclari is not None:
        df = st.session_state.analiz_sonuclari

        errors = df[df["Status"] == "⚠️ Error"]
        if not errors.empty:
            with st.expander(f"⚠️ {len(errors)} file(s) had errors — click to see details"):
                for _, row in errors.iterrows():
                    st.markdown(f"**{row['File Name']}**: {row['report']}")

        st.subheader(f"General Evaluation Table ({selected_position})")
        st.dataframe(df.drop(columns=["report"]), use_container_width=True)

        st.write("---")
        selected_candidate = st.selectbox("Select Candidate:", options=df["File Name"].tolist())
        if selected_candidate:
            row = df[df["File Name"] == selected_candidate].iloc[0]
            st.info(f"**Candidate:** {selected_candidate} | **Score:** {row['Score']} | **Status:** {row['Status']}")
            st.markdown("### Comprehensive Competency Analysis")
            st.write(row["report"])
