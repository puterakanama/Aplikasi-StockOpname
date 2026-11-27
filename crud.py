import sqlite3
from datetime import datetime
from database import get_db_connection
import pandas as pd
import io

def log_audit(cursor, item_id, serial_number, action, pic, from_loc="", to_loc="", target_device="", notes=""):
    cursor.execute("""
        INSERT INTO audit_logs (item_id, serial_number, action, from_location, to_location, target_device, pic, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_id, serial_number, action, from_loc, to_loc, target_device, pic, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def get_dashboard_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total counts
    cursor.execute("SELECT COUNT(*) as total FROM items;")
    total_items = cursor.fetchone()["total"]

    # Status breakdown
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM items 
        GROUP BY status;
    """)
    status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

    # Location breakdown
    cursor.execute("""
        SELECT l.id, l.name, l.code, COUNT(i.id) as count
        FROM locations l
        LEFT JOIN items i ON l.id = i.current_location_id
        GROUP BY l.id;
    """)
    location_counts = [dict(row) for row in cursor.fetchall()]

    # Switches count
    cursor.execute("SELECT COUNT(*) as total FROM switches;")
    total_switches = cursor.fetchone()["total"]

    # Installed SFP count per site
    cursor.execute("""
        SELECT l.id, l.name, COUNT(i.id) as installed_count
        FROM locations l
        LEFT JOIN items i ON l.id = i.current_location_id AND i.status = 'INSTALLED'
        GROUP BY l.id;
    """)
    installed_per_site = [dict(row) for row in cursor.fetchall()]

    # Recent Audit Activities
    cursor.execute("""
        SELECT * FROM audit_logs 
        ORDER BY timestamp DESC LIMIT 10;
    """)
    recent_logs = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        "total_items": total_items,
        "status_counts": status_counts,
        "location_counts": location_counts,
        "total_switches": total_switches,
        "installed_per_site": installed_per_site,
        "recent_logs": recent_logs
    }

def get_locations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations ORDER BY name ASC;")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def create_location(name: str, code: str = "", description: str = ""):
    name_str = (name or "").strip()
    if not name_str:
        raise Exception("Nama lokasi / site tidak boleh kosong!")
    code_str = (code.strip() if code else name_str.upper().replace(" ", "-"))[:15]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM locations WHERE LOWER(name) = LOWER(?)", (name_str,))
    if cursor.fetchone():
        conn.close()
        raise Exception(f"Lokasi '{name_str}' sudah ada!")
    cursor.execute("INSERT INTO locations (name, code, description) VALUES (?, ?, ?)", (name_str, code_str, description.strip()))
    loc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": loc_id, "name": name_str, "code": code_str}

