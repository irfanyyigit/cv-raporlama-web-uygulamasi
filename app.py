import streamlit as st
import json
import os
import pandas as pd
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

# Yerel geliştirme için .env dosyasını yükle (Bulutta burası atlansa da sistem çalışır)
load_dotenv()

# ==========================================
# 1. SAYFA AYARLARI VE TASARIM
# ==========================================
st.set_page_config(
    page_title="Gelişmiş CV Analiz Paneli / Advanced CV Analysis Dashboard",
    layout="wide"
)

# DİL DESTEĞİ (TOGGLE)
# Uygulamanın en üst sağ/sol köşesinde temiz bir geçiş sağlar
dil_secimi = st.toggle("English / Türkçe", value=False, help="Switch language / Dili değiştir")

# Dil Paketleri Sözlüğü
DIL = {
    "TR": {
        "baslik": "Puanlama Sistemi",
        "alt_baslik": "Adayların **PDF** özgeçmişlerini yükleyin, sistem saniyeler içinde analiz etsin.",
        "hata_key": "Sistem Yapılandırma Hatası: Groq API Key tanımlanmamış. Lütfen Streamlit Cloud Secrets ayarlarını kontrol edin.",
        "alt_header_yukle": "PDF Dosyalarını Yükleyin",
        "uploader_label": "Değerlendirmek istediğiniz tüm CV'leri (PDF) çoklu olarak seçip buraya bırakın:",
        "buton_analiz": "Analiz sürecini başlat",
        "hata_pdf": "PDF metni taranamadı.",
        "hata_pdf_detay": "Bu dosya dijital metin içermiyor.",
        "basari_analiz": "Tüm CV'ler başarıyla analiz edildi!",
        "tablo_baslik": "Genel Aday Değerlendirme Tablosu",
        "buton_indir": "Genel Tabloyu İndir (Excel/CSV)",
        "derin_analiz_baslik": "Yapay Zeka Derinlemesine Aday Analiz Raporu",
        "selectbox_label": "Raporu İncelenecek Adayı Seçin:",
        "info_metni": "**Aday:** {aday} | **Aldığı Puan:** {puan} | **Durum:** {durum}",
        "teknik_analiz_header": "### Baştan Sona Teknik ve Yetkinlik Analizi",
        "durum_gecti": "Geçti",
        "durum_elendi": "Elendi",
        "durum_hata": "⚠️ Hata",
        "durum_okunamadi": "⚠️ Okunamadı",
        "baraj_alti_mesaj": "Baraj altı puan.",
        "format_hatasi": "Format hatası.",
        "format_hatasi_detay": "Yapay zeka yanıtı işleyemedi.",
        "baglanti_hatasi": "Bağlantı hatası.",
        "kolon_dosya": "Dosya Adı (Aday)",
        "kolon_puan": "Puan",
        "kolon_durum": "Durum",
        "kolon_neden": "Elenirse Neden Yetersiz?",
        "ai_prompt_lang": "Türkçe"
    },
    "EN": {
        "baslik": "Scoring System",
        "alt_baslik": "Upload candidates' **PDF** resumes, and the system will analyze them in seconds.",
        "hata_key": "System Configuration Error: Groq API Key is not defined. Please check Streamlit Cloud Secrets settings.",
        "alt_header_yukle": "Upload PDF Files",
        "uploader_label": "Drag and drop all candidate CVs (PDF) here for multi-upload:",
        "buton_analiz": "Start analysis process",
        "hata_pdf": "PDF text could not be scanned.",
        "hata_pdf_detay": "This file does not contain digital text.",
        "basari_analiz": "All CVs have been successfully analyzed!",
        "tablo_baslik": "General Candidate Evaluation Table",
        "buton_indir": "Download General Table (Excel/CSV)",
        "derin_analiz_baslik": "AI In-Depth Candidate Analysis Report",
        "selectbox_label": "Select Candidate to Review Report:",
        "info_metni": "**Candidate:** {aday} | **Score:** {puan} | **Status:** {durum}",
        "teknik_analiz_header": "### Comprehensive Technical and Competency Analysis",
        "durum_gecti": "Passed",
        "durum_elendi": "Rejected",
        "durum_hata": "⚠️ Error",
        "durum_okunamadi": "⚠️ Unreadable",
        "baraj_alti_mesaj": "Score below threshold.",
        "format_hatasi": "Format error.",
        "format_hatasi_detay": "AI could not process the response.",
        "baglanti_hatasi": "Connection error.",
        "kolon_dosya": "File Name (Candidate)",
        "kolon_puan": "Score",
        "kolon_durum": "Status",
        "kolon_neden": "Reason for Rejection (If Ineligible)",
        "ai_prompt_lang": "English"
    }
}

