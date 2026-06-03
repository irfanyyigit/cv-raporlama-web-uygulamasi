import streamlit as st
import json
import os
import pandas as pd
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv
from datetime import datetime, timedelta
from st_supabase_connection import SupabaseConnection # Yeni kütüphane

load_dotenv()

# ==========================================
# 1. PAGE SETTINGS
# ==========================================
st.set_page_config(
    page_title="Advanced CV Analysis Panel",
    layout="wide"
)

# Canlı Supabase Bağlantısı
conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url="https://ngbfndehzmpzeiuzdlbo.supabase.co",
    key="BURAYA_ANON_PUBLIC_KEY_GELECEK" # Kendi Anon Public Key'ini tırnak içine yapıştır
)

def check_and_activate_token(input_token):
    """
    Supabase üzerinden token kontrolü yapar. İlk girişte 30 günlük süreyi başlatır.
    """
    try:
        # Veritabanından tokenı sorgula (Boşlukları temizleyerek)
        response = conn.table("users_tokens").select("*").eq("token", input_token.strip()).execute()
        
        if response.data and len(response.data) > 0:
            row = response.data[0]
            expiry_date_str = row.get("expiry_date")
            now = datetime.now()
            
            # DURUM 1: Token var ama expiry_date boş veya None (İlk kez giriş yapıyor)
            if not expiry_date_str or expiry_date_str == "":
                future_date = now + timedelta(days=30)
                future_date_str = future_date.isoformat()
                
                # Supabase'de expiry_date alanını güncelle
                conn.table("users_tokens").update({"expiry_date": future_date_str}).eq("token", input_token.strip()).execute()
                return True, "Activated"
            
            # DURUM 2: Token daha önce aktifleştirilmiş, süre kontrolü
            else:
                expiry_date = datetime.fromisoformat(expiry_date_str)
                if now <= expiry_date:
                    return True, "Valid"
                else:
                    return False, "Expired"
                    
        return False, "Invalid"
    except Exception as e:
        return False, "Error"

# Session State Kimlik Doğrulama Kontrolü
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ==========================================
# GİRİŞ EKRANI (ÖDEME DUVARI)
# ==========================================
if not st.session_state.authenticated:
    st.title("Advanced CV Analysis Panel")
    st.subheader("Devam Etmek İçin Erişim Kodunuzu Girin")
    
    user_token = st.text_input("Lütfen e-posta adresinize gönderilen Token anahtarını girin:", type="password")
    
    if st.button("Uygulamaya Giriş Yap"):
        if user_token:
            is_valid, status = check_and_activate_token(user_token)
            if is_valid:
                st.session_state.authenticated = True
                if status == "Activated":
                    st.success("Tokenınız ilk kez aktifleştirildi! 30 günlük süreniz şu andan itibaren başladı.")
                else:
                    st.success("Giriş başarılı!")
                st.rerun()
            elif status == "Expired":
                st.error("Bu tokenın 1 aylık kullanım süresi dolmuştur. Lütfen planınızı yenileyin.")
            else:
                st.error("Geçersiz veya hatalı bir token girdiniz. Lütfen tekrar deneyin.")
        else:
            st.warning("Lütfen bir token alanı doldurun.")
            
    st.write("---")
    st.info("Aktif bir erişim kodunuz yoksa Starter veya Pro planlarımızdan birini satın alarak anında kod edinebilirsiniz.")
    st.stop()
# ==========================================
# ANA UYGULAMA (KODUNUN ORİJİNAL KISMI)
# ==========================================
POSITIONS = [
    # --- IT, Software and Technology ---
    "Backend Developer", "Frontend Developer", "Full Stack Developer", "Mobile Application Developer",
    "DevOps Engineer", "Data Scientist", "Data Analyst", "Data Engineer",
    "QA / Software Test Engineer", "Cyber Security Specialist", "Cloud Engineer",
    "Embedded Systems Developer", "Game Developer", "Database Administrator (DBA)",
    "System Administrator", "IT Support Specialist",

    # --- Product, Project and Management ---
    "Project Manager", "Product Manager", "Scrum Master / Agile Coach",
    "Business Analyst", "Team Lead / Technical Lead", "CTO (Chief Technology Officer)",

    # --- Design and Creative ---
    "UI/UX Designer", "Graphic Designer", "Video Editor / Motion Designer", "Art Director",
    "3D Artist / Modeler",

    # --- Marketing, E-Commerce and Growth ---
    "Marketing Specialist", "Digital Marketing Specialist", "E-commerce Specialist",
    "SEO Specialist", "Growth Hacker", "Content Creator",
    "Social Media Manager", "Brand Manager",

    # --- Sales and Customer Relations ---
    "Sales Representative", "Account Manager",
    "Business Development Specialist", "Customer Success Specialist", "Call Center / Customer Representative",

    # --- Human Resources and Administration ---
    "HR Specialist", "Talent Acquisition Specialist",
    "HR Business Partner (HRBP)", "Office Manager / Executive Assistant", "Administrative Affairs Specialist",

    # --- Finance, Accounting and Legal ---
    "Accountant", "Certified Public Accountant (CPA)", "Financial Analyst", "Budgeting and Reporting Specialist",
    "Legal Counsel / Lawyer", "Internal Auditor",

    # --- Health, Education and Social Sciences ---
    "Psychologist", "Clinical Psychologist", "Dietitian / Nutritionist", "Corporate HR Psychologist",
    "Special Education Teacher", "Corporate Trainer",

    # --- Operations, Logistics and Manufacturing ---
    "Operations Manager", "Logistics and Supply Chain Specialist", "Procurement Specialist",
    "Production / Factory Engineer", "Quality Assurance Engineer (Manufacturing)", "Warehouse / Inventory Specialist"
]

