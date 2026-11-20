# Aplikasi SFP & Network Stock Opname Tracker (Multi-Site)

Aplikasi inventaris, pelacakan keluar-masuk, deployment port switch, dan stock opname khusus perangkat jaringan (SFP, Switch, dan aksesori) untuk project 2 lokasi berbeda dengan database **SQLite lokal**.

---

## 🚀 Cara Menjalankan Aplikasi

### Cara 1: Menggunakan File Batch (Paling Praktis)
Cukup **klik ganda (double click)** file:
`run.bat`

### Cara 2: Lewat Command Prompt / PowerShell
Buka terminal di folder ini dan jalankan:
```bash
python run.py
```

Aplikasi akan otomatis:
1. Membuka browser laptop Anda di: `http://localhost:8000`
2. Menampilkan alamat IP laptop (contoh: `http://192.168.1.50:8000`) agar **teknisi di lapangan bisa membuka aplikasi lewat browser HP** (dengan menghubungkan HP ke Wi-Fi / Hotspot yang sama).

---

## 🎯 Fitur-Fitur Utama

1. **Dashboard KPI & Progres Real-Time**:
   - Total material, stok Gudang Pusat, stok Site A, stok Site B, terpasang di switch, dan unit rusak (DOA).
   - Indikator persentase penyelesaian pemasangan switch.
   - Live Audit Log: memantau aktivitas mutasi barang detik demi detik.

2. **Pencatatan Berbasis Serial Number (Zero-Loss Guarantee)**:
   - Setiap 1 unit SFP memiliki Serial Number unik yang dicegah duplikatnya di level database.
   - Riwayat hidup lengkap (*Audit Trail Timeline*): siapa yang menerima, siapa yang membawa, dan di switch/port mana terpasang.

3. **Deployment ke Switch (Visual Port Matrix)**:
   - Tampilan visual rak dan 48 port switch fisik (hijau = terisi SFP, abu-abu = kosong).
   - Klik port switch mana saja untuk langsung memasang SFP dengan validasi otomatis agar port tidak tertimpa.

4. **Penerimaan Barang Masuk (Inbound)**:
   - Dukungan **Batch Paste**: bisa paste puluhan hingga ratusan Serial Number sekaligus (1 baris per SN).
   - Fitur **Import Excel (.xlsx)** untuk input massal.

5. **Mutasi & Transfer Antar Site**:
   - Pengiriman barang dari Gudang Pusat ke Site A / Site B atau antar site.
   - Mengubah status ke *STAGING* di lokasi tujuan dengan nomor surat jalan dan nama kurir/PIC.

6. **Barcode & QR Camera Scanner**:
   - Terintegrasi langsung dengan kamera smartphone atau webcam laptop.
   - Mengeluarkan bunyi *beep* setiap kali scan berhasil.
   - Kompatibel dengan alat **Barcode Scanner USB fisik** (tembak).

7. **Modul Stock Opname & Rekonsiliasi Otomatis**:
   - Pembuatan sesi audit fisik berkala (misal: "Opname Site A Minggu 1").
   - Menghitung otomatis: *Seharusnya Ada vs Fisik Ter-scan*.
   - Menampilkan daftar barang yang **belum ditemukan / hilang** secara instan.

8. **Export ke File Excel (.xlsx)**:
   - Satu tombol untuk mendownload seluruh data inventaris, data switch, dan riwayat audit log ke dalam format Microsoft Excel.

---

## 📂 Lokasi File Database
Seluruh data tersimpan aman di file lokal:
`stockopname.db`

*Untuk backup data, cukup salin file `stockopname.db` ini ke flashdisk atau penyimpanan cadangan Anda.*