def delete_location(loc_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if there are items in this location
    cursor.execute("SELECT COUNT(*) as cnt FROM items WHERE current_location_id = ?", (loc_id,))
    item_count = cursor.fetchone()["cnt"]
    if item_count > 0:
        conn.close()
        raise Exception(f"Lokasi tidak dapat dihapus karena masih ada {item_count} barang tercatat di lokasi ini!")

    # Check if there are switches in this location
    cursor.execute("SELECT COUNT(*) as cnt FROM switches WHERE location_id = ?", (loc_id,))
    sw_count = cursor.fetchone()["cnt"]
    if sw_count > 0:
        conn.close()
        raise Exception(f"Lokasi tidak dapat dihapus karena masih ada {sw_count} switch terdaftar di lokasi ini!")

    cursor.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Lokasi berhasil dihapus."}

def get_items(search="", status="", location_id=None, switch_id=None, category="", limit=200, offset=0):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT i.*, l.name as location_name, l.code as location_code, s.hostname as switch_hostname, s.rack_name
        FROM items i
        LEFT JOIN locations l ON i.current_location_id = l.id
        LEFT JOIN switches s ON i.installed_switch_id = s.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (i.serial_number LIKE ? OR i.part_number LIKE ? OR i.brand LIKE ? OR i.specs LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term, term, term])

    if status:
        query += " AND i.status = ?"
        params.append(status)

    if category:
        query += " AND i.category LIKE ?"
        params.append(f"%{category.strip()}%")

    if location_id:
        query += " AND i.current_location_id = ?"
        params.append(location_id)

    if switch_id:
        query += " AND i.installed_switch_id = ?"
        params.append(switch_id)

    query += " ORDER BY i.updated_at DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_item_by_sn(serial_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, l.name as location_name, l.code as location_code, s.hostname as switch_hostname, s.rack_name
        FROM items i
        LEFT JOIN locations l ON i.current_location_id = l.id
        LEFT JOIN switches s ON i.installed_switch_id = s.id
        WHERE i.serial_number = ?;
    """, (serial_number.strip(),))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return None

    item_dict = dict(item)

    # Get full history log
    cursor.execute("""
        SELECT * FROM audit_logs
        WHERE serial_number = ?
        ORDER BY timestamp DESC;
    """, (serial_number.strip(),))
    item_dict["history"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return item_dict

def get_or_create_location(cursor, location_input):
    if isinstance(location_input, int) or (isinstance(location_input, str) and location_input.strip().isdigit()):
        loc_id = int(location_input)
        cursor.execute("SELECT id, name FROM locations WHERE id = ?", (loc_id,))
        row = cursor.fetchone()
        if row:
            return row["id"], row["name"]

    name_str = str(location_input).strip() if location_input else "Lokasi Utama"
    cursor.execute("SELECT id, name FROM locations WHERE LOWER(name) = LOWER(?) OR LOWER(code) = LOWER(?)", (name_str, name_str))
    row = cursor.fetchone()
    if row:
        return row["id"], row["name"]

    code_slug = name_str.upper().replace(" ", "-")[:12]
    cursor.execute("INSERT INTO locations (name, code, description) VALUES (?, ?, ?)", (name_str, code_slug, "Lokasi Tambahan"))
    return cursor.lastrowid, name_str

def bulk_inbound(items_data, location_id, pic, inbound_doc=""):
    """
    items_data is a list of dicts:
    [{serial_number, part_number, brand, speed, wavelength, specs, notes}, ...]
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    loc_id, loc_name = get_or_create_location(cursor, location_id)

    success_count = 0
    skipped_duplicates = []
    errors = []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, item in enumerate(items_data):
        sn = item.get("serial_number", "").strip()
        if not sn:
            continue

        pn = item.get("part_number", "SFP-GENERIC").strip()
        brand = item.get("brand", "Generic").strip()
        category = item.get("category", "SFP").strip()
        speed = item.get("speed", "").strip()
        wavelength = item.get("wavelength", "").strip()
        specs = item.get("specs", "").strip()
        notes = item.get("notes", "").strip()

        try:
            cursor.execute("""
                INSERT INTO items (serial_number, part_number, brand, category, speed, wavelength, specs, 
                                   current_location_id, status, inbound_doc, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'IN_STOCK', ?, ?, ?, ?)
            """, (sn, pn, brand, category, speed, wavelength, specs, loc_id, inbound_doc, notes, now_str, now_str))
            
            item_id = cursor.lastrowid
            log_audit(cursor, item_id, sn, "INBOUND", pic, "", loc_name, "", f"Penerimaan {inbound_doc} ({pn} {brand})")
            success_count += 1

            # Auto-register to switches table if it is a switch/chassis
            is_switch = "switch" in category.lower() or "chassis" in category.lower() or any(
                k in pn.lower() for k in ["n9k-c", "c1300", "c9300", "c9200", "ws-c", "nexus", "catalyst"]
            )
            if is_switch:
                sw_host = f"{pn}-{sn[-6:]}"
                cursor.execute("SELECT id FROM switches WHERE hostname = ?", (sw_host,))
                if not cursor.fetchone():
                    try:
                        port_prefix = "Eth1/" if "n9k" in pn.lower() else "Te1/0/"
                        cursor.execute("""
                            INSERT INTO switches (hostname, ip_address, model, brand, location_id, rack_name, total_sfp_ports, port_prefix)
                            VALUES (?, '', ?, ?, ?, 'Inbound Staging', 48, ?)
                        """, (sw_host, pn, brand, loc_id, port_prefix))
                    except Exception:
                        pass
        except sqlite3.IntegrityError:
            skipped_duplicates.append(sn)
        except Exception as e:
            errors.append(f"Row {idx+1} ({sn}): {str(e)}")

    conn.commit()
    conn.close()
    return {
        "success_count": success_count,
        "skipped_duplicates": skipped_duplicates,
        "errors": errors
    }

