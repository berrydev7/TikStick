# Berry TikTok Sticker Scraper

![Version](https://img.shields.io/badge/version-1.0.0-cyan.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20Terminal%20%7C%20PowerShell%20%7C%20Termux-brightgreen.svg)

**Berry TikTok Sticker Scraper** adalah tool Command-Line Interface (CLI) modern, interaktif, dan informatif untuk mendeteksi, mengekstrak, dan mengunduh stiker komentar dari video TikTok secara otomatis.

Dirancang dengan antarmuka terminal profesional menggunakan palet warna standar, visual tabel dan progress bar interaktif, serta penyimpanan JSON otomatis yang aman dan tahan terhadap kegagalan jaringan.

---

## Fitur Utama

- **Antarmuka CLI Modern & Interaktif**:
  - Tampilan visual rapi menggunakan library `rich` dan menu navigasi interaktif `questionary`.
  - Konsistensi warna terminal: **Cyan** (Informasi), **Hijau** (Keberhasilan), **Kuning** (Peringatan), **Merah** (Error), dan **Putih/Abu-abu** (Teks biasa).
  - Mode non-interaktif saat argumen baris perintah diberikan.
  - Kompatibel penuh dengan **Windows Terminal**, **PowerShell**, dan **Termux** (Android).
  - Dukungan flag `--no-color` untuk terminal monokrom.

- **Penyimpanan JSON Otomatis di Direktori Script**:
  - Seluruh hasil scraping tersimpan secara default di direktori tempat `main.py` berada (`SCRIPT_DIR`), bukan di working directory terminal pengguna saat menjalankan perintah.
  - Penamaan file otomatis berbasis waktu lokal: `berry_stickers_YYYYMMDD_HHMMSS.json`.
  - Pencegahan benturan nama file (*collision handling*): jika file dengan timestamp yang sama sudah ada, suffix numerik (`_1`, `_2`, dst.) otomatis ditambahkan tanpa menimpa file lama.
  - Format UTF-8 dengan `ensure_ascii=False` dan indentasi 4 spasi yang valid serta dapat dibaca kembali dengan `json.load()`.

- **Mekanisme Penyimpanan Parsial & Penanganan Error**:
  - Jika koneksi terputus atau terjadi pembatasan API di tengah jalan, data stiker yang telah terkumpul **tidak akan hilang**.
  - Status ditandai secara akurat: `completed`, `partial`, atau `failed`.
  - Pesan error disanitasi secara otomatis agar tidak membocorkan token, cookie, atau kredensial sensitif.

- **Dukungan Format URL Fleksibel**:
  - URL Web standar: `https://www.tiktok.com/@username/video/1234567890123456789`
  - URL Foto: `https://www.tiktok.com/@username/photo/1234567890123456789`
  - URL Mobile / Webapp / V: `https://m.tiktok.com/v/1234567890123456789.html`
  - Shortlink: `https://vt.tiktok.com/ZS.../`, `https://vm.tiktok.com/...`, `https://www.tiktok.com/t/...`
  - ID numerik langsung: `1234567890123456789`

- **Downloader dan Ekstraktor Bawaan**:
  - Ekstraksi dan peninjauan daftar URL stiker dari file JSON sebelumnya (`--extract-json`).
  - Pengunduhan aset media stiker (WebP, GIF, PNG, JPG) ke folder lokal secara otomatis (`--download-json`).

---

## Struktur Proyek

```
berry-tiktok-sticker-scraper/
├── main.py                     # Entry point CLI (menu interaktif & argument parser)
├── config.py                   # Konfigurasi aplikasi, header browser, dan endpoint
├── requirements.txt            # Daftar pustaka dependensi
├── README.md                   # Dokumentasi lengkap
├── core/
│   ├── __init__.py
│   ├── tiktok_client.py        # Klien HTTP, resolusi URL/shortlink & stream komentar
│   ├── comment_parser.py       # Parser batch komentar & pagination TikTok API
│   ├── sticker_detector.py     # Pendeteksi attachment stiker & tipe media MIME
│   ├── sticker_downloader.py   # Pengunduh file stiker dari file JSON
│   └── exporter.py             # Manajemen ekspor JSON, penamaan & mitigasi benturan
├── utils/
│   ├── __init__.py
│   ├── cli_ui.py               # Panel branding Berry, tabel, & progress bar
│   ├── validators.py           # Validasi URL/ID, filter sanitasi token & path
│   └── logger.py               # Logger terminal dengan skema warna Berry
└── tests/
    ├── __init__.py
    ├── test_sticker_detector.py # Pengujian deteksi stiker & tipe media
    ├── test_exporter.py         # Pengujian ekspor JSON, direktori default, & data parsial
    └── test_url_validation.py   # Pengujian validasi URL, regex ID, & sanitasi error
```

---

## Instalasi

### 1. Klon atau Masuk ke Direktori Proyek

```bash
cd D:\Scrape\TikTokSticker
```

### 2. Pasang Dependensi

Pastikan Python 3.8+ telah terpasang:

```bash
pip install -r requirements.txt
```

---

## Panduan Penggunaan

### 1. Mode Menu Interaktif

Jalankan script tanpa argumen untuk membuka menu interaktif Berry:

```bash
python main.py
```

Tampilan menu utama:
```text
╭──────────────────────────────────────────────────╮
│           BERRY TIKTOK STICKER SCRAPER           │
│                  Version 1.0.0                   │
╰──────────────────────────────────────────────────╯

[1] Scrape stickers from TikTok video
[2] Extract sticker URLs from JSON
[3] Download stickers from JSON
[4] View previous results
[5] Exit
```

Pilih opsi dengan mengetikkan angka atau memilih via prompt interaktif:
- **[1] Scrape stickers from TikTok video**: Masukkan URL video untuk memulai proses scraping.
- **[2] Extract sticker URLs from JSON**: Lihat ringkasan dan tabel URL stiker dari file JSON yang ada.
- **[3] Download stickers from JSON**: Unduh file stiker ke folder lokal.
- **[4] View previous results**: Jelajahi riwayat ekspor JSON yang tersimpan di direktori script.
- **[5] Exit**: Keluar dari aplikasi.

---

### 2. Mode Perintah Langsung (CLI Flag)

Aplikasi mendukung eksekusi cepat non-interaktif:

#### A. Melakukan Scraping Video Langsung
```bash
python main.py --url "https://www.tiktok.com/@username/video/1234567890123456789"
```

#### B. Menyimpan Hasil ke Lokasi Kustom
```bash
python main.py --url "https://www.tiktok.com/@username/video/1234567890123456789" --output ./custom_result.json
```
*(Catatan: Jika `--output` tidak dicantumkan, file JSON otomatis disimpan di direktori script `main.py`).*

#### C. Mengekstrak URL Stiker dari File JSON
```bash
python main.py --extract-json berry_stickers_20261014_083000.json
```

#### D. Mengunduh Stiker dari File JSON
```bash
python main.py --download-json berry_stickers_20261014_083000.json
```

#### E. Menonaktifkan Warna Terminal (Monokrom)
```bash
python main.py --url "https://www.tiktok.com/@username/video/1234567890123456789" --no-color
```

#### F. Menampilkan Bantuan Argumen
```bash
python main.py --help
```

---

## Struktur File JSON Hasil Scraping

File JSON output mengikuti struktur standar berikut:

```json
{
    "tool": "Berry TikTok Sticker Scraper",
    "version": "1.0.0",
    "source": {
        "video_url": "https://www.tiktok.com/@username/video/1234567890123456789",
        "video_id": "1234567890123456789"
    },
    "scraping": {
        "started_at": "2026-10-14T08:30:00+07:00",
        "completed_at": "2026-10-14T08:30:15+07:00",
        "comments_processed": 250,
        "stickers_found": 18,
        "unique_stickers": 12,
        "direct_urls_found": 10,
        "status": "completed"
    },
    "stickers": [
        {
            "comment_id": "7354928192305810721",
            "sticker_id": "99887766",
            "sticker_url": "https://p16-sign-va.tiktokcdn.com/tos-maliva-i-0000/sticker1_anim.webp",
            "thumbnail_url": "https://p16-sign-va.tiktokcdn.com/tos-maliva-i-0000/sticker1_thumb.webp",
            "media_type": "image/webp",
            "download_status": "pending"
        }
    ],
    "errors": []
}
```

### Keterangan Field:
- `source`: URL canonical dan ID video yang diproses.
- `scraping.started_at` & `completed_at`: Waktu lokal sistem dalam format ISO 8601 dengan offset timezone.
- `scraping.status`: Status eksekusi (`completed`, `partial`, atau `failed`).
- `stickers`: Array objek stiker yang terdeteksi. Identifier asli (`sticker_id`, `comment_id`) dipertahankan tanpa rekayasa. Informasi yang tidak tersedia diisi dengan `null`.
- `errors`: Daftar pesan error yang telah disanitasi dari token dan kredensial rahasia.

---

## Pengujian Otomatis (Unit Testing)

Unit test otomatis telah disediakan dengan mock lengkap tanpa ketergantungan pada jaringan TikTok langsung.

Jalankan test suite menggunakan `pytest`:

```bash
python -m pytest tests/ -v
```

Cakupan pengujian meliputi:
- Verifikasi default output JSON selalu berada di direktori script (`SCRIPT_DIR`).
- Bukti independensi output terhadap working directory terminal (`os.chdir`).
- Validasi deserialisasi JSON dengan `json.load()`.
- Penanganan benturan nama file (*no overwrite*, penambahan suffix numerik).
- Ketahanan penyimpanan data parsial saat terjadi gangguan koneksi/rate limit.
- Penyimpanan metadata saat kegagalan dini terjadi tanpa merusak struktur JSON.
- Dukungan argumen `--output` kustom.
- Kejelasan output error pada CLI.
- Ketepatan kalkulasi statistik ringkasan scraping (*summary counts*).

---

## Keterbatasan & Catatan Etika Scraping

1. **Aksesibilitas Komentar Publik**:
   - Tool ini hanya dapat mengakses komentar pada video TikTok yang bersifat publik.
   - Video yang diprivat atau dinonaktifkan fitur komentarnya oleh pemilik video tidak akan menghasilkan data komentar.
2. **Pembatasan Laju Permintaan (Rate Limiting) & Proteksi Bot**:
   - TikTok menerapkan sistem proteksi bot (seperti WAF, captcha/challenge, dan pembatasan frekuensi request).
   - Apabila permintaan terblokir atau dibatasi, Berry akan menghentikan proses secara anggun (*graceful fallback*), menyimpan stiker yang telah terkumpul, menandai status sebagai `partial`, serta menampilkan lokasi file JSON di terminal.
3. **Masa Berlaku URL Media**:
   - URL CDN TikTok (`tiktokcdn.com`) seringkali memiliki tanda tangan keamanan dengan masa kedaluwarsa (`x-expires`). Disarankan untuk mengunduh stiker menggunakan opsi `--download-json` sesegera mungkin setelah proses scraping selesai.
4. **Keaslian Data**:
   - Berry tidak pernah mengarang atau merekayasa URL maupun ID stiker. Data yang tersimpan merupakan representasi murni dari response payload yang diterima.
