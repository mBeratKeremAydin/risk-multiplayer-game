# Dosya Adı: server.py

import socket
import threading
import json
import random
import string
import time
from collections import deque  # BFS algoritmasında kuyruk (queue) yapısı için eklendi
from models import Player, Room
from game_engine import setup_game, start_turn

# ==============================================================================
# AWS DEĞİŞİKLİĞİ İÇİN NOT:
# Şimdilik kendi bilgisayarında (lokalde) test edeceğin için HOST'u 127.0.0.1 yaptık.
# Projeyi teslim etmeden önce AWS sanal makinesine taşıdığında, 
# dışarıdan gelen bağlantıları kabul edebilmesi için bunu '0.0.0.0' yapmalısın.
# ==============================================================================
HOST = '127.0.0.1'  
PORT = 5555

# --- EVRENSEL KOMŞULUK TABLOSU (Harita Bağlantıları) ---
NEIGHBORS = {
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
# --------------------------------------------------------

# Global Hafıza (Sunucu açık kaldığı sürece verileri burada tutacağız)
active_players = {}  # Key: Player ID, Value: Player object
active_rooms = {}    # Key: Room Code, Value: Room object

def generate_room_code():
    """4 haneli rastgele ve benzersiz bir oda kodu üretir."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if code not in active_rooms:
            return code

def send_msg(connection, data_dict):
    """Sözlük (dict) tipindeki veriyi JSON formatına çevirip sonuna \n ekleyerek gönderir."""
    try:
        json_data = json.dumps(data_dict) + "\n"
        connection.sendall(json_data.encode('utf-8'))
    except Exception as e:
        print(f"[HATA] Mesaj gönderilemedi: {e}")

def broadcast_room(room, data_dict):
    """Bir odadaki TÜM oyunculara aynı mesajı gönderir."""
    for player in room.players:
        send_msg(player.connection, data_dict)

def has_valid_path(room, player_id, source_id, target_id):
    """
    BFS (Genişlik Öncelikli Arama) kullanarak, kaynak bölgeden hedef bölgeye
    SADECE oyuncunun kendi bölgeleri üzerinden geçerek gidilip gidilemeyeceğini kontrol eder.
    """
    if source_id == target_id:
        return True

    visited = set()
    queue = deque([source_id])
    visited.add(source_id)

    while queue:
        current_node = queue.popleft()
        
        # Hedefe ulaştıysak yol var demektir!
        if current_node == target_id:
            return True
            
        # Mevcut bölgenin komşularını kontrol et
        for neighbor in NEIGHBORS.get(current_node, []):
            if neighbor not in visited:
                territory = room.board.territories.get(neighbor)
                # Eğer komşu bölge bu oyuncuya aitse, yola oradan devam edebiliriz
                if territory and territory.owner_id == player_id:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    
    # Kuyruk bittiyse ve hedef bulunamadıysa yol yok demektir.
    return False

def room_timer_thread(room):
    """Arka planda odanın süresini sayar ve süre bittiğinde evreyi otomatik atlatır."""
    while room.is_playing:
        if room.remaining_time > 0:
            time.sleep(1)
            room.remaining_time -= 1
            # Odadaki herkese süreyi bildir
            broadcast_room(room, {"action": "TIME_TICK", "time": room.remaining_time})
        else:
            # SÜRE BİTTİ! Otomatik Evre Geçişi
            current_player_id = room.current_turn_player_id
            
            if room.phase == "REINFORCEMENT":
                # Eğer dağıtılmamış asker kaldıysa, oyuncunun bölgelerine rastgele dağıt
                if getattr(room, 'remaining_bonus_troops', 0) > 0:
                    player_territories = [t for t in room.board.territories.values() if t.owner_id == current_player_id]
                    if player_territories:
                        for _ in range(room.remaining_bonus_troops):
                            random_territory = random.choice(player_territories)
                            random_territory.troop_count += 1
                    
                    room.remaining_bonus_troops = 0
                    
                    # Güncel haritayı herkese yolla
                    board_data = {t: {"owner": obj.owner_id, "troops": obj.troop_count} for t, obj in room.board.territories.items()}
                    broadcast_room(room, {
                        "action": "BOARD_UPDATE",
                        "board": board_data,
                        "remaining_troops": 0
                    })
                
                # Saldırı evresine geç
                room.phase = "ATTACK"
                room.remaining_time = 45

            elif room.phase == "ATTACK":
                # Kaydırma evresine geç
                room.phase = "FORTIFY"
                room.remaining_time = 30

            elif room.phase == "FORTIFY":
                # Turu bitir, sırayı karşıya ver
                room.switch_turn()
                start_turn(room) # Diğer oyuncunun REINFORCEMENT evresini başlatır ve süreyi 30 yapar
            
            # Yeni evreyi herkese bildir
            broadcast_room(room, {
                "action": "PHASE_CHANGED",
                "phase": room.phase,
                "current_turn_id": room.current_turn_player_id,
                "remaining_troops": getattr(room, 'remaining_bonus_troops', 0)
            })

def handle_client(conn, addr):
    """Her bağlanan istemci için arka planda sürekli çalışan dinleyici fonksiyon."""
    print(f"[YENİ BAĞLANTI] {addr} bağlandı.")
    current_player_id = None
    buffer = ""

    while True:
        try:
            # İstemciden veri bekle
            data = conn.recv(4096)
            if not data:
                break 
            
            buffer += data.decode('utf-8')
            
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                
                request = json.loads(line)
                action = request.get("action")

                # ---------------- 1. LOGIN İŞLEMİ ----------------
                if action == "LOGIN":
                    nickname = request.get("nickname")
                    new_player = Player(nickname, addr, conn)
                    active_players[new_player.id] = new_player
                    current_player_id = new_player.id
                    
                    print(f"[LOGIN] {nickname} giriş yaptı. ID: {new_player.id}")
                    
                    send_msg(conn, {
                        "action": "LOGIN_SUCCESS", 
                        "player_id": new_player.id,
                        "nickname": nickname
                    })

                # ---------------- 2. ODA KURMA (CREATE ROOM) ----------------
                elif action == "CREATE_ROOM":
                    player = active_players.get(current_player_id)
                    room_code = generate_room_code()
                    
                    new_room = Room(room_code)
                    active_rooms[room_code] = new_room
                    new_room.add_player(player)
                    
                    print(f"[ODA KURULDU] Kod: {room_code}, Kuran: {player.nickname}")
                    
                    broadcast_room(new_room, {
                        "action": "ROOM_UPDATED",
                        "room_code": room_code,
                        "players": [p.to_dict() for p in new_room.players]
                    })

                # ---------------- 3. ODAYA KATILMA (JOIN ROOM) ----------------
                elif action == "JOIN_ROOM":
                    player = active_players.get(current_player_id)
                    room_code = request.get("room_code")
                    
                    if room_code in active_rooms:
                        room = active_rooms[room_code]
                        if len(room.players) < 2:
                            room.add_player(player)
                            print(f"[ODAYA KATILDI] {player.nickname}, {room_code} odasına girdi.")
                            
                            broadcast_room(room, {
                                "action": "ROOM_UPDATED",
                                "room_code": room_code,
                                "players": [p.to_dict() for p in room.players]
                            })
                        else:
                            send_msg(conn, {"action": "ERROR", "message": "Oda dolu!"})
                    else:
                        send_msg(conn, {"action": "ERROR", "message": "Geçersiz oda kodu!"})

                # ---------------- 4. HAZIR (READY) VE OYUN BAŞLATMA ----------------
                elif action == "READY":
                    player = active_players.get(current_player_id)
                    room = active_rooms.get(player.room_code)
                    
                    if room:
                        player.is_ready = True
                        broadcast_room(room, {
                            "action": "ROOM_UPDATED",
                            "room_code": room.room_code,
                            "players": [p.to_dict() for p in room.players]
                        })
                        
                        # İki oyuncu da hazırsa oyunu başlat
                        if len(room.players) == 2 and all(p.is_ready for p in room.players):
                            print(f"[OYUN BAŞLIYOR] {room.room_code} odası oyuna geçiyor...")
                            
                            setup_game(room)
                            
                            board_data = {}
                            for t_name, t_obj in room.board.territories.items():
                                board_data[t_name] = {"owner": t_obj.owner_id, "troops": t_obj.troop_count}
                                
                            broadcast_room(room, {
                                "action": "GAME_START",
                                "current_turn_id": room.current_turn_player_id,
                                "board": board_data,
                                "phase": room.phase,
                                "remaining_troops": getattr(room, 'remaining_bonus_troops', 0)
                            })
                            
                            # Oyun başladıktan sonra sayaç thread'ini başlat
                            threading.Thread(target=room_timer_thread, args=(room,), daemon=True).start()
                
                # ---------------- 5. TAKVİYE YAPMA (PLACE_TROOP) ----------------
                elif action == "PLACE_TROOP":
                    player = active_players.get(current_player_id)
                    room = active_rooms.get(player.room_code)
                    node_id = request.get("node_id")
                    
                    if room and room.is_playing and room.is_it_players_turn(player.id) and room.phase == "REINFORCEMENT":
                        territory = room.board.territories.get(node_id)
                        
                        if territory and territory.owner_id == player.id and room.remaining_bonus_troops > 0:
                            territory.troop_count += 1
                            room.remaining_bonus_troops -= 1
                            
                            board_data = {t: {"owner": obj.owner_id, "troops": obj.troop_count} for t, obj in room.board.territories.items()}
                            broadcast_room(room, {
                                "action": "BOARD_UPDATE",
                                "board": board_data,
                                "remaining_troops": room.remaining_bonus_troops
                            })

                # ---------------- 6. SONRAKİ EVREYE GEÇİŞ (NEXT_PHASE) ----------------
                elif action == "NEXT_PHASE":
                    player = active_players.get(current_player_id)
                    room = active_rooms.get(player.room_code)
                    
                    if room and room.is_playing and room.is_it_players_turn(player.id):
                        # Evreyi ilerlet ve süreleri ayarla
                        if room.phase == "REINFORCEMENT":
                            room.phase = "ATTACK"
                            room.remaining_time = 45
                        elif room.phase == "ATTACK":
                            room.phase = "FORTIFY"
                            room.remaining_time = 30
                        elif room.phase == "FORTIFY":
                            room.switch_turn()
                            start_turn(room)
                        
                        broadcast_room(room, {
                            "action": "PHASE_CHANGED",
                            "phase": room.phase,
                            "current_turn_id": room.current_turn_player_id,
                            "remaining_troops": getattr(room, 'remaining_bonus_troops', 0)
                        })
                
                # ---------------- 7. SALDIRI EVRESİ (ATTACK_TERRITORY) ----------------
                elif action == "ATTACK_TERRITORY":
                    player = active_players.get(current_player_id)
                    if not player: continue
                    room = active_rooms.get(player.room_code)
                    if not room: continue
                    
                    if not room.is_playing or room.current_turn_player_id != current_player_id or room.phase != "ATTACK":
                        continue

                    attacker_id = str(request.get("attacker"))
                    defender_id = str(request.get("defender"))

                    attacker_node = room.board.territories.get(attacker_id)
                    defender_node = room.board.territories.get(defender_id)

                    if not attacker_node or not defender_node: continue
                    if attacker_node.owner_id != current_player_id: continue 
                    if defender_node.owner_id == current_player_id: continue 
                    if attacker_node.troop_count <= 1: continue 
                    if defender_id not in NEIGHBORS.get(attacker_id, []): continue 

                    att_dice_count = min(3, attacker_node.troop_count - 1)
                    def_dice_count = min(2, defender_node.troop_count)

                    att_rolls = sorted([random.randint(1, 6) for _ in range(att_dice_count)], reverse=True)
                    def_rolls = sorted([random.randint(1, 6) for _ in range(def_dice_count)], reverse=True)

                    att_losses = 0
                    def_losses = 0

                    for i in range(min(len(att_rolls), len(def_rolls))):
                        if att_rolls[i] > def_rolls[i]:
                            def_losses += 1 
                        else:
                            att_losses += 1 

                    attacker_node.troop_count -= att_losses
                    defender_node.troop_count -= def_losses

                    is_conquered = False
                    if defender_node.troop_count == 0:
                        is_conquered = True
                        defender_node.owner_id = current_player_id
                        
                        troops_to_move = att_dice_count - att_losses 
                        if troops_to_move < 1: 
                            troops_to_move = 1 
                            
                        defender_node.troop_count = troops_to_move
                        attacker_node.troop_count -= troops_to_move

                        # OYUN BİTİŞ KONTROLÜ
                        owns_all = all(t.owner_id == current_player_id for t in room.board.territories.values())
                        if owns_all:
                            room.is_playing = False
                            broadcast_room(room, {
                                "action": "GAME_OVER",
                                "winner": player.nickname
                            })
                            # Odayı temizle
                            if room.room_code in active_rooms:
                                del active_rooms[room.room_code]
                            continue

                    broadcast_room(room, {
                        "action": "BATTLE_REPORT",
                        "attacker_node": attacker_id,
                        "defender_node": defender_id,
                        "a_rolls": att_rolls,
                        "d_rolls": def_rolls,
                        "a_lost": att_losses,
                        "d_lost": def_losses,
                        "conquered": is_conquered
                    })

                    board_data = {t: {"owner": obj.owner_id, "troops": obj.troop_count} for t, obj in room.board.territories.items()}
                    broadcast_room(room, {
                        "action": "BOARD_UPDATE",
                        "board": board_data,
                        "remaining_troops": getattr(room, 'remaining_bonus_troops', 0)
                    })

                # ---------------- 8. ASKER KAYDIRMA (FORTIFY_MOVE) ----------------
                elif action == "FORTIFY_MOVE":
                    player = active_players.get(current_player_id)
                    if not player: continue
                    room = active_rooms.get(player.room_code)
                    if not room: continue
                    
                    # Tur ve Evre Kontrolleri
                    if not room.is_playing or room.current_turn_player_id != current_player_id or room.phase != "FORTIFY":
                        continue

                    source_id = str(request.get("source"))
                    target_id = str(request.get("target"))
                    troop_count = int(request.get("troops", 0))

                    source_node = room.board.territories.get(source_id)
                    target_node = room.board.territories.get(target_id)

                    # Güvenlik Kontrolleri
                    if not source_node or not target_node: continue
                    if source_node.owner_id != current_player_id or target_node.owner_id != current_player_id: continue
                    if troop_count <= 0 or source_node.troop_count <= troop_count: continue # Kaynakta en az 1 asker kalmak zorunda!

                    # BFS (Yol Bulma) ile aradaki bağlantının kontrolü
                    if has_valid_path(room, current_player_id, source_id, target_id):
                        # Yol geçerli, askerleri taşı
                        source_node.troop_count -= troop_count
                        target_node.troop_count += troop_count

                        # Haritayı güncelle
                        board_data = {t: {"owner": obj.owner_id, "troops": obj.troop_count} for t, obj in room.board.territories.items()}
                        broadcast_room(room, {
                            "action": "BOARD_UPDATE",
                            "board": board_data,
                            "remaining_troops": getattr(room, 'remaining_bonus_troops', 0)
                        })

                        # Kural gereği asker kaydırması bittiğinde otomatik olarak tur biter ve sıradaki oyuncuya geçilir
                        room.switch_turn()
                        start_turn(room) 

                        # Yeni evreyi (yeni oyuncunun Reinforcement evresini) bildir
                        broadcast_room(room, {
                            "action": "PHASE_CHANGED",
                            "phase": room.phase,
                            "current_turn_id": room.current_turn_player_id,
                            "remaining_troops": getattr(room, 'remaining_bonus_troops', 0)
                        })
                    else:
                        # Bağlantı kopuksa veya araya düşman girmişse reddet
                        send_msg(conn, {"action": "ERROR", "message": "Bu iki bölge arasında geçerli bir bağlantı yolu yok!"})

        except json.JSONDecodeError:
            print(f"[HATA] {addr} adresinden geçersiz JSON formatı geldi.")
        except ConnectionResetError:
            break
        except Exception as e:
            print(f"[HATA] Beklenmeyen bir durum oluştu: {e}")
            break
            
    # Temizlik kısmı (İstemci bağlantıyı kopardığında)
    print(f"[BAĞLANTI KOPTU] {addr}")

    # Oyun devam ediyorsa rakibi galip ilan et
    disconnected_player = active_players.get(current_player_id)
    if disconnected_player and disconnected_player.room_code:
        room = active_rooms.get(disconnected_player.room_code)
        if room and room.is_playing:
            room.is_playing = False  # Timer thread'ini durdur
            # Kalan oyuncuyu bul ve galip ilan et
            for p in room.players:
                if p.id != current_player_id:
                    print(f"[OYUN BİTTİ] {disconnected_player.nickname} bağlantısı koptu. Kazanan: {p.nickname}")
                    send_msg(p.connection, {
                        "action": "GAME_OVER",
                        "winner": p.nickname
                    })
                    break
            # Odayı temizle
            if disconnected_player.room_code in active_rooms:
                del active_rooms[disconnected_player.room_code]

    if current_player_id in active_players:
        del active_players[current_player_id]
    conn.close()

def start_server():
    """Sunucuyu başlatır ve ana kapıda yeni bağlantıları bekler."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SUNUCU] {HOST}:{PORT} adresinde dinleniyor... (Risk MultiPlayer Server)")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[SUNUCU] Aktif Bağlantı Sayısı: {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()