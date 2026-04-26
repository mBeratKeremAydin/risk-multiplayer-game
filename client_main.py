# Dosya Adı: client_main.py

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLineEdit, QLabel, 
                             QStackedWidget, QMessageBox, QListWidget, QGridLayout, QFrame)
from PyQt5.QtCore import Qt
from network_worker import NetworkWorker

class RiskClientApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Risk Oyunu - Multiplayer")
        self.resize(1000, 700) # Harita sığsın diye pencereyi büyüttük
        
        self.worker = NetworkWorker(host='127.0.0.1', port=5555)
        self.worker.connected_signal.connect(self.on_connected)
        self.worker.error_signal.connect(self.show_error)
        self.worker.message_received_signal.connect(self.handle_network_message)
        
        self.my_id = None
        self.my_nickname = None
        self.node_buttons = {} # Haritadaki 42 butonu burada tutacağız (Key: Node ID, Value: QPushButton)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.setup_login_page()
        self.setup_lobby_page()
        self.setup_room_page()
        self.setup_game_page() # YENİ EKLENDİ
        
        self.stacked_widget.setCurrentIndex(0)
        self.worker.start()

    # ================= 1. UI KURULUM METOTLARI =================
    
    def setup_login_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        self.status_label = QLabel("Sunucuya bağlanılıyor...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("Kullanıcı Adı (Nickname) Girin")
        self.nickname_input.setEnabled(False)
        self.login_btn = QPushButton("Giriş Yap")
        self.login_btn.setEnabled(False)
        self.login_btn.clicked.connect(self.send_login)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.nickname_input)
        layout.addWidget(self.login_btn)
        layout.addStretch()
        page.setLayout(layout)
        self.stacked_widget.addWidget(page) # Index 0

    def setup_lobby_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        self.welcome_label = QLabel("Hoş Geldin!")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.create_room_btn = QPushButton("Yeni Oda Kur")
        self.create_room_btn.clicked.connect(self.send_create_room)
        join_layout = QHBoxLayout()
        self.room_code_input = QLineEdit()
        self.room_code_input.setPlaceholderText("Oda Kodu")
        self.join_room_btn = QPushButton("Odaya Katıl")
        self.join_room_btn.clicked.connect(self.send_join_room)
        join_layout.addWidget(self.room_code_input)
        join_layout.addWidget(self.join_room_btn)
        layout.addStretch()
        layout.addWidget(self.welcome_label)
        layout.addWidget(self.create_room_btn)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Veya var olan bir odaya katıl:"))
        layout.addLayout(join_layout)
        layout.addStretch()
        page.setLayout(layout)
        self.stacked_widget.addWidget(page) # Index 1

    def setup_room_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        self.room_info_label = QLabel("Oda Kodu: Bekleniyor...")
        self.room_info_label.setAlignment(Qt.AlignCenter)
        self.players_list = QListWidget()
        self.ready_btn = QPushButton("Hazır (Ready)")
        self.ready_btn.clicked.connect(self.send_ready)
        layout.addWidget(self.room_info_label)
        layout.addWidget(QLabel("Odadaki Oyuncular:"))
        layout.addWidget(self.players_list)
        layout.addWidget(self.ready_btn)
        page.setLayout(layout)
        self.stacked_widget.addWidget(page) # Index 2

    # YENİ EKLENDİ: OYUN/HARİTA EKRANI
    def setup_game_page(self):
        page = QWidget()
        main_layout = QVBoxLayout()

        # Üst Bilgi Paneli
        info_layout = QHBoxLayout()
        self.turn_label = QLabel("Sıra: Bekleniyor...")
        self.turn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: darkred;")
        self.phase_label = QLabel("Evre: BEKLENİYOR")
        self.phase_label.setStyleSheet("font-size: 16px; font-weight: bold; color: darkblue;")
        
        info_layout.addWidget(self.turn_label)
        info_layout.addStretch()
        info_layout.addWidget(self.phase_label)

        # Harita (Node) Paneli
        # Ekranda kolay dizmek için Kıtaları Grid'lere ayırıyoruz
        map_layout = QGridLayout()
        
        # Kıtaların node numaraları (Oyun motorunda belirlediğin gibi)
        continents = {
            "Kuzey Amerika": ["0","1","2","3","4","5","6","7","8"],
            "Güney Amerika": ["9","10","11","12"],
            "Avrupa": ["19","20","21","22","23","24","25"],
            "Afrika": ["13","14","15","16","17","18"],
            "Asya": ["26","27","28","29","30","31","36","37","38","39","40","41"],
            "Avustralya": ["32","33","34","35"]
        }

        row = 0
        col = 0
        # Her kıta için bir çerçeve (Frame) oluştur
        for continent_name, nodes in continents.items():
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            frame_layout = QGridLayout()
            frame_layout.addWidget(QLabel(f"<b>{continent_name}</b>"), 0, 0, 1, 3, Qt.AlignCenter)
            
            n_row, n_col = 1, 0
            for node_id in nodes:
                # Düğüm Butonu Oluşturma
                btn = QPushButton(f"Node {node_id}\nAsker: ?")
                btn.setFixedSize(80, 60)
                btn.setStyleSheet("background-color: #DDDDDD;")
                
                # Butona tıklanınca node_id'yi fırlatacak fonksiyon bağlaması
                btn.clicked.connect(lambda checked, n_id=node_id: self.on_node_clicked(n_id))
                
                self.node_buttons[node_id] = btn
                frame_layout.addWidget(btn, n_row, n_col)
                n_col += 1
                if n_col > 2: # Her satırda 3 node olsun
                    n_col = 0
                    n_row += 1
            
            frame.setLayout(frame_layout)
            map_layout.addWidget(frame, row, col)
            col += 1
            if col > 2: # 3 kıta yan yana, sonra alt satır
                col = 0
                row += 1

        main_layout.addLayout(info_layout)
        main_layout.addLayout(map_layout)
        page.setLayout(main_layout)
        self.stacked_widget.addWidget(page) # Index 3

    # ================= 2. BUTON ETKİLEŞİMLERİ =================
    
    def send_login(self):
        nickname = self.nickname_input.text().strip()
        if nickname:
            self.worker.send_message({"action": "LOGIN", "nickname": nickname})

    def send_create_room(self):
        self.worker.send_message({"action": "CREATE_ROOM"})

    def send_join_room(self):
        code = self.room_code_input.text().strip().upper()
        if code:
            self.worker.send_message({"action": "JOIN_ROOM", "room_code": code})

    def send_ready(self):
        self.worker.send_message({"action": "READY"})
        self.ready_btn.setEnabled(False)
        self.ready_btn.setText("Bekleniyor...")

    def on_node_clicked(self, node_id):
        """Bir ülkeye/bölgeye tıklandığında çalışır."""
        print(f"[HARİTA] Node {node_id} tıklandı!")
        # İLERİDE: Burada evreye göre sunucuya mesaj atacağız
        # Örn: {"action": "ADD_TROOP", "node": node_id} veya {"action": "ATTACK", "from": x, "to": node_id}

    # ================= 3. SUNUCUDAN GELENLERİ İŞLEME =================
    
    def on_connected(self):
        self.status_label.setText("Sunucuya bağlandı! Lütfen isminizi girin.")
        self.status_label.setStyleSheet("color: green;")
        self.nickname_input.setEnabled(True)
        self.login_btn.setEnabled(True)

    def show_error(self, err_msg):
        QMessageBox.critical(self, "Hata", err_msg)

    def update_board_ui(self, board_data):
        """Sunucudan gelen harita verisini arayüze (butonlara) yansıtır."""
        for node_id, data in board_data.items():
            btn = self.node_buttons.get(node_id)
            if btn:
                owner = data["owner"]
                troops = data["troops"]
                btn.setText(f"Node {node_id}\nAsker: {troops}")
                
                # Renklendirme (Kendimiz ise yeşilimsi, düşmansa kırmızımsı)
                if owner == self.my_id:
                    btn.setStyleSheet("background-color: lightgreen; font-weight: bold;")
                else:
                    btn.setStyleSheet("background-color: lightcoral; font-weight: bold;")

    def handle_network_message(self, message):
        action = message.get("action")
        
        if action == "ERROR":
            self.show_error(message.get("message", "Bilinmeyen Hata"))
            
        elif action == "LOGIN_SUCCESS":
            self.my_id = message.get("player_id")
            self.my_nickname = message.get("nickname")
            self.welcome_label.setText(f"Hoş Geldin, {self.my_nickname}!")
            self.stacked_widget.setCurrentIndex(1)
            
        elif action == "ROOM_UPDATED":
            self.stacked_widget.setCurrentIndex(2) 
            self.room_info_label.setText(f"Oda Kodu: {message.get('room_code')}")
            self.players_list.clear()
            for p in message.get("players", []):
                durum = "Hazır" if p["is_ready"] else "Bekliyor"
                self.players_list.addItem(f"{p['nickname']} - [{durum}]")
                
        elif action == "GAME_START":
            # 1. Oyun ekranına geç
            self.stacked_widget.setCurrentIndex(3)
            
            # 2. Sıra ve Evre bilgilerini güncelle
            current_turn_id = message.get("current_turn_id")
            if current_turn_id == self.my_id:
                self.turn_label.setText("Sıra: Sende!")
                self.turn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
            else:
                self.turn_label.setText("Sıra: Rakipte")
                self.turn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
            
            self.phase_label.setText("Evre: TAKVİYE (REINFORCEMENT)")
            
            # 3. Haritayı çiz/güncelle
            self.update_board_ui(message.get("board"))

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RiskClientApp()
    window.show()
    sys.exit(app.exec_())