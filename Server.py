import socket
import threading
import json
import random
import string
from models import Player, Room
from game_engine import setup_game

# ==============================================================================
# AWS DEĞİŞİKLİĞİ İÇİN NOT:
# Şimdilik kendi bilgisayarında (lokalde) test edeceğin için HOST'u 127.0.0.1 yaptık.
# Projeyi teslim etmeden önce AWS sanal makinesine taşıdığında, 
# dışarıdan gelen bağlantıları kabul edebilmesi için bunu '0.0.0.0' yapmalısın.
# ==============================================================================
HOST = '127.0.0.1'  
PORT = 5555

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
    """Sözlük (dict) tipindeki veriyi JSON formatına çevirip istemciye gönderir."""
    try:
        json_data = json.dumps(data_dict)
        connection.sendall(json_data.encode('utf-8'))
    except Exception as e:
        print(f"[HATA] Mesaj gönderilemedi: {e}")

def broadcast_room(room, data_dict):
    """Bir odadaki TÜM oyunculara aynı mesajı gönderir."""
    for player in room.players:
        send_msg(player.connection, data_dict)

def handle_client(conn, addr):
    """Her bağlanan istemci için arka planda sürekli çalışan dinleyici fonksiyon."""
    print(f"[YENİ BAĞLANTI] {addr} bağlandı.")
    current_player_id = None

    while True:
        try:
            # İstemciden veri bekle (Bloklayıcı fonksiyondur, mesaj gelene kadar bekler)
            data = conn.recv(4096) # JSON boyutu büyük olabileceği için 4096 byte'a çıkardık
            if not data:
                break # Eğer data boş gelirse, istemci bağlantıyı kopardı demektir.
            
            # Gelen byte verisini JSON'a (Sözlük yapısına) çevir
            request = json.loads(data.decode('utf-8'))
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
                            "board": board_data
                        })

        except json.JSONDecodeError:
            print(f"[HATA] {addr} adresinden geçersiz JSON formatı geldi.")
        except ConnectionResetError:
            break
        except Exception as e:
            print(f"[HATA] Beklenmeyen bir durum oluştu: {e}")
            break
            
    # Temizlik kısmı (İstemci bağlantıyı kopardığında)
    print(f"[BAĞLANTI KOPTU] {addr}")
    if current_player_id in active_players:
        # İleride buraya odadan çıkarma mantığı eklenebilir
        del active_players[current_player_id]
    conn.close()

def start_server():
    """Sunucuyu başlatır ve ana kapıda yeni bağlantıları bekler."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Portun işletim sistemi tarafından hemen serbest bırakılması için bir ayar:
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