# Expenses App 💰

Aplikasi manajemen pengeluaran yang dapat digunakan melalui Command Line Interface (CLI) dan Discord Bot. Aplikasi ini dilengkapi dengan fitur sinkronisasi Google Drive untuk backup data.

## ✨ Fitur

- **CLI Interface**: Kelola pengeluaran melalui command line
- **Discord Bot**: Kelola pengeluaran melalui Discord dengan UI interaktif
- **Database SQLite**: Penyimpanan data lokal yang efisien
- **Google Drive Sync**: Backup dan sinkronisasi data ke Google Drive
- **Kategorisasi**: Organisasi pengeluaran berdasarkan kategori
- **Laporan & Analisis**: View dan summary pengeluaran dengan berbagai filter

## 🚀 Instalasi

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Setup
1. Clone repository ini:
```bash
git clone <repository-url>
cd Expenses_App
```

2. Buat virtual environment:
```bash
python -m venv dc_env
```

3. Aktifkan virtual environment:
```bash
# Windows
dc_env\Scripts\activate

# Linux/Mac
source dc_env/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Setup environment variables (untuk Discord Bot):
Copy dan rename `.env.example` menjadi `.env`, lalu isi nilai yang sesuai:
```bash
cp .env.example .env
```
Atau buat file `.env` manual:
```env
DISCORD_TOKEN=your_discord_bot_token
OWNER_ID=your_discord_user_id
EXPENSES_CHANNEL_ID=your_channel_id_for_expenses_app_here
```

6. Setup Google Drive (opsional):
   - Lihat bagian [🔧 Konfigurasi → Google Drive Setup](#google-drive-setup) untuk setup lengkap
   - Dibutuhkan untuk fitur sinkronisasi data ke cloud

## 🔧 Konfigurasi

### Discord Bot Setup
1. Pergi ke [Discord Developer Portal](https://discord.com/developers/applications)
2. Buat aplikasi baru
3. Buat bot dan copy token
4. Tambahkan token ke file `.env`
5. Invite bot ke server dengan permissions yang sesuai

### Google Drive Setup
Untuk menggunakan fitur sinkronisasi dengan Google Drive, ikuti langkah berikut:

#### 1. Setup Google Cloud Console
1. Pergi ke [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru atau pilih project yang ada
3. Enable **Google Drive API**:
   - Pergi ke "APIs & Services" → "Library"
   - Cari "Google Drive API" dan klik "Enable"
4. Buat credentials (OAuth 2.0 Client ID):
   - Pergi ke "APIs & Services" → "Credentials"
   - Klik "Create Credentials" → "OAuth 2.0 Client ID"
   - Pilih "Desktop application"
   - Beri nama (contoh: "Expenses App")
   - Download file JSON credentials

#### 2. Setup File Konfigurasi
1. **client_secrets.json**: 
   - Rename file JSON yang didownload menjadi `client_secrets.json`
   - Letakkan di folder `gdrive/`

2. **settings.yaml**:
   Buat file `gdrive/settings.yaml` dengan konfigurasi berikut:
   ```yaml
   client_config_backend: settings
   client_config:
     client_id: your_client_id_from_json_file
     client_secret: your_client_secret_from_json_file

   save_credentials: True
   save_credentials_backend: file
   save_credentials_file: gdrive/credentials.json

   get_refresh_token: True

   oauth_scope:
     - https://www.googleapis.com/auth/drive
   ```

   **Tips**: Salin `client_id` dan `client_secret` dari file `client_secrets.json` yang sudah didownload.

#### 3. Autentikasi Pertama Kali
1. Ketika pertama kali menyimpan data ke Google Drive menggunakan perintah:
   ```bash
   python cli.py drive save
   ```
2. Browser akan terbuka otomatis untuk proses OAuth
3. Login dengan akun Google Anda
4. Berikan permission untuk mengakses Google Drive
5. File `credentials.json` akan dibuat otomatis untuk autentikasi selanjutnya

## 📖 Penggunaan

### CLI Interface

#### Menambah Pengeluaran
```bash
python cli.py add 2025-01-15 "Mie Ayam" 12000 "Makanan"
```

#### Menambah Multiple Pengeluaran
```bash
python cli.py addmany -e 2025-01-15 "Kopi" 5000 "Minuman" -e 2025-01-15 "Bensin" 20000 "Transportasi"
```

#### Melihat Pengeluaran
```bash
# Lihat semua pengeluaran
python cli.py view

# Filter berdasarkan tahun
python cli.py view -y 2025

# Filter berdasarkan bulan
python cli.py view -m 01

# Filter berdasarkan kategori
python cli.py view --category_name Makanan

