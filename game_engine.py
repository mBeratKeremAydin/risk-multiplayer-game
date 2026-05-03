# Dosya Adı: game_engine.py
# İşlevi: Oyunun kurulumu, zar atışları, asker dağıtımı gibi oyun mantığını (kurallarını) barındırır.

import random
from models import Continent, Territory

def start_turn(room):
    """
    Sırası gelen oyuncunun turunu başlatır, 
    bonus askerlerini hesaplar ve süreleri ayarlar.
    """
    board = room.board
    current_player_id = room.current_turn_player_id
    
    # 1. Aşama: REINFORCEMENT (Takviye)
    room.phase = "REINFORCEMENT"
    room.remaining_time = 30 # 30 saniye süre tanınır
    
    # Bonus Asker Hesaplama (Minimum 3 asker verilir)
    # Oyuncunun sahip olduğu toplam bölge sayısı / 3
    player_node_count = sum(1 for t in board.territories.values() if t.owner_id == current_player_id)
    base_bonus = max(3, player_node_count // 3)
    
    # Kıta bonuslarını ekle (Eğer bir kıtanın tamamına sahipse)
    continent_bonus = board.get_player_bonus(current_player_id)
    
    room.remaining_bonus_troops = base_bonus + continent_bonus
    print(f"[TUR BAŞLADI] Oyuncu: {current_player_id} | Verilen Asker: {room.remaining_bonus_troops}")


def setup_game(room):
    """
    Oda 2 kişiyle dolup herkes hazır olduğunda çağrılır.
    Haritayı oluşturur, kıtaları bağlar ve askerleri dağıtır.
    """
    board = room.board
    
    # 1. KITALAR VE SAHİP OLDUKLARI NODE'LAR (BÖLGELER)
    continents_data = {
        "Kuzey Amerika": {"bonus": 4, "nodes": ["0","1","2","3","4","5","6","7","8"]},
        "Güney Amerika": {"bonus": 3, "nodes": ["9","10","11","12"]},
        "Afrika": {"bonus": 4, "nodes": ["13","14","15","16","17","18"]},
        "Avrupa": {"bonus": 5, "nodes": ["19","20","21","22","23","24","25"]},
        "Asya": {"bonus": 6, "nodes": ["26","27","28","29","30","31","36","37","38","39","40","41"]},
        "Avustralya": {"bonus": 2, "nodes": ["32","33","34","35"]}
    }

    # Kıtaları ve Bölgeleri (Territories) Board'a ekle
    for continent_name, data in continents_data.items():
        # Kıta nesnesini oluştur ve Board'a kaydet
        board.continents[continent_name] = Continent(continent_name, data["bonus"], data["nodes"])
        
        # Bu kıtadaki node'ları (bölgeleri) oluştur
        for node_id in data["nodes"]:
            board.add_territory(node_id, continent_name)


    # KOMŞULUK BAĞLANTILARI (GRAPH EDGES) artık burada oluşturulmuyor!
    # Bunun yerine Server.py'deki evrensel NEIGHBORS tablosu kullanılıyor.

    # 3. NODE VE ASKER DAĞITIMI
    all_nodes = list(board.territories.keys())
    random.shuffle(all_nodes) # Düğüm listesini rastgele karıştır

    # Toplam 42 Node var. 2 Oyuncu olduğuna göre 21-21 paylaşacaklar.
    player1_nodes = all_nodes[:21]
    player2_nodes = all_nodes[21:]
    
    player1_id = room.players[0].id
    player2_id = room.players[1].id

    # Başlangıç asker ayarları
    TOTAL_STARTING_TROOPS = 50  # Her oyuncunun toplam başlangıç askeri
    MAX_TROOP_PER_NODE = 7      # Başlangıçta bir node'da en fazla olabilecek asker

    def distribute_troops_for_player(player_id, assigned_nodes):
        # Önce her bölgeye 1'er asker koymak zorundayız (Boş bölge olamaz)
        for node_id in assigned_nodes:
            board.territories[node_id].owner_id = player_id
            board.territories[node_id].troop_count = 1
        
        # Geriye kalan askerleri (50 - 21 = 29 asker) rastgele dağıt
        remaining_troops = TOTAL_STARTING_TROOPS - len(assigned_nodes)
        
        while remaining_troops > 0:
            random_node = random.choice(assigned_nodes)
            # Eğer o bölgedeki asker sayısı limiti (örn: 7) aşmadıysa 1 asker ekle
            if board.territories[random_node].troop_count < MAX_TROOP_PER_NODE:
                board.territories[random_node].troop_count += 1
                remaining_troops -= 1

    # İki oyuncu için de asker dağıtımını yap
    distribute_troops_for_player(player1_id, player1_nodes)
    distribute_troops_for_player(player2_id, player2_nodes)

    # 4. BAŞLANGIÇ AYARLARINI TAMAMLA
    # Kimin başlayacağını rastgele seçelim
    room.current_turn_player_id = random.choice([player1_id, player2_id])
    room.is_playing = True
    
    # Dağıtım sonrası tamamen ele geçirilmiş şanslı kıta var mı diye kontrol et 
    board.update_continent_ownership()
    
    # İŞTE BURASI: Oyunun ilk turunu ve süreleri başlatıyoruz!
    start_turn(room)