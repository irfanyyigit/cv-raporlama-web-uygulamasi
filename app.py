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
    page_title="Gelişmiş CV Analiz Paneli",
    layout="wide"
)

st.title("Derinlemesine CV Analiz & Puanlama Sistemi")
st.markdown("Adayların **PDF** özgeçmişlerini yükleyin, sistem saniyeler içinde analiz etsin.")
st.write("---")
# ==========================================
# GÜVENLİ API KEY OTOMASYONU (Lokal ve Bulut Uyumlu)
# ==========================================
groq_key = ""

# Önce Streamlit Cloud Secrets kontrol edilir (Hata vermemesi için try-except içinde)
try:
    if "GROQ_API_KEY" in st.secrets:
        groq_key = st.secrets["GROQ_API_KEY"]
except Exception:
    # Eğer lokaldeysek st.secrets hata verir, bu durumda buraya düşer ve .env dosyasını okur
    groq_key = os.getenv("GROQ_API_KEY", "")

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
def cv_analiz_et(cv_metni, api_key):
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )
    
    prompt = f"""
    Sana aşağıda metni verilen bir adayın CV'sini göndereceğim. Bu CV'yi bir Senior/Expert backend developer pozisyonu için baştan sona detaylıca değerlendir.
    
    [KRİTİK KURALLAR]: 
    1. Adaya 100 üzerinden bir "puan" ver.
    2. Eğer adaya verdiğin toplam puan 60 veya daha üzerindeyse, "neden_yetersiz" alanını KESİNLİKLE boş bırak (null dön).
    3. Eğer puan 60'ın altındaysa, adayın neden elendiğini "neden_yetersiz" alanında açıkla.
    4. "detayli_analiz_raporu" alanında: Puanı kaç olursa olsun, İK çalışanına adayın baştan sona derinlemesine bir analizini sun. Bu analiz uzun ve detaylı olmalı; adayın teknik yetkinlik güçlü tarafları, varsa iş deneyimindeki boşluklar veya eksiklikler, şirkete katabileceği katma değer ve Senior pozisyonuna uyumu hakkında kapsamlı, profesyonel bir yorum içermelidir (En az 3-4 uzun cümle veya paragraf yapısında olmalı).

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
            veri["durum"] = "Geçti"
        else:
            veri["durum"] = "Elendi"
            if not veri.get("neden_yetersiz"):
                veri["neden_yetersiz"] = "Baraj altı puan."
                
        return veri

    except json.JSONDecodeError:
        return {"puan": 0, "durum": "⚠️ Hata", "neden_yetersiz": "Format hatası.", "detayli_analiz_raporu": "Yapay zeka yanıtı işleyemedi."}
    except Exception as e:
        return {"puan": 0, "durum": "⚠️ Hata", "neden_yetersiz": "Bağlantı hatası.", "detayli_analiz_raporu": f"Hata: {str(e)}"}

# ==========================================
# 4. KULLANICI ARAYÜZÜ (SIFIR KEY GİRİŞİ)
# ==========================================
if not groq_key:
    st.error("Sistem Yapılandırma Hatası: Groq API Key tanımlanmamış. Lütfen Streamlit Cloud Secrets ayarlarını kontrol edin.")
else:
    st.subheader("PDF Dosyalarını Yükleyin")
    
    yuklenen_dosyalar = st.file_uploader(
        "Değerlendirmek istediğiniz tüm CV'leri (PDF) çoklu olarak seçip buraya bırakın:",
        type=["pdf"],
        accept_multiple_files=True
    )
    
    if yuklenen_dosyalar:
        if st.button("Analiz sürecini başlat"):
            rapor_verisi = []
            ilerleme_cubugu = st.progress(0)
            
            for index, dosya in enumerate(yuklenen_dosyalar):
                dosya_adi = dosya.name
                cv_metni = pdf_metin_ayıkla(dosya)
                
                if cv_metni and not cv_metni.startswith("PDF Okuma Hatası"):
                    sonuc = cv_analiz_et(cv_metni, groq_key)
                else:
                    sonuc = {
                        "puan": 0, 
                        "durum": "⚠️ Okunamadı", 
                        "neden_yetersiz": "PDF metni taranamadı.", 
                        "detayli_analiz_raporu": "Bu dosya dijital metin içermiyor."
                    }
                
                rapor_verisi.append({
                    "Dosya Adı (Aday)": dosya_adi,
                    "Puan": sonuc["puan"],
                    "Durum": sonuc["durum"],
                    "Elenirse Neden Yetersiz?": sonuc["neden_yetersiz"],
                    "detayli_rapor_hafiza": sonuc["detayli_analiz_raporu"]
                })
                
                ilerleme_cubugu.progress((index + 1) / len(yuklenen_dosyalar))
            
            st.session_state.analiz_sonuclari = pd.DataFrame(rapor_verisi)
            st.success("Tüm CV'ler başarıyla analiz edildi!")

    # ==========================================
    # 5. SONUÇLARIN GÖSTERİLME ALANI
    # ==========================================
    if st.session_state.analiz_sonuclari is not None:
        df = st.session_state.analiz_sonuclari
        gosterilecek_df = df[["Dosya Adı (Aday)", "Puan", "Durum", "Elenirse Neden Yetersiz?"]]
        
        st.subheader("Genel Aday Değerlendirme Tablosu")
        st.dataframe(gosterilecek_df, use_container_width=True)
        
        csv_indir = gosterilecek_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="Genel Tabloyu İndir (Excel/CSV)",
            data=csv_indir,
            file_name="ik_cv_ozet_raporu.csv",
            mime="text/csv"
        )
        
        st.write("---")
        
        st.subheader("Yapay Zeka Derinlemesine Aday Analiz Raporu")
        secilen_aday = st.selectbox(
            "Raporu İncelenecek Adayı Seçin:",
            options=df["Dosya Adı (Aday)"].tolist()
        )
        
        if secilen_aday:
            aday_verisi = df[df["Dosya Adı (Aday)"] == secilen_aday].iloc[0]
            st.info(f"**Aday:** {secilen_aday} | **Aldığı Puan:** {aday_verisi['Puan']} | **Durum:** {aday_verisi['Durum']}")
            st.markdown("### Baştan Sona Teknik ve Yetkinlik Analizi")
            st.write(aday_verisi["detayli_rapor_hafiza"])