# Seçili dil paketini ata
L = DIL["EN"] if dil_secimi else DIL["TR"]

st.title(L["baslik"])
st.markdown(L["alt_baslik"])
st.write("---")

# ==========================================
# GÜVENLİ API KEY OTOMASYONU (Lokal ve Bulut Uyumlu)
# ==========================================
groq_key = ""

# Önce sistemde .env veya yerel çevre değişkeni var mı diye bakar (Lokal kontrol)
local_key = os.getenv("GROQ_API_KEY", "")

if local_key:
    groq_key = local_key
else:
    # Eğer lokalde key yoksa, buluttadır diyerek direkt Secrets'tan çekmeye çalışır
    try:
        groq_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        groq_key = ""

# Varsayılan model seçimi
MODEL_NAME = "llama-3.3-70b-versatile"

if "analiz_sonuclari" not in st.session_state:
    st.session_state.analiz_sonuclari = None

# ==========================================
# 2. PDF METİN OKUMA FONKSİYONU
# ==========================================
def pdf_metin_ayıkla(pdf_dosyası):
    try:
        reader = PdfReader(pdf_dosyası)
        tam_metin = ""
        for sayfa in reader.pages:
            metin = sayfa.extract_text()
            if metin:
                tam_metin += metin + "\n"
        return tam_metin.strip()
    except Exception as e:
        return f"PDF Okuma Hatası: {str(e)}"

