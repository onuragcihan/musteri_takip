import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="Müşteri Sipariş ve Borç Takibi",
    page_icon="📊",
    layout="wide"
)

DB_NAME = "musteri_takip_web.db"

# --- Veritabanı Kurulumu ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Siparişler Tablosu (Excel yapısı)
    c.execute('''
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_adi TEXT,
            urun_siparis TEXT,
            adet INTEGER,
            birim_fiyati REAL,
            toplam_tutar REAL,
            tarih TEXT,
            notlar TEXT
        )
    ''')
    # Ödemeler Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS odemeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_adi TEXT,
            odenen_tutar REAL,
            tarih TEXT,
            notlar TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Şifre Kontrolü ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 Müşteri Takip Sistemi")
    sifre_girdisi = st.text_input("Giriş Şifresi:", type="password")
    if st.button("Giriş Yap"):
        if sifre_girdisi == "010162":
            st.session_state['logged_in'] = True
            st.success("Giriş Başarılı!")
            st.rerun()
        else:
            st.error("Hatalı Şifre!")
    st.stop()

# --- Ana Başlık ---
st.title("📋 Müşteri Sipariş, Borç ve Ödeme Takibi")

tab1, tab2, tab3 = st.tabs(["📝 Excel Sipariş Gir / Düzenle", "💳 Müşteri Borç Kartları & Hesap Özeti", "💵 Ödeme Al"])

# ==========================================
# 1. SEKME: EXCEL GİBİ SİPARİŞ GİRİŞİ
# ==========================================
with tab1:
    st.header("Excel Modu: Sipariş ve Ürün Girişi")
    st.info("💡 **Kullanım:** Tablodaki hücrelere tıklayıp müşteri adı, ürün, adet ve birim fiyatı yazın. Alt taraftaki **'+'** butonuna basarak yeni satır ekleyebilirsiniz. **'💾 Değişiklikleri Kaydet'** butonuna bastığınızda toplam borçlar otomatik hesaplanır.")

    conn = sqlite3.connect(DB_NAME)
    df_siparisler = pd.read_sql_query("SELECT * FROM siparisler", conn)
    conn.close()

    # Eksik sütun kontrolü ve tamamlama
    gerekli_sutunlar = ["musteri_adi", "urun_siparis", "adet", "birim_fiyati", "toplam_tutar", "tarih", "notlar"]
    for col in gerekli_sutunlar:
        if col not in df_siparisler.columns:
            if col in ["adet"]:
                df_siparisler[col] = 1
            elif col in ["birim_fiyati", "toplam_tutar"]:
                df_siparisler[col] = 0.0
            else:
                df_siparisler[col] = ""

    if df_siparisler.empty:
        df_siparisler = pd.DataFrame({
            "musteri_adi": [""],
            "urun_siparis": [""],
            "adet": [1],
            "birim_fiyati": [0.0],
            "toplam_tutar": [0.0],
            "tarih": [datetime.now().strftime("%Y-%m-%d")],
            "notlar": [""]
        })

    # Etkileşimli Excel Tablosu
    edited_df = st.data_editor(
        df_siparisler[gerekli_sutunlar],
        num_rows="dynamic",
        use_container_width=True,
        key="siparis_editor",
        column_config={
            "musteri_adi": st.column_config.TextColumn("Müşteri Adı Soyadı", required=True),
            "urun_siparis": st.column_config.TextColumn("Ürün / Sipariş Adı"),
            "adet": st.column_config.NumberColumn("Adet", min_value=1, default=1),
            "birim_fiyati": st.column_config.NumberColumn("Birim Fiyatı (TL)", format="%.2f TL", default=0.0),
            "toplam_tutar": st.column_config.NumberColumn("Toplam Borç (Otomatik)", format="%.2f TL", disabled=True),
            "tarih": st.column_config.TextColumn("Tarih"),
            "notlar": st.column_config.TextColumn("Notlar")
        }
    )

    col_save, col_down = st.columns([1, 4])
    with col_save:
        if st.button("💾 Değişiklikleri Kaydet", type="primary"):
            # Otomatik Borç Hesaplama: Adet * Birim Fiyatı
            edited_df["toplam_tutar"] = edited_df["adet"] * edited_df["birim_fiyati"]
            
            # Veritabanına kaydet
            conn = sqlite3.connect(DB_NAME)
            edited_df.to_sql("siparisler", conn, if_exists="replace", index=False)
            conn.close()
            st.success("Siparişler ve borçlar başarıyla güncellendi!")
            st.rerun()

    with col_down:
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Excel / CSV Olarak İndir", csv, f"siparisler_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

