import streamlit as st
import json
import os
import pandas as pd
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

# Yerel geliştirme için .env dosyasını yükle
load_dotenv()

# ==========================================
# 1. SAYFA AYARLARI VE TASARIM
# ==========================================
st.set_page_config(
    page_title="Gelişmiş CV Analiz Paneli",
    layout="wide"
)

# 🌐 DİL DESTEĞİ VE ÇİFT DİLLİ MESLEK LİSTELERİ
dil_secimi = st.toggle("English / Türkçe", value=False)

# Türkçe Meslek Listesi (65 Pozisyon)
MESLEKLER_TR = [
    # --- Bilişim, Yazılım ve Teknoloji ---
    "Backend Geliştirici", "Frontend Geliştirici", "Full Stack Geliştirici", "Mobil Uygulama Geliştirici",
    "DevOps Mühendisi", "Veri Bilimci", "Veri Analisti", "Veri Mühendisi",
    "Yazılım Test Uzmanı (QA)", "Siber Güvenlik Uzmanı", "Bulut Bilişim Mühendisi",
    "Gömülü Sistemler Geliştirici", "Oyun Geliştirici", "Veritabanı Yöneticisi (DBA)",
    "Sistem Yöneticisi", "IT Destek Uzmanı",
    
    # --- Ürün, Proje ve Yönetim ---
    "Proje Yöneticisi", "Ürün Yöneticisi", "Scrum Master / Çevik Koç",
    "İş Analisti", "Takım Lideri / Teknik Lider", "CTO (Teknoloji Başkanı)",
    
    # --- Tasarım ve Kreatif ---
    "UI/UX Tasarımcı", "Grafik Tasarımcı", "Video Editörü / Hareketli Grafik Tasarımcı", "Sanat Yönetmeni",
    "3D Sanatçısı / Modelleme Uzmanı",
    
    # --- Pazarlama, E-Ticaret ve Büyüme ---
    "Pazarlama Uzmanı", "Dijital Pazarlama Uzmanı", "E-ticaret Uzmanı",
    "SEO Uzmanı", "Büyüme Uzmanı (Growth Hacker)", "İçerik Üreticisi",
    "Sosyal Medya Yöneticisi", "Marka Yöneticisi",
    
    # --- Satış ve Müşteri İlişkileri ---
    "Satış Temsilcisi", "Müşteri İlişkileri Yöneticisi (Account Manager)",
    "İş Geliştirme Uzmanı", "Müşteri Başarısı Uzmanı (Customer Success)", "Çağrı Merkezi / Müşteri Temsilcisi",
    
    # --- İnsan Kaynakları ve İdari İşler ---
    "İnsan Kaynakları Uzmanı", "İşe Alım Uzmanı (Talent Acquisition)",
    "İK İş Ortağı (HRBP)", "Ofis Yöneticisi / Yönetici Asistanı", "İdari İşler Uzmanı",
    
    # --- Finans, Muhasebe ve Hukuk ---
    "Muhasebe Uzmanı", "Mali Müşavir", "Finansal Analist", "Bütçe ve Raporlama Uzmanı",
    "Hukuk Müşaviri / Avukat", "İç Denetçi",
    
    # --- Sağlık, Eğitim ve Sosyal Bilimler ---
    "Psikolog", "Klinik Psikolog", "Diyetisyen / Beslenme Uzmanı", "Kurumsal İK Psikoloğu",
    "Özel Eğitim Öğretmeni", "Kurumsal Eğitmen",
    
    # --- Operasyon, Lojistik ve Üretim ---
    "Operasyon Yöneticisi", "Lojistik ve Tedarik Zinciri Uzmanı", "Satınalma Uzmanı",
    "Üretim / Fabrika Mühendisi", "Kalite Güvence Mühendisi (Üretim)", "Depo / Stok Yönetim Uzmanı"
]

