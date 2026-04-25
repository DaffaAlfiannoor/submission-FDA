# 🛒 E-Commerce Data Analysis Project

Dashboard interaktif dan analisis data lengkap menggunakan dataset **E-Commerce Public Dataset**

---

## 🔧 Cara Setup & Menjalankan

### 1. Clone / Download Proyek

Pastikan seluruh file di atas sudah tersedia di direktori lokal Anda.

### 2. Buat Virtual Environment (Direkomendasikan)

```bash
# Buat virtual environment
python -m venv venv

# Aktifkan — Windows
venv\Scripts\activate

# Aktifkan — macOS / Linux
source venv/bin/activate
```

### 3. Install Dependensi

```bash
pip install -r requirements.txt
```

### 4. Jalankan Dashboard Streamlit

```bash
cd dashboard
streamlit run dashboard.py
```

Dashboard akan terbuka otomatis di browser pada alamat **http://localhost:8501**

### 5. Jalankan Notebook Analisis (Opsional)

```bash
jupyter notebook olist_analysis.ipynb
```

---

## 📊 Fitur Dashboard

Dashboard terdiri dari **5 halaman** yang dapat diakses melalui sidebar:

| Halaman | Konten |
|---|---|
| 🏠 **Overview** | KPI utama (revenue, orders, customers), tren revenue, distribusi payment |
| 📈 **Revenue Trend** | Analisis bulanan, rolling average, perbandingan YoY, MoM growth |
| 📦 **Product Categories** | Revenue & unit terjual per kategori, bubble chart review vs revenue |
| 🌍 **Geographic Analysis** | Distribusi order & revenue per state, revenue per customer |
| 👥 **RFM Segmentation** | Segmentasi pelanggan, scatter RFM, clustering spending tier |

### Filter Interaktif (Sidebar)
- **Year Range** — Filter data berdasarkan rentang tahun
- **Top N Categories** — Atur jumlah kategori yang ditampilkan (5–30)

---

## 📋 Pertanyaan Bisnis yang Dijawab

1. **Bagaimana tren pendapatan bulanan Olist selama 2016–2018, dan pada bulan apa puncaknya?**
2. **Kategori produk apa yang paling banyak terjual dan menghasilkan revenue tertinggi?**
3. **Bagaimana distribusi geografis pelanggan dan wilayah mana yang berpotensi tinggi?**

---

## 🔬 Teknik Analisis yang Diterapkan

- **RFM Analysis** — Segmentasi pelanggan berdasarkan Recency, Frequency, Monetary
- **Geospatial Analysis** — Peta interaktif distribusi pelanggan & seller (Folium)
- **Clustering (Manual Binning)** — Pengelompokan spending tier & recency tier menggunakan `pd.cut`

---

## 🌐 Deploy ke Streamlit Cloud

1. Push seluruh isi folder `dashboard/` ke repositori GitHub
2. Buka [share.streamlit.io](https://share.streamlit.io) dan login
3. Klik **New app** → pilih repositori dan set **Main file path** ke `dashboard.py`
4. Klik **Deploy** — aplikasi akan live dalam beberapa menit

> **Catatan:** Pastikan semua file `.csv` ikut ter-push ke repositori agar dashboard dapat membaca data.

---

## 🐍 Versi Python

Proyek ini dikembangkan dan diuji menggunakan **Python 3.10+**

---

## 📦 Library Utama

| Library | Kegunaan |
|---|---|
| `pandas` | Manipulasi dan analisis data |
| `numpy` | Komputasi numerik |
| `matplotlib` | Visualisasi statis (notebook) |
| `seaborn` | Visualisasi statistik (notebook) |
| `folium` | Peta interaktif geospatial |
| `streamlit` | Framework dashboard web |
| `plotly` | Visualisasi interaktif (dashboard) |
| `jupyter` | Eksekusi notebook analisis |
