import os
import shutil
import sqlite3
from database import DB_PATH, init_db

def reset_database():
    print("=" * 65)
    print(" RESET DATABASE STOCK OPNAME KE KONDISI AWAL (BERSIH / KOSONG)")
    print("=" * 65)
    
    if os.path.exists(DB_PATH):
        backup_path = os.path.join(os.path.dirname(DB_PATH), "stockopname_backup_sebelum_reset.db")
        try:
            shutil.copy2(DB_PATH, backup_path)
            print(f" [OK] Data lama telah dibackup aman ke:\n      -> {backup_path}")
        except Exception as e:
            print(f" [!] Gagal membuat file backup: {e}")

        # Checkpoint WAL before clearing
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA wal_checkpoint(FULL);")
            conn.close()
        except Exception:
            pass

        # Clear data from tables
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stock_opname_scans;")
            cursor.execute("DELETE FROM stock_opname_sessions;")
            cursor.execute("DELETE FROM audit_logs;")
            cursor.execute("DELETE FROM items;")
            cursor.execute("DELETE FROM switches;")
            cursor.execute("DELETE FROM locations;")
            # Reset sqlite_sequence for autoincrement IDs
            cursor.execute("DELETE FROM sqlite_sequence;")
            conn.commit()
            conn.close()
            print(" [OK] Seluruh data items, switches, log audit, dan sesi opname telah dibersihkan.")
        except Exception as e:
            print(f" [!] Error saat membersihkan tabel: {e}")

    # Re-initialize clean tables & default locations
    init_db()
    
    # Verify counts
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM items;")
    items_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM switches;")
    switches_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM locations;")
    locations_count = cursor.fetchone()[0]
    conn.close()

    print("-" * 65)
    print(f" Status Database Sekarang:")
    print(f"  - Total Barang / SFP / Switch : {items_count} (Kosong)")
    print(f"  - Total Switch Terpasang      : {switches_count} (Kosong)")
    print(f"  - Lokasi Default Tersedia     : {locations_count} (Gudang Pusat, Site A, Site B)")
    print("=" * 65)
    print(" Database siap dipakai dari nol di laptop baru!")

if __name__ == "__main__":
    reset_database()