# İngilizce Meslek Listesi (65 Pozisyon - Birebir Eşleşen Sıralamada)
MESLEKLER_EN = [
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

DIL = {
    "TR": {
        "baslik": "Puanlama Sistemi",
        "meslek_secin": "Hedef Pozisyonu Seçin:",
        "alt_baslik": "Adayların **PDF** özgeçmişlerini yükleyin, sistem seçtiğiniz alana göre analiz etsin.",
        "hata_key": "API Key tanımlanmamış.",
        "alt_header_yukle": "PDF Dosyalarını Yükleyin",
        "uploader_label": "CV'leri buraya bırakın:",
        "buton_analiz": "Analiz sürecini başlat",
        "basari_analiz": "Tüm CV'ler seçilen pozisyona göre analiz edildi!",
        "tablo_baslik": "Genel Aday Değerlendirme Tablosu",
        "buton_indir": "Genel Tabloyu İndir",
        "derin_analiz_baslik": "Yapay Zeka Derinlemesine Rapor",
        "selectbox_label": "Aday Seçin:",
        "info_metni": "**Aday:** {aday} | **Puan:** {puan} | **Durum:** {durum}",
        "teknik_analiz_header": "### Baştan Sona Yetkinlik Analizi",
        "kolon_dosya": "Dosya Adı", "kolon_puan": "Puan", "kolon_durum": "Durum", "kolon_neden": "Elenme Nedeni",
        "ai_prompt_lang": "Türkçe",
        "durum_gecti": "Geçti", "durum_elendi": "Elendi", "durum_hata": "⚠️ Hata", "baraj_alti_mesaj": "Pozisyon uyumsuzluğu veya düşük puan.",
        "meslek_listesi": MESLEKLER_TR
    },
    "EN": {
        "baslik": "Scoring System",
        "meslek_secin": "Select Target Position:",
        "alt_baslik": "Upload candidate PDFs; the system will analyze them based on the selected role.",
        "hata_key": "API Key not defined.",
        "alt_header_yukle": "Upload PDF Files",
        "uploader_label": "Drop CVs here:",
        "buton_analiz": "Start analysis",
        "basari_analiz": "All CVs analyzed based on the selected role!",
        "tablo_baslik": "General Evaluation Table",
        "buton_indir": "Download Report",
        "derin_analiz_baslik": "AI In-Depth Report",
        "selectbox_label": "Select Candidate:",
        "info_metni": "**Candidate:** {aday} | **Score:** {puan} | **Status:** {durum}",
        "teknik_analiz_header": "### Comprehensive Competency Analysis",
        "kolon_dosya": "File Name", "kolon_puan": "Score", "kolon_durum": "Status", "kolon_neden": "Rejection Reason",
        "ai_prompt_lang": "English",
        "durum_gecti": "Passed", "durum_elendi": "Rejected", "durum_hata": "⚠️ Error", "baraj_alti_mesaj": "Role mismatch or low score.",
        "meslek_listesi": MESLEKLER_EN
    }
}

L = DIL["EN"] if dil_secimi else DIL["TR"]

st.title(L["baslik"])

# 🎯 POZİSYON SEÇİMİ (Seçilen dile göre dinamik liste yüklenir)
secilen_alan = st.selectbox(L["meslek_secin"], options=L["meslek_listesi"])

st.markdown(L["alt_baslik"])
st.write("---")

# API KEY Ayarları (Lokal/Secrets)
groq_key = os.getenv("GROQ_API_KEY", "") or st.secrets.get("GROQ_API_KEY", "")
MODEL_NAME = "llama-3.3-70b-versatile"

if "analiz_sonuclari" not in st.session_state:
    st.session_state.analiz_sonuclari = None

def pdf_metin_ayıkla(pdf_dosyası):
    try:
        reader = PdfReader(pdf_dosyası)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()]).strip()
    except: return None

