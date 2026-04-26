# Dosya Adı: network_worker.py

import socket
import json
from PyQt5.QtCore import QThread, pyqtSignal

class NetworkWorker(QThread):
    # Ana arayüze göndereceğimiz özel sinyaller
    connected_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    message_received_signal = pyqtSignal(dict) # Sunucudan gelen JSON (sözlük) paketini taşıyacak

    def __init__(self, host='127.0.0.1', port=5555):
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = True

    def run(self):
        """Bu metod QThread başlatıldığında (start) arka planda çalışmaya başlar."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.connected_signal.emit() # Bağlantı başarılı sinyali gönder
            
            # Sürekli sunucuyu dinle
            while self.is_running:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                
                # Gelen veriyi JSON'dan Python sözlüğüne (dict) çevir
                message = json.loads(data.decode('utf-8'))
                
                # Arayüze "Mesaj Geldi" sinyali fırlat ve paketi içine koy
                self.message_received_signal.emit(message)
                
        except Exception as e:
            self.error_signal.emit(f"Bağlantı hatası: {str(e)}")
        finally:
            if self.client_socket:
                self.client_socket.close()

    def send_message(self, data_dict):
        """Ana arayüzün sunucuya mesaj göndermek için kullanacağı fonksiyon."""
        if self.client_socket:
            try:
                json_data = json.dumps(data_dict)
                self.client_socket.sendall(json_data.encode('utf-8'))
            except Exception as e:
                print(f"[HATA] Mesaj gönderilemedi: {e}")

    def stop(self):
        self.is_running = False
        if self.client_socket:
            self.client_socket.close()