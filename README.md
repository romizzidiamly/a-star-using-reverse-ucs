# Sistem Optimasi Rute Pengiriman Multi-Kriteria

Aplikasi terminal untuk mencari rute pengiriman menggunakan algoritma A* dengan pertimbangan jarak, waktu, kendaraan, bahan bakar, dan paket layanan. Hasil penggunaan dicatat ke CSV dan dapat divisualisasikan sebagai peta jaringan.

## Persyaratan

- Python 3.11 atau lebih baru
- pip

## Instalasi

Buat dan aktifkan virtual environment, lalu pasang dependency:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
```

## Menjalankan

Jalankan aplikasi interaktif dari root repository:

```powershell
python tugas_terstruktur_pka.py
```

Aplikasi meminta lokasi awal dan tujuan, jenis kendaraan, bahan bakar, serta paket layanan. Ringkasan eksperimen disimpan ke `output/eksperimen.csv`.

Untuk membuat visualisasi dari data eksperimen:

```powershell
python -m pka_route.visualisasi
```

Untuk membangun ulang data graf:

```powershell
python -m pka_route.graph_builder
```

## Struktur Project

```text
.
├── pka_route/       # Logika pencarian, data graf, metrik, dan visualisasi
├── output/          # CSV hasil dan gambar visualisasi
├── requirements.txt
└── tugas_terstruktur_pka.py
```