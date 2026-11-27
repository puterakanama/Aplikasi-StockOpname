from database import init_db, get_db_connection
from crud import bulk_inbound, add_switch, install_item_to_switch

def seed_data():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if switches exist
    cursor.execute("SELECT COUNT(*) as cnt FROM switches;")
    if cursor.fetchone()["cnt"] == 0:
        print("Seeding Switches for Site A and Site B...")
        # Site A Switches (ID 2 is Site A, ID 3 is Site B)
        sw1 = add_switch("SW-CORE-SITE-A-01", "10.10.1.1", "Catalyst 9300-48UXM", "Cisco", 2, "Rack-A01", 48, "Te1/0/")
        sw2 = add_switch("SW-DIST-SITE-A-02", "10.10.1.2", "Catalyst 9300-48S", "Cisco", 2, "Rack-A02", 48, "Te1/0/")
        sw3 = add_switch("SW-ACC-SITE-A-03", "10.10.1.3", "Catalyst 9200-48P", "Cisco", 2, "Rack-A03", 4, "Te1/1/")

        # Site B Switches
        sw4 = add_switch("SW-CORE-SITE-B-01", "10.20.1.1", "Catalyst 9300-48UXM", "Cisco", 3, "Rack-B01", 48, "Te1/0/")
        sw5 = add_switch("SW-DIST-SITE-B-02", "10.20.1.2", "Catalyst 9300-48S", "Cisco", 3, "Rack-B02", 48, "Te1/0/")

        # Seed initial sample SFP (50 units) to demonstrate realistic inventory
        sample_sfps = []
        for i in range(1, 31):
            sample_sfps.append({
                "serial_number": f"FNS27{i:04d}LR",
                "part_number": "SFP-10G-LR",
                "brand": "Cisco",
                "category": "SFP+ 10G",
                "speed": "10 Gbps",
                "wavelength": "1310nm",
                "specs": "Singlemode 10km LC Duplex",
                "notes": "Lot A Batch 1"
            })
        for i in range(31, 51):
            sample_sfps.append({
                "serial_number": f"FNS27{i:04d}SR",
                "part_number": "SFP-10G-SR",
                "brand": "Cisco",
                "category": "SFP+ 10G",
                "speed": "10 Gbps",
                "wavelength": "850nm",
                "specs": "Multimode 300m LC Duplex",
                "notes": "Lot B Batch 2"
            })

        # Inbound to Gudang Pusat (ID 1)
        bulk_inbound(sample_sfps, 1, "Logistik Admin", "PO-NET-2026-001")

        # Install 3 sample SFP to demonstrate port visualizer
        install_item_to_switch("FNS270001LR", sw1, "Te1/0/1", "Putera (Teknisi)", "Uplink ke Router")
        install_item_to_switch("FNS270002LR", sw1, "Te1/0/2", "Putera (Teknisi)", "Uplink Redundant")
        install_item_to_switch("FNS270003LR", sw1, "Te1/0/48", "Putera (Teknisi)", "Interconnect Core")

        print("Sample data seeded successfully!")
    else:
        print("Data already exists, skipping seed.")

    conn.close()

if __name__ == "__main__":
    seed_data()
