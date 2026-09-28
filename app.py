import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="Müşteri Borç ve Sipariş Takibi",
    page_icon="📋",
    layout="wide"
)

# --- Veritabanı Kurulumu ---
DB_NAME = "musteri_takip_web.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Borç Takip Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_adi TEXT,
            islem_tipi TEXT,
            tutar REAL,
            tarih TEXT,
            not_alani TEXT
        )
    ''')
    # Sipariş Takip Tablosu (Excel Modu)
    c.execute('''
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_adi TEXT,
            siparis_detayi TEXT,
            adet INTEGER,
            birim_fiyati REAL,
            toplam_tutar REAL,
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
    st.title("🔒 Müşteri Takip Sistemi Girişi")
    sifre_girdisi = st.text_input("Lütfen Giriş Şifresini Girin:", type="password")
    if st.button("Giriş Yap"):
        if sifre_girdisi == "010162":
            st.session_state['logged_in'] = True
            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Hatalı şifre!")
    st.stop()

# --- Ana Menü (Sekmeler) ---
tab1, tab2 = st.tabs(["💰 Borç ve Ödeme Takibi", "📦 Sipariş Takibi (Excel Modu)"])

# ==========================================
# 1. SEKME: BORÇ VE ÖDEME TAKİBİ
# ==========================================
with tab1:
    st.header("Müşteri Borç ve Ödeme İşlemleri")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Yeni İşlem Ekle")
        musteri_adi = st.text_input("Müşteri Adı Soyadı:")
        islem_tipi = st.selectbox("İşlem Tipi:", ["Borç Ekle", "Ödeme Alındı"])
        tutar = st.number_input("Tutar (TL):", min_value=0.0, step=10.0)
        not_alani = st.text_area("İşlem Notu (İsteğe Bağlı):")
        
        if st.button("İşlemi Kaydet"):
            if musteri_adi.strip() != "" and tutar > 0:
                bugun = datetime.now().strftime("%Y-%m-%d %H:%M")
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute(
                    "INSERT INTO islemler (musteri_adi, islem_tipi, tutar, tarih, not_alani) VALUES (?, ?, ?, ?, ?)",
                    (musteri_adi.strip(), islem_tipi, tutar, bugun, not_alani)
                )
                conn.commit()
                conn.close()
                st.success(f"{musteri_adi} için {islem_tipi} kaydedildi!")
                st.rerun()
            else:
                st.warning("Lütfen müşteri adı ve tutar giriniz.")

    with col2:
        st.subheader("Müşteri Bakiye Sorgulama")
        conn = sqlite3.connect(DB_NAME)
        df_islemler = pd.read_sql_query("SELECT * FROM islemler ORDER BY id DESC", conn)
        conn.close()
        
        if not df_islemler.empty:
            musteri_listesi = ["Tüm Müşteriler"] + sorted(df_islemler['musteri_adi'].unique().tolist())
            secilen_musteri = st.selectbox("Müşteri Seçin:", musteri_listesi)
            
            if secilen_musteri != "Tüm Müşteriler":
                filtreli_df = df_islemler[df_islemler['musteri_adi'] == secilen_musteri]
                toplam_borc = filtreli_df[filtreli_df['islem_tipi'] == "Borç Ekle"]['tutar'].sum()
                toplam_odeme = filtreli_df[filtreli_df['islem_tipi'] == "Ödeme Alındı"]['tutar'].sum()
                kalan_bakiye = toplam_borc - toplam_odeme
                
                st.metric("Kalan Borç Bakiyesi", f"{kalan_bakiye:,.2f} TL")
                st.dataframe(filtreli_df[['tarih', 'musteri_adi', 'islem_tipi', 'tutar', 'not_alani']], use_container_width=True)
            else:
                st.dataframe(df_islemler[['tarih', 'musteri_adi', 'islem_tipi', 'tutar', 'not_alani']], use_container_width=True)

# ==========================================
# 2. SEKME: SİPARİŞ TAKİBİ (EXCEL MODU)
# ==========================================
with tab2:
    st.header("Sipariş Takip Tablosu (Excel Modu)")
    st.info("💡 **Nasıl Kullanılır?** Tablodaki hücrelere tıklayarak doğrudan yazabilirsiniz. Alt taraftaki **'+'** ikonuna basarak yeni satır ekleyebilir, **'💾 Değişiklikleri Kaydet'** butonu ile kaydedebilirsiniz.")

    conn = sqlite3.connect(DB_NAME)
    df_siparisler = pd.read_sql_query("SELECT * FROM siparisler", conn)
    conn.close()

    # Kolon isimleri ve varsayılan veri tipi düzenlemesi
    if df_siparisler.empty:
        df_siparisler = pd.DataFrame({
            "musteri_adi": ["---"],
            "siparis_detayi": ["---"],
            "adet": [1],
            "birim_fiyati": [0.0],
            "toplam_tutar": [0.0],
            "tarih": [datetime.now().strftime("%Y-%m-%d")],
            "notlar": ["-"]
        })

    # Etkileşimli Excel Tablosu (st.data_editor)
    edited_df = st.data_editor(
        df_siparisler,
        num_rows="dynamic",  # Satır ekleme/silme imkanı verir
        use_container_width=True,
        key="siparis_editor",
        column_config={
            "id": None, # ID sütununu gizle
            "musteri_adi": st.column_config.TextColumn("Müşteri Adı", required=True),
            "siparis_detayi": st.column_config.TextColumn("Sipariş / Ürün Detayı"),
            "adet": st.column_config.NumberColumn("Adet", min_value=1, default=1),
            "birim_fiyati": st.column_config.NumberColumn("Birim Fiyatı (TL)", format="%.2f TL", default=0.0),
            "toplam_tutar": st.column_config.NumberColumn("Toplam Tutar (TL)", format="%.2f TL", disabled=True),
            "tarih": st.column_config.TextColumn("Tarih"),
            "notlar": st.column_config.TextColumn("Notlar")
        }
    )

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("💾 Değişiklikleri Kaydet"):
            # Otomatik Toplam Tutar Hesabı
            edited_df["toplam_tutar"] = edited_df["adet"] * edited_df["birim_fiyati"]
            
            # Veritabanına Yaz
            conn = sqlite3.connect(DB_NAME)
            edited_df.to_sql("siparisler", conn, if_exists="replace", index=False)
            conn.close()
            st.success("Tüm sipariş verileri başarıyla kaydedildi!")
            st.rerun()

    with col_btn2:
        # Excel / CSV İndirme Butonu
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Tabloyu İndir (CSV/Excel)",
            data=csv,
            file_name=f"siparisler_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
