import sqlite3
import datetime
import streamlit as st

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Müşteri Borç Takip Sistemi",
    page_icon="💰",
    layout="wide"
)

DB_NAME = "musteri_takip_web.db"
SISTEM_SIFRESI = "010162"

# --- VERİTABANI İŞLEMLERİ ---
def db_init():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musteriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            tarih TEXT NOT NULL,
            borc REAL NOT NULL,
            not_bilgisi TEXT
        )
    """)
    conn.commit()
    conn.close()

def db_tum_kayitlari_getir():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, tarih, ad, borc, not_bilgisi FROM musteriler ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def db_kayit_ekle(ad, tarih, borc, not_bilgisi):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO musteriler (ad, tarih, borc, not_bilgisi)
        VALUES (?, ?, ?, ?)
    """, (ad, tarih, borc, not_bilgisi))
    conn.commit()
    conn.close()

def db_kayit_guncelle(row_id, ad, tarih, borc, not_bilgisi):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE musteriler
        SET ad = ?, tarih = ?, borc = ?, not_bilgisi = ?
        WHERE id = ?
    """, (ad, tarih, borc, not_bilgisi, row_id))
    conn.commit()
    conn.close()

def db_kayit_sil(row_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM musteriler WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()

def format_borc(val):
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

# --- BAŞLANGIÇ AYARLARI ---
db_init()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# --- ŞİFRE GİRİŞ EKRANI ---
if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align: center;'>🔒 Müşteri Borç Takip - Giriş</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        girilen_sifre = st.text_input("Sistem Şifresi:", type="password", key="sifre_input")
        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            if girilen_sifre == SISTEM_SIFRESI:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Hatalı şifre! Lütfen tekrar deneyin.")
    st.stop()

# --- ANA UYGULAMA EKRANI ---
st.title("💰 Müşteri Borç Kayıt Paneli")

# Çıkış Yap Butonu (Yan panelde)
with st.sidebar:
    st.write("🔑 **Oturum Bilgisi**")
    if st.button("Çıkış Yap"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- VERİLERİ YÜKLE VE TOPLAM BORÇ HESAPLA ---
rows = db_tum_kayitlari_getir()
toplam_borc = sum(row[3] for row in rows)

# Toplam Borç Metrik Kartı
st.metric(label="📊 Toplam Borç Tutarı", value=format_borc(toplam_borc))

st.markdown("---")

# --- YENİ KAYIT EKLEME FORMU ---
with st.expander("➕ Yeni Müşteri / Borç Kaydı Ekle", expanded=True):
    with st.form("yeni_kayit_formu", clear_on_submit=True):
        col_tarih, col_ad, col_borc = st.columns([1, 2, 1])
        
        with col_tarih:
            tarih_val = st.date_input("Tarih", value=datetime.date.today(), format="DD.MM.YYYY")
        with col_ad:
            ad_val = st.text_input("Müşteri Adı *")
        with col_borc:
            borc_val = st.number_input("Borç Miktarı (TL) *", min_value=0.0, step=50.0, format="%.2f")
            
        not_val = st.text_input("Not / Ödeme Bilgisi (Opsiyonel)")
        
        btn_ekle = st.form_submit_button("Kaydı Ekle", type="primary", use_container_width=True)
        
        if btn_ekle:
            if not ad_val.strip():
                st.warning("Lütfen Müşteri Adı alanını doldurun!")
            elif borc_val <= 0:
                st.warning("Lütfen geçerli bir borç miktarı girin!")
            else:
                tarih_str = tarih_val.strftime("%d.%m.%Y")
                db_kayit_ekle(ad_val.strip(), tarih_str, borc_val, not_val.strip())
                st.success(f"'{ad_val}' kaydı başarıyla eklendi.")
                st.rerun()

# --- KAYIT LİSTESİ VE YÖNETİMİ ---
st.subheader("📋 Müşteri Kayıtları")

if not rows:
    st.info("Henüz kayıtlı müşteri bulunmamaktadır.")
else:
    # Arama Filtresi
    arama_termi = st.text_input("🔍 Müşteri Adına Göre Ara:", "")
    
    filtered_rows = [
        r for r in rows if arama_termi.lower() in r[2].lower()
    ] if arama_termi else rows

    # Kayıtları Tablo Halinde Göster
    for row in filtered_rows:
        row_id, tarih, ad, borc_val, not_bilgisi = row
        
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([1.2, 2, 1.5, 2.5, 2])
            
            c1.write(f"📅 **{tarih}**")
            c2.write(f"👤 **{ad}**")
            c3.write(f"🔴 **{format_borc(borc_val)}**")
            c4.write(f"📝 {not_bilgisi if not_bilgisi else '-'}")
            
            # İşlem Butonları (Düzenle / Ödeme Al / Sil)
            with c5:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    btn_odeme = st.button("💳 Ödeme", key=f"odeme_{row_id}")
                with col_btn2:
                    btn_islem = st.button("⚙️ Yönet", key=f"yonet_{row_id}")

            # --- ÖDEME ALMA MODALI/PANELİ ---
            if btn_odeme:
                st.session_state[f"active_odeme_{row_id}"] = True

            if st.session_state.get(f"active_odeme_{row_id}", False):
                with st.form(key=f"odeme_form_{row_id}"):
                    st.write(f"### 💳 Ödeme Al: {ad}")
                    st.write(f"Mevcut Borç: **{format_borc(borc_val)}**")
                    
                    odeme_tutari = st.number_input("Alınan Ödeme Tutarı (TL):", min_value=0.01, max_value=float(borc_val), step=10.0, format="%.2f")
                    
                    c_odeme_submit, c_odeme_cancel = st.columns(2)
                    with c_odeme_submit:
                        if st.form_submit_button("Ödemeyi Onayla", type="primary"):
                            yeni_borc = borc_val - odeme_tutari
                            db_kayit_guncelle(row_id, ad, tarih, yeni_borc, not_bilgisi)
                            st.session_state[f"active_odeme_{row_id}"] = False
                            st.success("Ödeme düşüldü!")
                            st.rerun()
                    with c_odeme_cancel:
                        if st.form_submit_button("İptal"):
                            st.session_state[f"active_odeme_{row_id}"] = False
                            st.rerun()

            # --- DÜZENLEME VEYA SİLME PANELİ ---
            if btn_islem:
                st.session_state[f"active_edit_{row_id}"] = True

            if st.session_state.get(f"active_edit_{row_id}", False):
                with st.form(key=f"edit_form_{row_id}"):
                    st.write(f"### ✏️ Kaydı Düzenle: {ad}")
                    
                    e_tarih = st.text_input("Tarih", value=tarih)
                    e_ad = st.text_input("Müşteri Adı", value=ad)
                    e_borc = st.number_input("Borç (TL)", value=float(borc_val), min_value=0.0, format="%.2f")
                    e_not = st.text_input("Not", value=not_bilgisi if not_bilgisi else "")

                    c_save, c_del, c_cancel = st.columns(3)
                    with c_save:
                        if st.form_submit_button("💾 Kaydet", type="primary"):
                            db_kayit_guncelle(row_id, e_ad.strip(), e_tarih.strip(), e_borc, e_not.strip())
                            st.session_state[f"active_edit_{row_id}"] = False
                            st.success("Güncellendi!")
                            st.rerun()
                    with c_del:
                        if st.form_submit_button("🗑️ Kaydı Sil"):
                            db_kayit_sil(row_id)
                            st.session_state[f"active_edit_{row_id}"] = False
                            st.warning("Kayıt silindi.")
                            st.rerun()
                    with c_cancel:
                        if st.form_submit_button("Kapat"):
                            st.session_state[f"active_edit_{row_id}"] = False
                            st.rerun()
            st.divider()