if st.sidebar.button("Güvenli Çıkış"):
    st.session_state.authenticated = False
    st.rerun()

st.title("Scoring System")

selected_position = st.selectbox("Select Target Position:", options=POSITIONS)
st.markdown("Upload candidate **PDF** resumes; the system will analyze them based on the selected role.")
st.write("---")

# API Key
groq_key = os.getenv("GROQ_API_KEY", "") or st.secrets.get("GROQ_API_KEY", "")
MODEL_NAME = "llama-3.3-70b-versatile"

if "analiz_sonuclari" not in st.session_state:
    st.session_state.analiz_sonuclari = None


def extract_pdf_text(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()]).strip()
    except:
        return None


# ==========================================
# 2. AI ANALYSIS (ENGLISH ONLY)
# ==========================================
def analyze_cv(cv_text, api_key, target_position):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)

    prompt = f"""
    You will evaluate the CV below for the position of **"{target_position}"**.

    [CRITICAL RULES]:
    1. If the candidate's background and competencies are completely unrelated to **"{target_position}"**, give them a score below 40 and state the position mismatch in "rejection_reason".
    2. Assign a score out of 100 in the "score" field.
    3. If the score is 60 or above, leave "rejection_reason" null. If below 60, explain the reason.
    4. In "detailed_analysis_report": professionally analyze the candidate's suitability for this specific position ({target_position}) in terms of both technical skills and soft skills.
    5. Write ALL text (report and rejection reason) strictly in **English**.

    Respond ONLY with valid JSON in this exact format:
    {{
      "score": <integer>,
      "rejection_reason": <string or null>,
      "detailed_analysis_report": "<analysis text>"
    }}

    CV Text:
    {cv_text}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)

        if int(data["score"]) >= 60:
            data["rejection_reason"] = "—"
            data["status"] = "Passed"
        else:
            data["status"] = "Rejected"
            if not data.get("rejection_reason"):
                data["rejection_reason"] = "Role mismatch or low score."
        return data
    except:
        return {
            "score": 0,
            "status": "⚠️ Error",
            "rejection_reason": "Processing error.",
            "detailed_analysis_report": "An error occurred during analysis."
        }


# ==========================================
# 3. UI AND ANALYSIS
# ==========================================
if not groq_key:
    st.error("API Key is not defined.")
else:
    uploaded_files = st.file_uploader("Drop CVs here:", type=["pdf"], accept_multiple_files=True)

    if uploaded_files and st.button("Start Analysis"):
        results = []
        progress = st.progress(0)

        for i, file in enumerate(uploaded_files):
            text = extract_pdf_text(file)
            if text:
                result = analyze_cv(text, groq_key, selected_position)
            else:
                result = {
                    "score": 0,
                    "status": "⚠️ Error",
                    "rejection_reason": "Could not read file.",
                    "detailed_analysis_report": ""
                }

            results.append({
                "File Name": file.name,
                "Score": result["score"],
                "Status": result["status"],
                "Rejection Reason": result["rejection_reason"],
                "report": result["detailed_analysis_report"]
            })
            progress.progress((i + 1) / len(uploaded_files))

        st.session_state.analiz_sonuclari = pd.DataFrame(results)
        st.success("All CVs analyzed based on the selected role!")

    if st.session_state.analiz_sonuclari is not None:
        df = st.session_state.analiz_sonuclari

        st.subheader(f"General Evaluation Table ({selected_position})")
        st.dataframe(df.drop(columns=["report"]), use_container_width=True)

        st.write("---")
        selected_candidate = st.selectbox("Select Candidate:", options=df["File Name"].tolist())
        if selected_candidate:
            row = df[df["File Name"] == selected_candidate].iloc[0]
            st.info(f"**Candidate:** {selected_candidate} | **Score:** {row['Score']} | **Status:** {row['Status']}")
            st.markdown("### Comprehensive Competency Analysis")
            st.write(row["report"])
