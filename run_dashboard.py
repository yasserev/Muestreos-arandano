import sys
import webbrowser
import threading
import time
import socket
import app
import data_engine

def find_available_port(start_port=5000):
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
            port += 1
    return start_port

def open_browser(url):
    time.sleep(1.5)
    print(f"\n=======================================================")
    print(f" Abriendo Dashboard en el navegador: {url}")
    print(f" Presiona CTRL+C para detener el servidor.")
    print(f"=======================================================\n")
    webbrowser.open(url)

if __name__ == "__main__":
    print("Iniciando verificación de base de datos...")
    data_engine.sync_database_if_needed()
    
    port = find_available_port(5000)
    url = f"http://127.0.0.1:{port}"
    
    # Launch browser in a background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    
    # Run Flask server
    app.app.run(host="127.0.0.1", port=port, debug=False)