# Limit dan offset
python cli.py view --limit 10 --offset 0

# Urutkan berdasarkan harga (descending)
python cli.py view --orderby price --desc
```

#### Summary/Laporan
```bash
# Summary berdasarkan kategori
python cli.py summary --group-by category

# Summary bulan ini
python cli.py summary --period this_month

# Summary berdasarkan tahun
python cli.py summary --group-by year --period this_year
```

#### Sync dengan Google Drive
```bash
# Simpan data ke Google Drive
python cli.py drive save

# Load data dari Google Drive
python cli.py drive load
```

### Discord Bot

1. Jalankan bot:
```bash
python discord_bot.py
```

2. Gunakan commands di Discord:
Gunakan prefix `!` (bisa diubah di kode bot) untuk commands umum bot:
```
!info
!userinfo
!foo hello world
```
Gunakan prefix `>` (bisa diubah di kode bot) untuk menjalankan commands expenses:
```
>add 2025-01-15 "Mie Ayam" 12000 "Makanan"
>view
>addmany 2025-09-17 "Bakso" 15000 "Makanan", 2025-09-17 "Bensin" 20000 "Transportasi"
```

Bot Discord menyediakan interface yang lebih user-friendly dengan:
- Pagination untuk view data
- Interactive buttons untuk navigasi
- Embedded messages yang rapi
- Filter dan sorting interaktif

### Batch Script (Windows)
Untuk kemudahan di Windows, buat file batch script:

**Opsi 1: expenses.bat**
```bat
@echo off
call dc_env\Scripts\activate.bat
python cli.py %*
```

**Opsi 2: expenses.cmd**
```cmd
@echo off
call dc_env\Scripts\activate.bat
python cli.py %*
```

Kemudian gunakan:
```bash
# Dengan ekstensi
expenses.bat add 2025-01-15 "Kopi" 5000 "Minuman"

# Atau tanpa ekstensi (jika di PATH atau direktori yang sama)
expenses add 2025-01-15 "Kopi" 5000 "Minuman"
```

#### Menambahkan ke PATH (untuk akses global)
Untuk menggunakan `expenses` dari direktori mana pun:

**Cara 1: Control Panel**
1. Buka Control Panel → System → Advanced System Settings
2. Klik "Environment Variables"
3. Di bagian "System Variables", pilih "Path" → Edit
4. Klik "New" dan tambahkan path ke folder proyek (contoh: `D:\Downloads\Expenses_App`)
5. OK → OK → OK
6. Restart Command Prompt/PowerShell

**Cara 2: PowerShell (sebagai Administrator)**
```powershell
$env:PATH += ";D:\Downloads\Expenses_App"
# Atau untuk permanent:
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";D:\Downloads\Expenses_App", "Machine")
```

## 📊 Struktur Database

Aplikasi menggunakan SQLite dengan struktur tabel:

### Table: `expenses`
- `id`: Primary key
- `date`: Tanggal pengeluaran (YYYY-MM-DD)
- `item`: Nama item/deskripsi
- `price`: Harga (integer)
- `category_id`: Foreign key ke tabel category

### Table: `category`
- `id`: Primary key
- `category_name`: Nama kategori (unique)

## 📁 Struktur Proyek

```
Expenses_App/
├── cli.py                 # Command Line Interface
├── discord_bot.py         # Discord Bot main file
├── expense_manager.py     # Core expense management logic
├── sync_drive.py         # Google Drive synchronization
├── expenses.bat          # Windows batch script
├── requirements.txt      # Python dependencies
├── cogs/
│   ├── expenses.py       # Discord bot expenses commands
│   └── general.py        # Discord bot general commands
├── data/
│   └── expenses.db       # SQLite database
├── gdrive/
│   ├── client_secrets.json    # Google API credentials
│   ├── credentials.json       # Google auth tokens
│   └── settings.yaml         # PyDrive2 settings
└── dc_env/               # Virtual environment
```

## 🛠️ Dependencies

- **discord.py**: Discord bot framework
- **python-dotenv**: Environment variables management
- **pandas**: Data manipulation dan analysis
- **pydrive2**: Google Drive API wrapper
- **tabulate**: Table formatting untuk CLI
- **google-auth-httplib2**: Google authentication
- **google-api-python-client**: Google API client

## 🤝 Contributing

1. Fork repository
2. Buat feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Buat Pull Request

## 🔄 Changelog

### v1.0.0
- CLI interface untuk manajemen pengeluaran
- Discord bot dengan UI interaktif
- Google Drive synchronization
- Database SQLite dengan kategorisasi
- Batch script untuk Windows

---

**Happy expense tracking! 📊💰**