def transfer_items(serial_numbers, to_location_id, pic, notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM locations WHERE id = ?", (to_location_id,))
    target_loc = cursor.fetchone()
    if not target_loc:
        conn.close()
        raise ValueError("Lokasi tujuan tidak ditemukan.")
    to_name = target_loc["name"]

    updated_count = 0
    not_found = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sn in serial_numbers:
        sn = sn.strip()
        if not sn:
            continue

        cursor.execute("SELECT i.id, i.current_location_id, l.name as loc_name FROM items i LEFT JOIN locations l ON i.current_location_id = l.id WHERE i.serial_number = ?", (sn,))
        row = cursor.fetchone()
        if not row:
            not_found.append(sn)
            continue

        from_name = row["loc_name"]
        item_id = row["id"]

        # Update item location & status to STAGING at destination
        cursor.execute("""
            UPDATE items 
            SET current_location_id = ?, status = 'STAGING', updated_at = ?
            WHERE id = ?
        """, (to_location_id, now_str, item_id))

        log_audit(cursor, item_id, sn, "TRANSFER", pic, from_name, to_name, "", notes)
        updated_count += 1

    conn.commit()
    conn.close()
    return {"updated_count": updated_count, "not_found": not_found, "destination": to_name}

def install_item_to_switch(serial_number, switch_id, port_name, pic, notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Check switch
    cursor.execute("SELECT s.*, l.name as loc_name FROM switches s LEFT JOIN locations l ON s.location_id = l.id WHERE s.id = ?", (switch_id,))
    sw = cursor.fetchone()
    if not sw:
        conn.close()
        raise ValueError("Perangkat Switch tidak ditemukan.")

    # 2. Check if port is already occupied
    cursor.execute("""
        SELECT serial_number FROM items 
        WHERE installed_switch_id = ? AND installed_port = ? AND status = 'INSTALLED';
    """, (switch_id, port_name.strip()))
    occupied = cursor.fetchone()
    if occupied:
        conn.close()
        raise ValueError(f"Port {port_name} pada Switch {sw['hostname']} sudah terisi oleh SFP SN: {occupied['serial_number']}! Lepaskan dulu sebelum memasang yang baru.")

    # 3. Check item SFP
    cursor.execute("SELECT * FROM items WHERE serial_number = ?", (serial_number.strip(),))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise ValueError(f"Barang dengan Serial Number '{serial_number}' tidak ditemukan di database.")

    cat = (item["category"] or "").lower()
    if "switch" in cat or "chassis" in cat or "power supply" in cat or "linecard" in cat or "supervisor" in cat or "ups" in cat:
        conn.close()
        raise ValueError(f"Serial Number '{serial_number}' adalah '{item['category']}' ({item['part_number']}), bukan modul SFP atau Access Point! Perangkat ini tidak dapat dipasang ke port switch.")

    if item["status"] == "INSTALLED":
        conn.close()
        raise ValueError(f"SFP SN '{serial_number}' sudah berstatus INSTALLED di switch lain! Mohon lepaskan terlebih dahulu.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update item
    cursor.execute("""
        UPDATE items 
        SET status = 'INSTALLED',
            current_location_id = ?,
            installed_switch_id = ?,
            installed_port = ?,
            installed_by = ?,
            installed_at = ?,
            updated_at = ?
        WHERE id = ?
    """, (sw["location_id"], switch_id, port_name.strip(), pic, now_str, now_str, item["id"]))

    log_audit(cursor, item["id"], serial_number.strip(), "INSTALLED", pic,
              f"Site {sw['loc_name']}", f"Switch {sw['hostname']}",
              f"{sw['hostname']} ({port_name.strip()})", notes)

    conn.commit()
    conn.close()
    return {"success": True, "hostname": sw["hostname"], "port": port_name.strip(), "sn": serial_number}

def unmount_item(serial_number, pic, reason="Unmount / Ganti", return_to_status="STAGING"):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT i.*, s.hostname FROM items i LEFT JOIN switches s ON i.installed_switch_id = s.id WHERE i.serial_number = ?", (serial_number.strip(),))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise ValueError("Item tidak ditemukan.")

    prev_switch = item["hostname"] or "Switch"
    prev_port = item["installed_port"] or "-"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE items 
        SET status = ?,
            installed_switch_id = NULL,
            installed_port = NULL,
            updated_at = ?
        WHERE id = ?
    """, (return_to_status, now_str, item["id"]))

    log_audit(cursor, item["id"], serial_number.strip(), "UNMOUNT", pic,
              f"{prev_switch}:{prev_port}", return_to_status, f"{prev_switch}:{prev_port}", reason)

    conn.commit()
    conn.close()
    return {"success": True, "status": return_to_status}

def mark_faulty_doa(serial_number, pic, reason=""):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items WHERE serial_number = ?", (serial_number.strip(),))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise ValueError("Item tidak ditemukan.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE items 
        SET status = 'FAULTY_DOA',
            installed_switch_id = NULL,
            installed_port = NULL,
            updated_at = ?
        WHERE id = ?
    """, (now_str, item["id"]))

    log_audit(cursor, item["id"], serial_number.strip(), "FAULTY_DOA", pic,
              item["status"], "FAULTY_DOA", "", f"Gejala/Alasan: {reason}")

    conn.commit()
    conn.close()
    return {"success": True, "sn": serial_number}

# Switches Management
def get_switches(location_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT s.*, l.name as location_name, l.code as location_code,
               COUNT(i.id) as installed_sfp_count
        FROM switches s
        LEFT JOIN locations l ON s.location_id = l.id
        LEFT JOIN items i ON s.id = i.installed_switch_id AND i.status = 'INSTALLED'
        WHERE 1=1
    """
    params = []
    if location_id:
        query += " AND s.location_id = ?"
        params.append(location_id)
    query += " GROUP BY s.id ORDER BY s.hostname ASC;"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_switch_detail(switch_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, l.name as location_name, l.code as location_code
        FROM switches s
        LEFT JOIN locations l ON s.location_id = l.id
        WHERE s.id = ?;
    """, (switch_id,))
    sw = cursor.fetchone()
    if not sw:
        conn.close()
        return None
    sw_dict = dict(sw)

    # Get installed ports
    cursor.execute("""
        SELECT id, serial_number, part_number, brand, speed, installed_port, installed_by, installed_at
        FROM items
        WHERE installed_switch_id = ? AND status = 'INSTALLED';
    """, (switch_id,))
    sw_dict["installed_items"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return sw_dict

def add_switch(hostname, ip_address, model, brand, location_id, rack_name, total_ports=48, port_prefix="Te1/0/", serial_number=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO switches (hostname, serial_number, ip_address, model, brand, location_id, rack_name, total_sfp_ports, port_prefix)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (hostname.strip(), (serial_number or "").strip(), ip_address.strip(), model.strip(), brand.strip(), location_id, rack_name.strip(), total_ports, port_prefix.strip()))
        conn.commit()
        sw_id = cursor.lastrowid
        conn.close()
        return sw_id
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Switch dengan hostname '{hostname}' sudah terdaftar!")

def deploy_ups(serial_number, location_id, rack_name, pic, notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM locations WHERE id = ?", (location_id,))
    loc = cursor.fetchone()
    if not loc:
        conn.close()
        raise ValueError("Lokasi Site tidak ditemukan.")

    cursor.execute("SELECT * FROM items WHERE serial_number = ?", (serial_number.strip(),))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise ValueError(f"UPS dengan Serial Number '{serial_number}' tidak ditemukan di database.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE items 
        SET status = 'INSTALLED',
            current_location_id = ?,
            installed_port = ?,
            installed_by = ?,
            installed_at = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
    """, (location_id, rack_name.strip(), pic.strip(), now_str, notes.strip(), now_str, item["id"]))

    log_audit(cursor, item["id"], serial_number.strip(), "INSTALLED", pic.strip(),
              "Gudang / Inventory", f"Site {loc['name']}",
              f"UPS Rack: {rack_name.strip()}", notes.strip())

    conn.commit()
    conn.close()
    return {"success": True, "message": f"UPS {serial_number} berhasil dipasang di {loc['name']} ({rack_name})."}

def get_installed_ups(location_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT i.*, l.name as location_name
        FROM items i
        LEFT JOIN locations l ON i.current_location_id = l.id
        WHERE i.category LIKE '%UPS%' AND i.status = 'INSTALLED'
    """
    params = []
    if location_id:
        query += " AND i.current_location_id = ?"
        params.append(location_id)
    query += " ORDER BY i.updated_at DESC;"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_installed_aps(location_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT i.*, l.name as location_name, s.hostname as switch_hostname
        FROM items i
        LEFT JOIN locations l ON i.current_location_id = l.id
        LEFT JOIN switches s ON i.installed_switch_id = s.id
        WHERE (i.category LIKE '%AP%' OR i.category LIKE '%Access Point%' OR i.category LIKE '%WiFi%')
          AND i.status = 'INSTALLED'
    """
    params = []
    if location_id:
        query += " AND i.current_location_id = ?"
        params.append(location_id)
    query += " ORDER BY i.updated_at DESC;"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# Stock Opname Session & Reconciliation
def create_opname_session(session_name, location_id, pic):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO stock_opname_sessions (session_name, location_id, created_by)
        VALUES (?, ?, ?);
    """, (session_name.strip(), location_id, pic.strip()))
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id

def scan_opname_item(session_id, serial_number, pic):
    conn = get_db_connection()
    cursor = conn.cursor()

    sn = serial_number.strip()

    # Get session details
    cursor.execute("SELECT * FROM stock_opname_sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        raise ValueError("Sesi Opname tidak ditemukan.")

    # Check if this item is in database and at this location
    cursor.execute("SELECT * FROM items WHERE serial_number = ?", (sn,))
    item = cursor.fetchone()

    is_match = 0
    note = ""
    if not item:
        is_match = 0
        note = "Item TIDAK TERDAFTAR di sistem!"
    elif item["current_location_id"] != session["location_id"]:
        is_match = 0
        note = f"Item terdaftar di lokasi lain (ID Lokasi: {item['current_location_id']})!"
    else:
        is_match = 1
        note = f"Cocok: {item['part_number']} ({item['status']})"

    cursor.execute("""
        INSERT INTO stock_opname_scans (session_id, serial_number, scanned_by, is_match, notes)
        VALUES (?, ?, ?, ?, ?);
    """, (session_id, sn, pic.strip(), is_match, note))

    conn.commit()
    conn.close()
    return {"serial_number": sn, "is_match": is_match, "notes": note}

def get_opname_report(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sos.*, l.name as location_name 
        FROM stock_opname_sessions sos
        LEFT JOIN locations l ON sos.location_id = l.id
        WHERE sos.id = ?;
    """, (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        return None

    # Expected items at this location
    cursor.execute("""
        SELECT serial_number, part_number, brand, status, installed_port
        FROM items
        WHERE current_location_id = ?;
    """, (session["location_id"],))
    expected_items = {r["serial_number"]: dict(r) for r in cursor.fetchall()}

    # Scanned items
    cursor.execute("""
        SELECT serial_number, scanned_by, scanned_at, is_match, notes
        FROM stock_opname_scans
        WHERE session_id = ?
        ORDER BY scanned_at DESC;
    """, (session_id,))
    scanned_rows = [dict(r) for r in cursor.fetchall()]

    scanned_sns = set([r["serial_number"] for r in scanned_rows])
    expected_sns = set(expected_items.keys())

    matched_sns = scanned_sns.intersection(expected_sns)
    missing_sns = expected_sns.difference(scanned_sns) # Barang di sistem tapi belum ter-scan
    unexpected_sns = scanned_sns.difference(expected_sns) # Barang ter-scan tapi bukan milik lokasi ini / belum terdaftar

    conn.close()
    return {
        "session": dict(session),
        "total_expected": len(expected_sns),
        "total_scanned": len(scanned_sns),
        "total_matched": len(matched_sns),
        "total_missing": len(missing_sns),
        "total_unexpected": len(unexpected_sns),
        "scanned_details": scanned_rows,
        "missing_items": [expected_items[sn] for sn in missing_sns],
        "unexpected_sns": list(unexpected_sns)
    }

def export_all_to_excel():
    conn = get_db_connection()
    items_df = pd.read_sql_query("""
        SELECT i.serial_number as "Serial Number",
               i.part_number as "Part Number",
               i.brand as "Brand",
               i.category as "Kategori",
               i.speed as "Speed",
               l.name as "Lokasi Saat Ini",
               i.status as "Status",
               s.hostname as "Switch Terpasang",
               i.installed_port as "Port Switch",
               i.installed_by as "Teknisi Pemasang",
               i.installed_at as "Waktu Pasang",
               i.notes as "Catatan",
               i.updated_at as "Terakhir Diperbarui"
        FROM items i
        LEFT JOIN locations l ON i.current_location_id = l.id
        LEFT JOIN switches s ON i.installed_switch_id = s.id
        ORDER BY i.updated_at DESC;
    """, conn)

    switches_df = pd.read_sql_query("""
        SELECT s.hostname as "Hostname Switch",
               s.serial_number as "Serial Number",
               s.ip_address as "IP Management",
               s.model as "Model Switch",
               s.brand as "Brand",
               l.name as "Lokasi Site",
               s.rack_name as "Nama Rak",
               s.total_sfp_ports as "Total Port SFP",
               s.port_prefix as "Prefix Port",
               s.created_at as "Tanggal Didaftarkan"
        FROM switches s
        LEFT JOIN locations l ON s.location_id = l.id
        ORDER BY s.hostname ASC;
    """, conn)

    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        items_df.to_excel(writer, sheet_name='Data Material & SFP', index=False)
        switches_df.to_excel(writer, sheet_name='Daftar Switch Target', index=False)

    output.seek(0)
    return output

def export_opname_to_excel(session_id):
    rep = get_opname_report(session_id)
    if not rep:
        return None

    # Summary df
    summary_data = [
        {"Parameter": "Nama Sesi Opname", "Nilai": rep["session"]["session_name"]},
        {"Parameter": "Lokasi Audit", "Nilai": rep["session"]["location_name"]},
        {"Parameter": "Auditor Lead", "Nilai": rep["session"]["created_by"]},
        {"Parameter": "Tanggal Sesi", "Nilai": rep["session"]["created_at"]},
        {"Parameter": "Seharusnya Ada di Sistem", "Nilai": rep["total_expected"]},
        {"Parameter": "Total Fisik Ter-scan", "Nilai": rep["total_scanned"]},
        {"Parameter": "Cocok (Matched)", "Nilai": rep["total_matched"]},
        {"Parameter": "HILANG / Belum Ter-scan", "Nilai": rep["total_missing"]},
        {"Parameter": "Barang Nyasar / Tak Terdaftar", "Nilai": rep["total_unexpected"]}
    ]
    summary_df = pd.DataFrame(summary_data)

    # Missing items df
    missing_df = pd.DataFrame(rep["missing_items"])
    if not missing_df.empty:
        missing_df.columns = ["Serial Number", "Part Number", "Brand", "Status Terakhir", "Port Terpasang"]

    # Scanned items df
    scanned_df = pd.DataFrame(rep["scanned_details"])
    if not scanned_df.empty:
        scanned_df.columns = ["Serial Number", "Auditor", "Waktu Scan", "Status Cocok", "Keterangan"]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Ringkasan Opname', index=False)
        if not missing_df.empty:
            missing_df.to_excel(writer, sheet_name='Daftar Barang Belum Ditemukan', index=False)
        if not scanned_df.empty:
            scanned_df.to_excel(writer, sheet_name='Riwayat Fisik Ter-scan', index=False)

    output.seek(0)
    return output
