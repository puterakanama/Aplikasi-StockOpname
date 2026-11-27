import socket
import webbrowser
import threading
import time
import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows CMD
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000

    print("=" * 65)
    print(" [OK] COMPNET SFP & NETWORK INVENTORY TRACKER (MULTI-SITE)")
    print("=" * 65)
    print(f" >> Versi Python Aktif : Python {sys.version.split()[0]} (64-bit)")
    print(f" >> Buka di Laptop ini : http://localhost:{port}")
    print(f" >> Buka di HP Teknisi : http://{local_ip}:{port}")
    print("    (Pastikan HP terhubung ke Wi-Fi / Hotspot yang sama)")
    print("=" * 65)
    print(" Menjalankan server lokal dengan Auto-Reload...")
    print("-" * 65)

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