# ==========================================
# 3. AI ANALİZ MANTIĞI (POZİSYON ODAKLI)
# ==========================================
def cv_analiz_et(cv_metni, api_key, dil_paketi, hedef_meslek):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    
    prompt = f"""
    Sana aşağıda metni verilen bir adayın CV'sini göndereceğim. Bu CV'yi **"{hedef_meslek}"** pozisyonu için değerlendir.
    
    [KRİTİK KURALLAR]: 
    1. Eğer adayın geçmişi ve yetkinlikleri seçilen **"{hedef_meslek}"** alanı ile tamamen alakasızsa adaya direkt 40 puanın altında ver ve "neden_yetersiz" kısmına pozisyon uyumsuzluğu olduğunu belirt.
    2. Adaya 100 üzerinden bir "puan" ver.
    3. Eğer puan 60 veya üzerindeyse "neden_yetersiz" alanını boş (null) bırak. 60 altındaysa nedenini açıkla.
    4. "detayli_analiz_raporu" alanında: Adayın bu spesifik pozisyona ({hedef_meslek}) uygunluğunu teknik ve soft-skill açısından profesyonelce analiz et.
    5. Tüm metinleri (rapor ve elenme nedeni dahil) KESİNLİKLE **{dil_paketi['ai_prompt_lang']}** dilinde yaz.

    JSON Formatı:
    {{
      "puan": <puan>,
      "neden_yetersiz": <açıklama>,
      "detayli_analiz_raporu": "<analiz>"
    }}

    CV Metni:
    {cv_metni}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        veri = json.loads(response.choices[0].message.content.strip())
        
        if int(veri["puan"]) >= 60:
            veri["neden_yetersiz"], veri["durum"] = "—", dil_paketi["durum_gecti"]
        else:
            veri["durum"] = dil_paketi["durum_elendi"]
            if not veri.get("neden_yetersiz"): veri["neden_yetersiz"] = dil_paketi["baraj_alti_mesaj"]
        return veri
    except:
        return {"puan": 0, "durum": dil_paketi["durum_hata"], "neden_yetersiz": "Hata/Error", "detayli_analiz_raporu": "Hata oluştu."}

# ==========================================
# 4. ARAYÜZ VE ANALİZ
# ==========================================
if not groq_key:
    st.error(L["hata_key"])
else:
    yuklenen_dosyalar = st.file_uploader(L["uploader_label"], type=["pdf"], accept_multiple_files=True)
    
    if yuklenen_dosyalar and st.button(L["buton_analiz"]):
        rapor_verisi = []
        ilerleme = st.progress(0)
        
        for i, dosya in enumerate(yuklenen_dosyalar):
            metin = pdf_metin_ayıkla(dosya)
            sonuc = cv_analiz_et(metin, groq_key, L, secilen_alan) if metin else {"puan":0, "durum":"Error", "neden_yetersiz":"Okunamadı", "detayli_analiz_raporu":""}
            
            rapor_verisi.append({
                L["kolon_dosya"]: dosya.name,
                L["kolon_puan"]: sonuc["puan"],
                L["kolon_durum"]: sonuc["durum"],
                L["kolon_neden"]: sonuc["neden_yetersiz"],
                "rapor": sonuc["detayli_analiz_raporu"]
            })
            ilerleme.progress((i + 1) / len(yuklenen_dosyalar))
        
        st.session_state.analiz_sonuclari = pd.DataFrame(rapor_verisi)
        st.success(L["basari_analiz"])

    if st.session_state.analiz_sonuclari is not None:
        df = st.session_state.analiz_sonuclari
        
        st.subheader(f"{L['tablo_baslik']} ({secilen_alan})")
        st.dataframe(df.drop(columns=["rapor"]), use_container_width=True)
        
        st.write("---")
        secilen_aday = st.selectbox(L["selectbox_label"], options=df[L["kolon_dosya"]].tolist())
        if secilen_aday:
            v = df[df[L["kolon_dosya"]] == secilen_aday].iloc[0]
            st.info(L["info_metni"].format(aday=secilen_aday, puan=v[L["kolon_puan"]], durum=v[L["kolon_durum"]]))
            st.markdown(L["teknik_analiz_header"])
            st.write(v["rapor"])
