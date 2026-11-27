import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "stockopname.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency & performance
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Locations (Gudang Pusat, Site A, Site B)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        code TEXT UNIQUE NOT NULL,
        description TEXT,
        address TEXT
    );
    """)

    # 2. Switches / Network Devices Target
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS switches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostname TEXT UNIQUE NOT NULL,
        serial_number TEXT,
        ip_address TEXT,
        model TEXT,
        brand TEXT DEFAULT 'Cisco',
        location_id INTEGER NOT NULL REFERENCES locations(id),
        rack_name TEXT,
        total_sfp_ports INTEGER DEFAULT 48,
        port_prefix TEXT DEFAULT 'Te1/0/',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seamless schema migration if serial_number column missing
    try:
        cursor.execute("ALTER TABLE switches ADD COLUMN serial_number TEXT;")
    except Exception:
        pass

    # 3. Items (SFP & Hardware Master)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number TEXT UNIQUE NOT NULL,
        part_number TEXT NOT NULL,
        brand TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'SFP',
        speed TEXT,
        wavelength TEXT,
        connector_type TEXT DEFAULT 'LC',
        specs TEXT,
        current_location_id INTEGER NOT NULL REFERENCES locations(id),
        status TEXT NOT NULL DEFAULT 'IN_STOCK',
        installed_switch_id INTEGER REFERENCES switches(id),
        installed_port TEXT,
        installed_by TEXT,
        installed_at TIMESTAMP,
        inbound_doc TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Audit Trail Log (Immutable - Tidak Boleh Dihapus)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        serial_number TEXT NOT NULL,
        action TEXT NOT NULL,
        from_location TEXT,
        to_location TEXT,
        target_device TEXT,
        pic TEXT NOT NULL,
        notes TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Stock Opname Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_opname_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_name TEXT NOT NULL,
        location_id INTEGER NOT NULL REFERENCES locations(id),
        target_category TEXT DEFAULT 'ALL',
        status TEXT DEFAULT 'OPEN',
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP
    );
    """)

    # 6. Stock Opname Scans
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_opname_scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES stock_opname_sessions(id) ON DELETE CASCADE,
        serial_number TEXT NOT NULL,
        scanned_by TEXT NOT NULL,
        scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_match INTEGER DEFAULT 0,
        notes TEXT
    );
    """)

    # Create Indexes for fast barcode scanning & queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_sn ON items(serial_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_location ON items(current_location_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_sn ON audit_logs(serial_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_opname_scan ON stock_opname_scans(session_id, serial_number);")

    # Default locations: do not seed dummy locations so user can manage their own sites
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
