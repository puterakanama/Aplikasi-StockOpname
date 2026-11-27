from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Union
import os
import io
import socket
import openpyxl
import pandas as pd
import sys

from database import init_db, get_db_connection
import crud

app = FastAPI(title="SFP & Network Inventory Tracker - Multi-Site")

# Ensure DB initialized
init_db()

# Models for JSON APIs
class CreateLocationRequest(BaseModel):
    name: str
    code: Optional[str] = ""
    description: Optional[str] = ""

class InboundItem(BaseModel):
    serial_number: str
    part_number: str
    brand: str
    category: Optional[str] = "SFP"
    speed: Optional[str] = "10 Gbps"
    wavelength: Optional[str] = ""
    specs: Optional[str] = ""
    notes: Optional[str] = ""

class BulkInboundRequest(BaseModel):
    location_id: Union[int, str]
    pic: str
    inbound_doc: Optional[str] = ""
    items: List[InboundItem]

class TransferRequest(BaseModel):
    serial_numbers: List[str]
    to_location_id: int
    pic: str
    notes: Optional[str] = ""

class InstallRequest(BaseModel):
    serial_number: str
    switch_id: int
    port_name: str
    pic: str
    notes: Optional[str] = ""

class SwitchCreateRequest(BaseModel):
    hostname: str
    serial_number: Optional[str] = ""
    ip_address: Optional[str] = ""
    model: str
    brand: str = "Cisco"
    location_id: int
    rack_name: Optional[str] = ""
    total_ports: int = 48
    port_prefix: str = "Te1/0/"

class DeployUpsRequest(BaseModel):
    serial_number: str
    location_id: int
    rack_name: str
    pic: str
    notes: Optional[str] = ""

# --- API ENDPOINTS ---

@app.get("/api/dashboard")
def api_dashboard():
    summary = crud.get_dashboard_summary()
    summary["python_version"] = f"Python {sys.version.split()[0]}"
    summary["platform"] = sys.platform
    return summary

@app.get("/api/locations")
def api_locations():
    return crud.get_locations()

@app.post("/api/locations")
def api_create_location(req: CreateLocationRequest):
    try:
        return crud.create_location(req.name, req.code or "", req.description or "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/locations/{location_id}")
