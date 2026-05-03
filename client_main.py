import sys
import os
from PyQt5 import uic
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QPushButton, QLineEdit, QLabel,
                             QStackedWidget, QMessageBox, QListWidget, QTextEdit, QInputDialog)
from PyQt5.QtCore import Qt
from network_worker import NetworkWorker

class RiskClientApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Risk Oyunu - Multiplayer")
        self.resize(1100, 700) # Log ekranı sığsın diye genişliği biraz artırdık
        
        self.worker = NetworkWorker(host='127.0.0.1', port=5555)
        self.worker.connected_signal.connect(self.on_connected)
        self.worker.error_signal.connect(self.show_error)
        self.worker.message_received_signal.connect(self.handle_network_message)
        
        # OYUNCU VE OYUN DURUMU DEĞİŞKENLERİ
        self.my_id = None
        self.my_nickname = None
        self.my_color = None
        
        self.current_phase = "REINFORCEMENT"
        self.is_my_turn = False
        self.current_board = {} 

        # --- KOMŞULUK TABLOSU ---
        self.neighbors = {
            "0": ["1", "3", "26"], "1": ["0", "2", "3", "4"], "2": ["1", "4", "5", "19"],
            "3": ["0", "1", "4", "6"], "4": ["1", "2", "3", "5", "6", "7"], "5": ["2", "4", "7", "8"],
            "6": ["3", "4", "7", "8"], "7": ["4", "5", "6", "8"], "8": ["5", "6", "7", "9"],
            "9": ["8", "10", "11", "12"], "10": ["9", "11", "12"], "11": ["9", "10", "12", "13"], "12": ["9", "10", "11"],
            "13": ["11", "14", "15", "16", "20", "24"], "14": ["13", "15", "17"],
            "15": ["13", "14", "16", "17", "18", "36"], "16": ["13", "15", "17", "18"],
            "17": ["14", "15", "16", "18"], "18": ["15", "16", "17"],
            "19": ["2", "20", "21", "22"], "20": ["13", "19", "21", "22", "23", "24"],
            "21": ["19", "20", "22", "23", "24"], "22": ["19", "20", "21", "23", "24", "25"],
            "23": ["20", "21", "22", "24", "25", "27"], "24": ["13", "20", "21", "22", "23", "25", "36"],
            "25": ["22", "23", "24", "27", "28", "36"],
            "26": ["0", "27", "28", "29", "31"], "27": ["23", "25", "26", "28", "29", "30"],
            "28": ["25", "26", "27", "29", "30", "31", "36"], "29": ["26", "27", "28", "30", "31", "36", "37"],
            "30": ["27", "28", "29", "31", "36", "37", "38"], "31": ["26", "28", "29", "30", "37", "38", "40"],
            "36": ["15", "24", "25", "28", "29", "30", "37", "38", "39"], "37": ["29", "30", "31", "36", "38", "39", "40"],
            "38": ["30", "31", "36", "37", "39", "41"], "39": ["36", "37", "38", "40", "41"],
            "40": ["31", "37", "39", "41"], "41": ["32", "38", "39", "40"],
            "32": ["33", "34", "35", "41"], "33": ["32", "34", "35"],
            "34": ["32", "33", "35"], "35": ["32", "33", "34"]
        }
        
        self.selected_attacker = None 
        self.selected_defender = None 

        self.node_buttons = {} 
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.setup_login_page()
        self.setup_lobby_page()
        self.setup_room_page()
        self.setup_game_page()
        self.setup_gameover_page()   # Sayfa index: 4

        self.stacked_widget.setCurrentIndex(0)
        self.worker.start()

    # ================= 1. UI KURULUM METOTLARI =================

    
    def setup_login_page(self):
        ui_path = os.path.join(os.path.dirname(__file__), "Form", "login_form.ui")
        if not os.path.exists(ui_path):
            raise FileNotFoundError("Form/login_form.ui bulunamadı. Lütfen kontrol edin.")

        page = uic.loadUi(ui_path)

        self.status_label = page.findChild(QLabel, "status_label")
        self.nickname_input = page.findChild(QLineEdit, "nickname_input")
        self.login_btn = page.findChild(QPushButton, "login_btn")

        if not (self.nickname_input and self.login_btn):
            raise ValueError(
                "login_form.ui içinde en az nickname_input ve login_btn objectName alanları olmalı."
            )

        if self.status_label is None:
            self.status_label = QLabel("Sunucuya bağlanılıyor...", page)
            self.status_label.setObjectName("status_label")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setGeometry(85, 150, 230, 24)

        self.nickname_input.setEnabled(False)
        self.login_btn.setEnabled(False)
        self.nickname_input.returnPressed.connect(self.send_login)
        self.login_btn.clicked.connect(self.send_login)

        self.stacked_widget.addWidget(page)

    def setup_lobby_page(self):
        ui_path = os.path.join(os.path.dirname(__file__), "Form", "lobby_form.ui")
        if not os.path.exists(ui_path):
            raise FileNotFoundError("Form/lobby_form.ui bulunamadı. Lütfen kontrol edin.")

        page = uic.loadUi(ui_path)

        self.welcome_label = page.findChild(QLabel, "welcome_label")
        self.create_room_btn = page.findChild(QPushButton, "create_room_btn")
        self.room_code_input = page.findChild(QLineEdit, "room_code_input")
        self.join_room_btn = page.findChild(QPushButton, "join_room_btn")

        if not (self.welcome_label and self.create_room_btn and self.room_code_input and self.join_room_btn):
            raise ValueError(
                "lobby_form.ui içinde welcome_label, create_room_btn, room_code_input ve join_room_btn objectName alanları olmalı."
            )

        self.create_room_btn.clicked.connect(self.send_create_room)
        self.join_room_btn.clicked.connect(self.send_join_room)
        self.room_code_input.returnPressed.connect(self.send_join_room)

        self.stacked_widget.addWidget(page)

    def setup_room_page(self):
        ui_path = os.path.join(os.path.dirname(__file__), "Form", "room_form.ui")
        if not os.path.exists(ui_path):
            raise FileNotFoundError("Form/room_form.ui bulunamadı.")
            
        page = uic.loadUi(ui_path)
        
        self.room_info_label = page.findChild(QLabel, "room_info_label")
        self.players_list = page.findChild(QListWidget, "players_list")
        self.ready_btn = page.findChild(QPushButton, "ready_btn")
        
        self.ready_btn.clicked.connect(self.send_ready)
        self.stacked_widget.addWidget(page)

    def setup_game_page(self):
        ui_path = os.path.join(os.path.dirname(__file__), "Form", "game_form.ui")
        if not os.path.exists(ui_path):
            raise FileNotFoundError("Form/game_form.ui bulunamadı.")
            
        page = uic.loadUi(ui_path)

        self.color_label = page.findChild(QLabel, "color_label")
        self.turn_label = page.findChild(QLabel, "turn_label")
        self.phase_label = page.findChild(QLabel, "phase_label")
        self.time_label = page.findChild(QLabel, "time_label")
        self.troops_label = page.findChild(QLabel, "troops_label")
        
        self.action_button = page.findChild(QPushButton, "action_button")
        self.action_button.clicked.connect(self.on_action_button_clicked)
        
        self.battle_log = page.findChild(QTextEdit, "battle_log")

        # Butonları dinamik olarak yakalayıp sinyallerini bağla
        for i in range(42):
            node_id = str(i)
            btn = page.findChild(QPushButton, f"node_{node_id}")
            if btn:
                btn.clicked.connect(lambda checked, n_id=node_id: self.on_node_clicked(n_id))
                self.node_buttons[node_id] = btn

        self.stacked_widget.addWidget(page)

    def setup_gameover_page(self):
        """Oyun bitiş ekranını Form/gameover_form.ui dosyasından yükler."""
        ui_path = os.path.join(os.path.dirname(__file__), "Form", "gameover_form.ui")
        if not os.path.exists(ui_path):
            raise FileNotFoundError("Form/gameover_form.ui bulunamadı.")

        page = uic.loadUi(ui_path)

        self.gameover_winner_label = page.findChild(QLabel, "gameover_winner_label")
        replay_btn = page.findChild(QPushButton, "replay_btn")
        close_btn  = page.findChild(QPushButton, "close_btn")

        replay_btn.clicked.connect(self.on_replay_clicked)
        close_btn.clicked.connect(self.close)

        self.stacked_widget.addWidget(page)

    def show_gameover(self, winner_name):
        """
        Bitiş ekranını gösterir ve kazananın adını yazar.
        Sunucudan gelen GAME_OVER mesajı ile tetiklenir.
        """
        self.gameover_winner_label.setText(f"Kazanan: {winner_name}")
        self.stacked_widget.setCurrentIndex(4)

    def on_replay_clicked(self):
        """
        Yeniden Oyna butonu: oyun durumunu sıfırla ve lobi ekranına dön.
        Renk (my_color) ve ID'nin tamamen sıfırlanmasına gerek yoktur, 
        çünkü yeni odaya girip GAME_START mesajı alındığında üzerine yazılacaktır.
        """
        self.current_phase = "REINFORCEMENT"
        self.is_my_turn = False
        self.current_board = {}
        self.selected_attacker = None
        self.selected_defender = None
        
        # Seçili bölge renklerini sıfırla
        for btn in self.node_buttons.values():
            btn.setStyleSheet("background-color: #DDDDDD;")
            
        # Odaya girildiğinde "Hazırım!" butonunu yeniden aktif et
        if hasattr(self, 'ready_btn'):
            self.ready_btn.setEnabled(True)
            self.ready_btn.setText("Hazırım!")
            
        # Lobiye dönerken önceki oda kodunu temizle ki kazayla tekrar oraya girilmesin
        if hasattr(self, 'room_code_input'):
            self.room_code_input.clear()
            
        self.stacked_widget.setCurrentIndex(1)


    # ================= 2. MANTIKSAL UI FONKSİYONLARI =================

    def update_action_button(self, phase):
        self.action_button.setEnabled(self.is_my_turn)
        if phase == "REINFORCEMENT":
            self.phase_label.setText("1. Evre: Takviye")
            self.action_button.setText("Takviye Yap")
            self.action_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        elif phase == "ATTACK":
            self.phase_label.setText("2. Evre: Saldırı")
            self.action_button.setText("Saldır!")
            self.action_button.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
        elif phase == "FORTIFY":
            self.phase_label.setText("3. Evre: Kaydırma")
            self.action_button.setText("Turu Bitir")
            self.action_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")

    def set_board_data(self, board_data):
        self.current_board = board_data
        self.refresh_board_ui()

    def refresh_board_ui(self):
        for node_id, data in self.current_board.items():
            btn = self.node_buttons.get(node_id)
            if not btn: continue
            
            owner = data["owner"]
            troops = data["troops"]
            btn.setText(f"Node {node_id}\nAsker: {troops}")
            
            if self.my_color == "Yeşil":
                bg_color = "lightgreen" if owner == self.my_id else "lightcoral"
            else:
                bg_color = "lightcoral" if owner == self.my_id else "lightgreen"
            text_color = "black"
            border = ""

            if self.current_phase in ["REINFORCEMENT", "ATTACK", "FORTIFY"]:
                if node_id == self.selected_attacker: # Seçilen Kaynak Bölge (veya saldıran)
                    bg_color = "yellow"
                    border = "border: 3px solid black;"
                elif node_id == self.selected_defender: # Seçilen Hedef Bölge (veya savunan)
                    bg_color = "purple"
                    text_color = "white"
                    border = "border: 3px solid black;"

            btn.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; font-weight: bold; {border}")

    # ================= 3. BUTON ETKİLEŞİMLERİ =================
    
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
        if not self.is_my_turn: return

        owner = self.current_board.get(node_id, {}).get("owner")
        is_my_territory = (owner == self.my_id)

        if self.current_phase == "REINFORCEMENT":
            if is_my_territory:
                self.selected_attacker = node_id
                self.refresh_board_ui()
                
        elif self.current_phase == "ATTACK":
            if is_my_territory:
                if self.current_board.get(node_id, {}).get("troops", 0) > 1:
                    self.selected_attacker = node_id
                    self.selected_defender = None
                    self.refresh_board_ui()
                else:
                    QMessageBox.warning(self, "Yetersiz Asker", "Saldırı yapabilmek için bölgede en az 2 askeriniz olmalı!")
                    
            elif not is_my_territory and self.selected_attacker is not None:
                if str(node_id) in self.neighbors.get(str(self.selected_attacker), []):
                    self.selected_defender = node_id
                    self.refresh_board_ui()
                else:
                    QMessageBox.warning(self, "Geçersiz Hedef", "Sadece saldıran bölgeye doğrudan komşu olan bir bölgeye saldırabilirsiniz!")

        # YENİ EKLENEN FORTIFY (KAYDIRMA) EVRESİ TIKLAMA KONTROLLERİ
        elif self.current_phase == "FORTIFY":
            if is_my_territory:
                # Henüz kaynak seçilmediyse veya kaynak değiştirilmek isteniyorsa
                if self.selected_attacker is None or (self.selected_attacker == node_id and self.selected_defender is None):
                    if self.current_board.get(node_id, {}).get("troops", 0) > 1:
                        self.selected_attacker = node_id
                        self.selected_defender = None
                        self.refresh_board_ui()
                    else:
                        if self.selected_attacker is None:
                            QMessageBox.warning(self, "Yetersiz Asker", "Asker kaydırabilmek için bölgede en az 2 askeriniz olmalı!")
                
                # Kaynak seçili ve farklı bir kendi bölgesi hedeflendiyse
                elif self.selected_attacker != node_id:
                    self.selected_defender = node_id
                    self.refresh_board_ui()
                    
                    # İki bölge de seçildi, oyuncuya kaç asker göndermek istediğini sor
                    source_troops = self.current_board.get(self.selected_attacker, {}).get("troops", 0)
                    max_troops = source_troops - 1 # En az 1 asker kaynakta kalmalı
                    
                    amount, ok = QInputDialog.getInt(
                        self, 
                        "Asker Kaydırma", 
                        f"Bölge {self.selected_attacker}'den Bölge {self.selected_defender}'e kaç asker göndermek istiyorsunuz?\n(Maksimum: {max_troops})", 
                        1,          # Varsayılan değer
                        1,          # Minimum değer
                        max_troops, # Maksimum değer
                        1           # Artış miktarı (step)
                    )
                    
                    if ok:
                        # Seçim onaylandıysa sunucuya mesaj yolla
                        self.worker.send_message({
                            "action": "FORTIFY_MOVE",
                            "source": self.selected_attacker,
                            "target": self.selected_defender,
                            "troops": amount
                        })
                    
                    # İşlem tamamlansın veya iptal edilsin, seçimleri temizle
                    self.selected_attacker = None
                    self.selected_defender = None
                    self.refresh_board_ui()
            else:
                QMessageBox.warning(self, "Geçersiz Hedef", "Sadece kendi bölgeleriniz arasında asker kaydırabilirsiniz!")

    def on_action_button_clicked(self):
        if not self.is_my_turn: return

        if self.current_phase == "REINFORCEMENT":
            if self.selected_attacker:
                self.worker.send_message({"action": "PLACE_TROOP", "node_id": self.selected_attacker})
            else:
                QMessageBox.warning(self, "Uyarı", "Lütfen takviye yapacağınız kendi bölgenizi seçin.")

        elif self.current_phase == "ATTACK":
            if self.selected_attacker and self.selected_defender:
                self.worker.send_message({
                    "action": "ATTACK_TERRITORY", 
                    "attacker": self.selected_attacker, 
                    "defender": self.selected_defender
                })
                self.selected_defender = None
                self.refresh_board_ui()
            else:
                QMessageBox.warning(self, "Uyarı", "Lütfen önce saldıracak bölgenizi, sonra hedef bölgeyi seçin.")

        elif self.current_phase == "FORTIFY":
            # Asker kaydırmak istemeyen kullanıcı doğrudan bu butona basarak sırayı rakibe salabilir.
            self.worker.send_message({"action": "NEXT_PHASE"})

    # ================= 4. SUNUCUDAN GELENLERİ İŞLEME =================
    
    def on_connected(self):
        self.status_label.setText("Sunucuya bağlandı! Lütfen isminizi girin.")
        self.status_label.setStyleSheet("color: green;")
        self.nickname_input.setEnabled(True)
        self.login_btn.setEnabled(True)

    def show_error(self, err_msg):
        QMessageBox.critical(self, "Hata", err_msg)

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
            self.stacked_widget.setCurrentIndex(3)
            current_turn_id = message.get("current_turn_id")
            self.is_my_turn = (current_turn_id == self.my_id)
            self.current_phase = message.get("phase", "REINFORCEMENT")
            self.battle_log.clear() # Oyun başladığında logu temizle
            
            if self.is_my_turn:
                self.my_color = "Yeşil"
                self.color_label.setText("Renginiz: YEŞİL 🟢")
                self.color_label.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
                self.turn_label.setText("Sıra: SENDE")
                self.turn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
            else:
                self.my_color = "Kırmızı"
                self.color_label.setText("Renginiz: KIRMIZI 🔴")
                self.color_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")
                self.turn_label.setText("Sıra: RAKİPTE")
                self.turn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")

            self.troops_label.setText(f"Bonus Asker: {message.get('remaining_troops', 0)}")
            self.selected_attacker = None
            self.selected_defender = None
            self.update_action_button(self.current_phase)
            self.set_board_data(message.get("board"))
            
        elif action == "TIME_TICK":
            self.time_label.setText(f"Süre: {message.get('time')}")
            
        elif action == "BOARD_UPDATE":
            self.troops_label.setText(f"Bonus Asker: {message.get('remaining_troops', 0)}")
            if self.current_phase == "REINFORCEMENT":
                self.selected_attacker = None 
            self.set_board_data(message.get("board"))
            
        elif action == "PHASE_CHANGED":
            self.current_phase = message.get("phase")
            self.is_my_turn = (message.get("current_turn_id") == self.my_id)
            self.troops_label.setText(f"Bonus Asker: {message.get('remaining_troops', 0)}")
            
            if self.is_my_turn:
                self.turn_label.setText("Sıra: SENDE")
                self.turn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
            else:
                self.turn_label.setText("Sıra: RAKİPTE")
                self.turn_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
            
            self.selected_attacker = None
            self.selected_defender = None
            self.update_action_button(self.current_phase)
            self.refresh_board_ui()

        # YENİ EKLENEN SAVAŞ RAPORU YAKALAYICISI
        elif action == "BATTLE_REPORT":
            a_node = message.get("attacker_node")
            d_node = message.get("defender_node")
            a_rolls = message.get("a_rolls", [])
            d_rolls = message.get("d_rolls", [])
            a_lost = message.get("a_lost", 0)
            d_lost = message.get("d_lost", 0)
            conquered = message.get("conquered", False)
            
            # Log metnini oluştur (HTML destekler, renklendirme yapabiliriz)
            log_text = f"<b style='color:blue;'>Bölge {a_node}</b> ➔ <b style='color:red;'>Bölge {d_node}</b><br>"
            log_text += f"🗡️ Saldıran Zarları: <b>{a_rolls}</b><br>"
            log_text += f"🛡️ Savunan Zarları: <b>{d_rolls}</b><br>"
            log_text += f"📉 Kayıp ➔ Saldıran: <b style='color:red;'>-{a_lost}</b> | Savunan: <b style='color:red;'>-{d_lost}</b><br>"
            
            if conquered:
                log_text += f"🎉 <b style='color:green;'>BÖLGE ELE GEÇİRİLDİ!</b><br>"
                
            log_text += "<hr>"
            
            self.battle_log.append(log_text)
            
            # Log eklendikçe otomatik olarak en alta kaydır
            scrollbar = self.battle_log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        elif action == "GAME_OVER":
            winner = message.get("winner", "Bilinmeyen")
            self.show_gameover(winner)

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RiskClientApp()
    window.show()
    sys.exit(app.exec_())