# ==========================================
# 2. SEKME: MÜŞTERİ BAKIYE KARTLARI (ÖZET)
# ==========================================
with tab2:
    st.header("Müşteri Ekstreleri ve Toplam Borç Durumu")

    conn = sqlite3.connect(DB_NAME)
    df_sip = pd.read_sql_query("SELECT * FROM siparisler", conn)
    df_odeme = pd.read_sql_query("SELECT * FROM odemeler", conn)
    conn.close()

    # Güvenlik: Eksik sütun kontrolü
    for col in ["musteri_adi", "urun_siparis", "adet", "birim_fiyati", "toplam_tutar", "tarih", "notlar"]:
        if col not in df_sip.columns:
            df_sip[col] = 0.0 if "tutar" in col or "fiyati" in col else ""

    for col in ["musteri_adi", "odenen_tutar", "tarih", "notlar"]:
        if col not in df_odeme.columns:
            df_odeme[col] = 0.0 if "tutar" in col else ""

    # Müşteri Listesini Oluştur
    tum_musteriler = list(set(df_sip['musteri_adi'].dropna().tolist() + df_odeme['musteri_adi'].dropna().tolist()))
    tum_musteriler = [str(m).strip() for m in tum_musteriler if str(m).strip() != ""]

    if tum_musteriler:
        secilen_m = st.selectbox("Müşteri Seçiniz:", sorted(tum_musteriler))
        
        # Hesaplamalar
        m_sip = df_sip[df_sip['musteri_adi'] == secilen_m]
        m_odeme = df_odeme[df_odeme['musteri_adi'] == secilen_m]
        
        toplam_siparis_borcu = pd.to_numeric(m_sip['toplam_tutar'], errors='coerce').sum()
        toplam_odenen = pd.to_numeric(m_odeme['odenen_tutar'], errors='coerce').sum()
        kalan_net_borc = toplam_siparis_borcu - toplam_odenen

        # Özet Kartları
        c1, c2, c3 = st.columns(3)
        c1.metric("🛒 Toplam Sipariş Tutarı", f"{toplam_siparis_borcu:,.2f} TL")
        c2.metric("💵 Alınan Toplam Ödeme", f"{toplam_odenen:,.2f} TL")
        c3.metric("🔴 Kalan Net Borç Bakiyesi", f"{kalan_net_borc:,.2f} TL")

        st.divider()
        st.subheader(f"📌 {secilen_m} - Aldığı Ürünler ve Sipariş Detayları")
        st.dataframe(m_sip[['tarih', 'urun_siparis', 'adet', 'birim_fiyati', 'toplam_tutar', 'notlar']], use_container_width=True)

        if not m_odeme.empty:
            st.subheader(f"💳 {secilen_m} - Ödeme Geçmişi")
            st.dataframe(m_odeme[['tarih', 'odenen_tutar', 'notlar']], use_container_width=True)
    else:
        st.info("Henüz kayıtlı müşteri veya sipariş bulunmuyor.")

# ==========================================
# 3. SEKME: ÖDEME ALMA
# ==========================================
with tab3:
    st.header("Müşteriden Ödeme Al")
    
    conn = sqlite3.connect(DB_NAME)
    df_sip = pd.read_sql_query("SELECT * FROM siparisler", conn)
    conn.close()
    
    if "musteri_adi" in df_sip.columns:
        musteri_listesi = sorted(list(set(df_sip['musteri_adi'].dropna().tolist())))
        musteri_listesi = [str(m).strip() for m in musteri_listesi if str(m).strip() != ""]
    else:
        musteri_listesi = []

    if musteri_listesi:
        odeme_musteri = st.selectbox("Ödeme Yapan Müşteri:", musteri_listesi, key="odeme_m_sec")
        odenecek_tutar = st.number_input("Ödenen Tutar (TL):", min_value=0.0, step=50.0)
        odeme_notu = st.text_input("Ödeme Notu (Örn: Havale, Nakit):")
        
        if st.button("Ödemeyi Kaydet"):
            if odenecek_tutar > 0:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                bugun = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("INSERT INTO odemeler (musteri_adi, odenen_tutar, tarih, notlar) VALUES (?, ?, ?, ?)",
                          (odeme_musteri, odenecek_tutar, bugun, odeme_notu))
                conn.commit()
                conn.close()
                st.success(f"{odeme_musteri} kişisinden {odenecek_tutar} TL ödeme alındı!")
                st.rerun()
            else:
                st.warning("Lütfen geçerli bir tutar girin.")
    else:
        st.info("Ödeme almak için önce 1. sekmeden sipariş girilmelidir.")