def api_delete_location(location_id: int):
    try:
        return crud.delete_location(location_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/items")
def api_items(search: str = "", status: str = "", category: str = "", location_id: Optional[str] = None, switch_id: Optional[str] = None, limit: int = 200, offset: int = 0):
    loc_id = int(location_id) if (location_id and location_id.strip().isdigit()) else None
    sw_id = int(switch_id) if (switch_id and switch_id.strip().isdigit()) else None
    st = status.strip() if status else ""
    cat = category.strip() if category else ""
    return crud.get_items(search.strip(), st, loc_id, sw_id, cat, limit, offset)

@app.get("/api/items/{serial_number}")
def api_item_detail(serial_number: str):
    item = crud.get_item_by_sn(serial_number)
    if not item:
        raise HTTPException(status_code=404, detail="Serial Number tidak ditemukan.")
    return item

@app.get("/api/available-sfps")
def api_available_sfps(location_id: Optional[str] = None, item_type: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT i.serial_number, i.part_number, i.brand, i.speed, i.category, l.name as location_name
        FROM items i
        LEFT JOIN locations l ON i.current_location_id = l.id
        WHERE i.status IN ('IN_STOCK', 'STAGING')
    """
    params = []
    if location_id and location_id.strip().isdigit():
        query += " AND (i.current_location_id = ? OR i.current_location_id = 1)"
        params.append(int(location_id))

    if item_type and "ap" in item_type.lower():
        query += " AND (i.category LIKE '%Access Point%' OR i.category LIKE '%AP%')"
    elif item_type and "ups" in item_type.lower():
        query += " AND i.category LIKE '%UPS%'"
    else:
        query += """
          AND (
              i.category LIKE '%SFP%' 
              OR i.category LIKE '%Transceiver%' 
              OR i.category LIKE '%Optic%' 
              OR i.category LIKE '%Kabel%' 
              OR i.category LIKE '%DAC%'
          )
          AND i.category NOT LIKE '%Switch%'
          AND i.category NOT LIKE '%Chassis%'
          AND i.category NOT LIKE '%Power Supply%'
          AND i.category NOT LIKE '%Linecard%'
          AND i.category NOT LIKE '%Supervisor%'
          AND i.category NOT LIKE '%UPS%'
          AND i.category NOT LIKE '%Access Point%'
        """

    query += " ORDER BY i.part_number ASC, i.serial_number ASC LIMIT 500;"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/inbound/bulk")
def api_bulk_inbound(req: BulkInboundRequest):
    items_data = [item.dict() for item in req.items]
    res = crud.bulk_inbound(items_data, req.location_id, req.pic, req.inbound_doc)
    return res

@app.post("/api/transfer")
def api_transfer(req: TransferRequest):
    try:
        res = crud.transfer_items(req.serial_numbers, req.to_location_id, req.pic, req.notes or "")
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/install")
def api_install(req: InstallRequest):
    try:
        res = crud.install_item_to_switch(req.serial_number, req.switch_id, req.port_name, req.pic, req.notes or "")
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/deploy-ups")
def api_deploy_ups(req: DeployUpsRequest):
    try:
        res = crud.deploy_ups(req.serial_number, req.location_id, req.rack_name, req.pic, req.notes or "")
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/installed-ups")
def api_installed_ups(location_id: Optional[str] = None):
    loc_id = int(location_id) if (location_id and location_id.strip().isdigit()) else None
    return crud.get_installed_ups(loc_id)

@app.get("/api/installed-aps")
def api_installed_aps(location_id: Optional[str] = None):
    loc_id = int(location_id) if (location_id and location_id.strip().isdigit()) else None
    return crud.get_installed_aps(loc_id)

@app.post("/api/unmount")
def api_unmount(serial_number: str = Form(...), pic: str = Form(...), reason: str = Form(""), return_to: str = Form("STAGING")):
    try:
        res = crud.unmount_item(serial_number, pic, reason, return_to)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/faulty")
def api_faulty(serial_number: str = Form(...), pic: str = Form(...), reason: str = Form("")):
    try:
        res = crud.mark_faulty_doa(serial_number, pic, reason)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/switches")
def api_switches(location_id: Optional[str] = None):
    loc_id = int(location_id) if (location_id and location_id.strip().isdigit()) else None
    return crud.get_switches(loc_id)

@app.get("/api/switches/{switch_id}")
def api_switch_detail(switch_id: int):
    sw = crud.get_switch_detail(switch_id)
    if not sw:
        raise HTTPException(status_code=404, detail="Switch tidak ditemukan.")
    return sw

@app.post("/api/switches")
def api_add_switch(req: SwitchCreateRequest):
    try:
        sw_id = crud.add_switch(
            hostname=req.hostname,
            ip_address=req.ip_address or "",
            model=req.model,
            brand=req.brand,
            location_id=req.location_id,
            rack_name=req.rack_name or "",
            total_ports=req.total_ports,
            port_prefix=req.port_prefix,
            serial_number=req.serial_number or ""
        )
        return {"success": True, "switch_id": sw_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/switch-candidates")
def api_switch_candidates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.serial_number, i.part_number, i.brand, i.current_location_id, l.name as location_name
        FROM items i
        LEFT JOIN locations l ON i.current_location_id = l.id
        WHERE i.category LIKE '%Switch%' 
           OR i.category LIKE '%Chassis%' 
           OR i.part_number LIKE 'N9K%' 
           OR i.part_number LIKE 'C1300%' 
           OR i.part_number LIKE 'C9300%'
           OR i.part_number LIKE 'C9200%'
           OR i.part_number LIKE 'WS-C%'
        ORDER BY i.part_number, i.serial_number ASC;
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# Stock Opname API
@app.post("/api/opname/session")
def api_create_opname(session_name: str = Form(...), location_id: int = Form(...), pic: str = Form(...)):
    s_id = crud.create_opname_session(session_name, location_id, pic)
    return {"session_id": s_id}

@app.post("/api/opname/scan")
def api_scan_opname(session_id: int = Form(...), serial_number: str = Form(...), pic: str = Form(...)):
    try:
        res = crud.scan_opname_item(session_id, serial_number, pic)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/opname/report/{session_id}")
def api_opname_report(session_id: int):
    rep = crud.get_opname_report(session_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    return rep

@app.get("/api/export-excel")
def api_export_excel():
    excel_stream = crud.export_all_to_excel()
    filename = f"Laporan_Inventaris_SFP_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export-template-excel")
def api_export_template_excel():
    template_df = pd.DataFrame([
        {
            "serial_number": "FGE29035KN5",
            "part_number": "N9K-C9508",
            "brand": "Cisco",
            "category": "Switch / Chassis",
            "speed": "Nexus 9508 8-slot Modular Chassis",
            "notes": "Chassis Core Site A"
        },
        {
            "serial_number": "FDO2943031Z",
            "part_number": "N9K-C93180YC-FX3",
            "brand": "Cisco",
            "category": "Switch / Chassis",
            "speed": "Nexus 9300 48p 10/25G, 6p 100G",
            "notes": "Leaf Switch Site A"
        },
        {
            "serial_number": "FOC29480N4E",
            "part_number": "N9K-SUP-B+",
            "brand": "Cisco",
            "category": "Module / Linecard",
            "speed": "Supervisor B+ for Nexus 9500",
            "notes": "Slot SUP 1"
        },
        {
            "serial_number": "OPM294600A7",
            "part_number": "GLC-SX-MMD=",
            "brand": "Cisco",
            "category": "SFP / Transceiver",
            "speed": "1 Gbps 850nm Multi-Mode",
            "notes": "Box SFP 1"
        },
        {
            "serial_number": "FTF2748N18B",
            "part_number": "QSFP-40/100-SRBD=",
            "brand": "Cisco",
            "category": "SFP / Transceiver",
            "speed": "100G & 40GBASE SR-BiDi",
            "notes": "Uplink Spine-Leaf"
        },
        {
            "serial_number": "FOC29480AP1",
            "part_number": "C9120AXI-E",
            "brand": "Cisco",
            "category": "Access Point (AP)",
            "speed": "Wi-Fi 6 (802.11ax) Internal Antenna",
            "notes": "AP Plafon Lobby Lt 1"
        },
        {
            "serial_number": "AS29480UP01",
            "part_number": "SRT3000XLI",
            "brand": "APC",
            "category": "UPS",
            "speed": "3000VA / 2700W On-Line 2U",
            "notes": "Rack Server 01 Site A"
        }
    ])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        template_df.to_excel(writer, sheet_name='Template Material Cisco', index=False)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Template_Import_Material_Cisco.xlsx"}
    )

@app.get("/api/opname/export-excel/{session_id}")
def api_export_opname_excel(session_id: int):
    excel_stream = crud.export_opname_to_excel(session_id)
    if not excel_stream:
        raise HTTPException(status_code=404, detail="Sesi opname tidak ditemukan.")
    filename = f"Hasil_Stock_Opname_Sesi_{session_id}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def parse_excel_universal(file_bytes, default_category="AUTO"):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    items_data = []
    new_switches = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            continue

        header_idx = -1
        col_mapping = {}

        # Scan top 25 rows to locate header row
        for idx, r in enumerate(rows[:25]):
            if not any(r):
                continue
            cells = [str(c).strip() if c is not None else '' for c in r]
            cells_clean = [c.lower().replace(' ', '').replace('_', '').replace('/', '').replace('-', '') for c in cells]

            # SN keywords: serialnumber, sn, noseri, sn1, sn2
            sn_matches = [i for i, c in enumerate(cells_clean) if c in ['serialnumber', 'sn', 'noseri', 'sn1', 'sn2']]
            if sn_matches:
                header_idx = idx
                col_mapping['sn'] = sn_matches
                col_mapping['sku'] = next((i for i, c in enumerate(cells_clean) if c in ['sku', 'partnumber', 'pn', 'itemcode', 'model']), -1)
                col_mapping['desc'] = next((i for i, c in enumerate(cells_clean) if c in ['deskripsi', 'description', 'desc', 'namabarang', 'spesifikasi', 'specs']), -1)
                col_mapping['brand'] = next((i for i, c in enumerate(cells_clean) if c in ['brand', 'merk', 'vendor']), -1)
                col_mapping['category'] = next((i for i, c in enumerate(cells_clean) if c in ['category', 'kategori', 'tipe', 'type', 'jenis']), -1)
                col_mapping['speed'] = next((i for i, c in enumerate(cells_clean) if c in ['speed', 'kecepatan']), -1)
                col_mapping['wave'] = next((i for i, c in enumerate(cells_clean) if c in ['wavelength', 'panjanggelombang', 'wave']), -1)
                col_mapping['notes'] = next((i for i, c in enumerate(cells_clean) if c in ['notes', 'catatan', 'keterangan']), -1)
                break

        if header_idx == -1:
            continue

        current_sku = ''
        current_desc = ''
        current_brand = 'Cisco'

        for r in rows[header_idx + 1:]:
            if not any(r):
                continue

            if col_mapping['sku'] != -1 and col_mapping['sku'] < len(r):
                v = r[col_mapping['sku']]
                if v is not None and str(v).strip() and str(v).strip().lower() != 'none':
                    current_sku = str(v).strip()

            if col_mapping['desc'] != -1 and col_mapping['desc'] < len(r):
                v = r[col_mapping['desc']]
                if v is not None and str(v).strip() and str(v).strip().lower() != 'none':
                    current_desc = str(v).strip()

            if col_mapping['brand'] != -1 and col_mapping['brand'] < len(r):
                v = r[col_mapping['brand']]
                if v is not None and str(v).strip() and str(v).strip().lower() != 'none':
                    current_brand = str(v).strip()

            speed_val = str(r[col_mapping['speed']]).strip() if (col_mapping['speed'] != -1 and col_mapping['speed'] < len(r) and r[col_mapping['speed']] is not None) else ''
            wave_val = str(r[col_mapping['wave']]).strip() if (col_mapping['wave'] != -1 and col_mapping['wave'] < len(r) and r[col_mapping['wave']] is not None) else ''
            notes_val = str(r[col_mapping['notes']]).strip() if (col_mapping['notes'] != -1 and col_mapping['notes'] < len(r) and r[col_mapping['notes']] is not None) else ''
            cat_val = str(r[col_mapping['category']]).strip() if (col_mapping['category'] != -1 and col_mapping['category'] < len(r) and r[col_mapping['category']] is not None) else ''

            for sn_col in col_mapping['sn']:
                if sn_col < len(r) and r[sn_col] is not None:
                    sn_val = str(r[sn_col]).strip()
                    if sn_val and sn_val.upper() not in ['SN', 'NONE', '-', 'N/A', 'SERIAL_NUMBER', 'SERIALNUMBER']:
                        # Determine category
                        if cat_val and cat_val.lower() not in ['none', 'nan', '-']:
                            cat = cat_val
                        elif default_category and default_category != 'AUTO':
                            cat = default_category
                        else:
                            # Smart classification by SKU & Description
                            text = f"{current_sku} {current_desc}".lower()
                            if any(k in text for k in ['ups', 'smart-ups', 'liebert', 'vertiv', 'apc', 'eaton', 'cyberpower', 'baterai', 'battery', 'srt3000', 'smt2200', 'gxt5']):
                                cat = 'UPS'
                            elif any(k in text for k in ['access point', 'accesspoint', 'air-ap', 'air-cap', 'c9120', 'c9130', 'c9115', 'c9105', 'ap91', 'ap28', 'ap38', 'wifi', 'wireless ap', 'air-oeap']):
                                cat = 'Access Point (AP)'
                            elif any(k in text for k in ['pac-', 'power supply', 'psu', 'fan tray', 'ac ps']):
                                cat = 'Power Supply / Fan'
                            elif any(k in text for k in ['sup-', 'supervisor', 'fabric module', 'fm-e', 'x97', 'linecard', 'modular snap', 'universal module', 'adapter panel', 'apic-pcie', 'raid controller']):
                                cat = 'Module / Linecard'
                            elif any(k in text for k in ['sfp', 'qsfp', 'transceiver', 'glc', 'wsp', 'bidi', 'sr-bidi', 'mmd', 'smd', 'csr']):
                                cat = 'SFP / Transceiver'
                            elif any(k in text for k in ['chassis', 'switch', 'n9k-c9', 'c1300', 'c9300', 'c9200', 'ws-c', 'apic-server']):
                                cat = 'Switch / Chassis'
                            elif any(k in text for k in ['dac', 'cable', 'patchcord', 'patch panel', 'kabel']):
                                cat = 'Aksesori & Kabel'
                            else:
                                cat = 'Perangkat Network'

                        specs_str = f"{speed_val} {wave_val} {current_desc}".strip()[:120]

                        items_data.append({
                            'serial_number': sn_val,
                            'part_number': current_sku or 'ITEM-PROJECT',
                            'brand': current_brand,
                            'category': cat,
                            'speed': speed_val,
                            'wavelength': wave_val,
                            'specs': specs_str,
                            'notes': notes_val or f'Sheet: {sheet_name}'
                        })

                        # Auto-register switches
                        is_sw = 'switch' in cat.lower() or 'chassis' in cat.lower() or any(k in current_sku.lower() for k in ['n9k-c', 'c1300', 'ws-c', 'c9300', 'c9200'])
                        if is_sw:
                            new_switches.append({
                                'hostname': f"{current_sku}-{sn_val[-6:]}",
                                'model': current_sku,
                                'brand': current_brand
                            })

    return items_data, new_switches

@app.post("/api/import-excel")
async def api_import_excel(file: UploadFile = File(...), location_id: str = Form(...), pic: str = Form(...), category: str = Form("AUTO"), doc_no: str = Form("IMPORT-EXCEL")):
    try:
        contents = await file.read()
        items_data, new_switches = parse_excel_universal(contents, category)

        if len(items_data) == 0:
            raise HTTPException(status_code=400, detail="Tidak ditemukan serial number yang valid pada file Excel! Pastikan ada kolom 'serial_number' atau 'SN'.")

        # Execute bulk inbound
        res = crud.bulk_inbound(items_data, location_id, pic, file.filename or doc_no)

        # Auto-register detected switches with resolved location ID
        conn = get_db_connection()
        cursor = conn.cursor()
        resolved_loc_id, _ = crud.get_or_create_location(cursor, location_id)
        conn.commit()
        conn.close()

        sw_registered = 0
        for sw in new_switches:
            try:
                crud.add_switch(sw['hostname'], '', sw['model'], sw['brand'], resolved_loc_id, 'Auto-Import Rack', 48, 'Te1/0/')
                sw_registered += 1
            except Exception:
                pass

        res["switches_auto_registered"] = sw_registered
        return res

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca Excel: {str(e)}")

# Serve Single-Page Interactive Web Application
INDEX_HTML_PATH = os.path.join(os.path.dirname(__file__), "templates", "index.html")

@app.get("/", response_class=HTMLResponse)
def index_page():
    if os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Templates not found</h1>"

if __name__ == "__main__":
    import uvicorn
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    print("=" * 60)
    print(" [OK] SFP & NETWORK INVENTORY SYSTEM - READY!")
    print(f" >> Buka di Laptop: http://localhost:8000")
    print(f" >> Buka di HP Teknisi (Wi-Fi sama): http://{local_ip}:8000")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
