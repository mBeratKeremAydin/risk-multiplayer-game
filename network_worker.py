# Dosya Adı: network_worker.py
# İşlevi: İstemcinin arka planda (ayrı bir thread'de) sunucu ile olan TCP iletişimini sağlar.
#         PyQt5'in ana UI thread'inin (arayüzün) donmasını engeller.

import socket
import json
from PyQt5.QtCore import QThread, pyqtSignal

class NetworkWorker(QThread):
    # Ana arayüze (client_main.py) göndereceğimiz özel PyQt sinyalleri
    connected_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    message_received_signal = pyqtSignal(dict) # Sunucudan gelen JSON paketini (dict) taşır

    def __init__(self, host='127.0.0.1', port=5555):
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = True

    def run(self):
        """
        QThread başlatıldığında (.start() çağrıldığında) çalışır.
        Sonsuz bir döngüde sunucudan gelen mesajları dinler.
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.connected_signal.emit() # Bağlantı başarılı sinyali gönder
            
            # Sürekli sunucuyu dinle
            buffer = ""
            while self.is_running:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                
                buffer += data.decode('utf-8')
                
                # Buffer içinde \n olduğu sürece tam bir paket gelmiş demektir
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Gelen veriyi JSON formatından Python sözlüğüne (dict) çevir
                    message = json.loads(line)
                    
                    # Arayüze "Mesaj Geldi" sinyali fırlat ve paketi argüman olarak gönder
                    self.message_received_signal.emit(message)
                
        except Exception as e:
            self.error_signal.emit(f"Bağlantı hatası: {str(e)}")
        finally:
            if self.client_socket:
                self.client_socket.close()

    def send_message(self, data_dict):
        """
        Ana arayüzün (client_main.py) sunucuya veri göndermek için kullandığı fonksiyon.
        """
        if self.client_socket:
            try:
                # Python sözlüğünü JSON string'e çevir ve sonuna sınırlayıcı (\n) ekle
                json_data = json.dumps(data_dict) + "\n"
                self.client_socket.sendall(json_data.encode('utf-8'))
            except Exception as e:
                print(f"[HATA] Mesaj gönderilemedi: {e}")

    def stop(self):
        """Bağlantıyı ve dinleme döngüsünü güvenli bir şekilde kapatır."""
        self.is_running = False
        if self.client_socket:
            self.client_socket.close()