# ==========================================
# 3. AI ANALİZ MANTIĞI
# ==========================================
def cv_analiz_et(cv_metni, api_key, dil_paketi):
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )
    
    # Prompt içerisindeki yönlendirmeler seçilen dile göre güncellenir
    prompt = f"""
    Sana aşağıda metni verilen bir adayın CV'sini göndereceğim. Bu CV'yi bir Senior/Expert backend developer pozisyonu için baştan sona detaylıca değerlendir.
    
    [KRİTİK KURALLAR]: 
    1. Adaya 100 üzerinden bir "puan" ver.
    2. Eğer adaya verdiğin toplam puan 60 veya daha üzerindeyse, "neden_yetersiz" alanını KESİNLİKLE boş bırak (null dön).
    3. Eğer puan 60'ın altındaysa, adayın neden elendiğini "neden_yetersiz" alanında açıkla.
    4. "detayli_analiz_raporu" alanında: Puanı kaç olursa olsun, İK çalışanına adayın baştan sona derinlemesine bir analizini sun. Bu analiz uzun ve detaylı olmalı; adayın teknik yetkinlik güçlü tarafları, varsa iş deneyimindeki boşluklar veya eksiklikler, şirkete katabileceği katma değer ve Senior pozisyonuna uyumu hakkında kapsamlı, profesyonel bir yorum içermelidir (En az 3-4 uzun cümle veya paragraf yapısında olmalı).
    5. [DİL KURALI]: "neden_yetersiz" ve "detayli_analiz_raporu" alanlarına yazacağın tüm metinleri KESİNLİKLE **{dil_paketi['ai_prompt_lang']}** dilinde yaz.

    Çıktıyı KESİNLİKLE sadece aşağıdaki JSON formatında ver, kod blokları (```json ) veya ekstra açıklama yazma:
    {{
      "puan": <verdiğin_puan>,
      "neden_yetersiz": <açıklama_veya_null>,
      "detayli_analiz_raporu": "<adayın_bastan_sona_detayli_profesyonel_analizi>"
    }}

    Değerlendirilecek CV Metni:
    \"\"\"
    {cv_metni}
    \"\"\"
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        ham_yanit = response.choices[0].message.content.strip()
        veri = json.loads(ham_yanit)
        
        baraj_puan = 60
        if int(veri["puan"]) >= baraj_puan:
            veri["neden_yetersiz"] = "—"
            veri["durum"] = dil_paketi["durum_gecti"]
        else:
            veri["durum"] = dil_paketi["durum_elendi"]
            if not veri.get("neden_yetersiz") or veri["neden_yetersiz"] == "null":
                veri["neden_yetersiz"] = dil_paketi["baraj_alti_mesaj"]
                
        return veri

    except json.JSONDecodeError:
        return {"puan": 0, "durum": dil_paketi["durum_hata"], "neden_yetersiz": dil_paketi["format_hatasi"], "detayli_analiz_raporu": dil_paketi["format_hatasi_detay"]}
    except Exception as e:
        return {"puan": 0, "durum": dil_paketi["durum_hata"], "neden_yetersiz": dil_paketi["baglanti_hatasi"], "detayli_analiz_raporu": f"Hata/Error: {str(e)}"}

# ==========================================
# 4. KULLANICI ARAYÜZÜ (SIFIR KEY GİRİŞİ)
# ==========================================
if not groq_key:
    st.error(L["hata_key"])
else:
    st.subheader(L["alt_header_yukle"])
    
    yuklenen_dosyalar = st.file_uploader(
        L["uploader_label"],
        type=["pdf"],
        accept_multiple_files=True
    )
    
    if yuklenen_dosyalar:
        if st.button(L["buton_analiz"]):
            rapor_verisi = []
            ilerleme_cubugu = st.progress(0)
            
            for index, dosya in enumerate(yuklenen_dosyalar):
                dosya_adi = dosya.name
                cv_metni = pdf_metin_ayıkla(dosya)
                
                if cv_metni and not cv_metni.startswith("PDF Okuma Hatası"):
                    sonuc = cv_analiz_et(cv_metni, groq_key, L)
                else:
                    sonuc = {
                        "puan": 0, 
                        "durum": L["durum_okunamadi"], 
                        "neden_yetersiz": L["hata_pdf"], 
                        "detayli_analiz_raporu": L["hata_pdf_detay"]
                    }
                
                rapor_verisi.append({
                    L["kolon_dosya"]: dosya_adi,
                    L["kolon_puan"]: sonuc["puan"],
                    L["kolon_durum"]: sonuc["durum"],
                    L["kolon_neden"]: sonuc["neden_yetersiz"],
                    "detayli_rapor_hafiza": sonuc["detayli_analiz_raporu"]
                })
                
                ilerleme_cubugu.progress((index + 1) / len(yuklenen_dosyalar))
            
            st.session_state.analiz_sonuclari = pd.DataFrame(rapor_verisi)
            st.success(L["basari_analiz"])

    # ==========================================
    # 5. SONUÇLARIN GÖSTERİLME ALANI
    # ==========================================
    if st.session_state.analiz_sonuclari is not None:
        df = st.session_state.analiz_sonuclari
        
        # Eğer kullanıcı dil değiştirdiyse, DataFrame kolon isimlerini de dinamik olarak eşleştiriyoruz
        # (Önceki dilden kalan kolon adlarını yakalamak için dinamik kontrol sağlanmıştır)
        mevcut_kolonlar = df.columns.tolist()
        dosya_kolonu = mevcut_kolonlar[0]
        puan_kolonu = mevcut_kolonlar[1]
        durum_kolonu = mevcut_kolonlar[2]
        neden_kolonu = mevcut_kolonlar[3]
        
        gosterilecek_df = df[[dosya_kolonu, puan_kolonu, durum_kolonu, neden_kolonu]].copy()
        # Tablo başlıklarını seçili dile göre güncelle
        gosterilecek_df.columns = [L["kolon_dosya"], L["kolon_puan"], L["kolon_durum"], L["kolon_neden"]]
        
        st.subheader(L["tablo_baslik"])
        st.dataframe(gosterilecek_df, use_container_width=True)
        
        csv_indir = gosterilecek_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label=L["buton_indir"],
            data=csv_indir,
            file_name="ik_cv_ozet_raporu.csv",
            mime="text/csv"
        )
        
        st.write("---")
        
        st.subheader(L["derin_analiz_baslik"])
        secilen_aday = st.selectbox(
            L["selectbox_label"],
            options=df[dosya_kolonu].tolist()
        )
        
        if secilen_aday:
            aday_verisi = df[df[dosya_kolonu] == secilen_aday].iloc[0]
            info_mesaji = L["info_metni"].format(aday=secilen_aday, puan=aday_verisi[puan_kolonu], durum=aday_verisi[durum_kolonu])
            st.info(info_mesaji)
            st.markdown(L["teknik_analiz_header"])
            st.write(aday_verisi["detayli_rapor_hafiza"])