# Dosya Adı: game_engine.py
# İşlevi: Oyunun kurulumu, zar atışları, asker dağıtımı gibi oyun mantığını (kurallarını) barındırır.

import random
from models import Continent, Territory

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


    # 2. KOMŞULUK BAĞLANTILARI (GRAPH EDGES)
    connections_data = {
        # Kuzey Amerika
        "0": ["1", "2", "41"], "1": ["0", "2", "3", "4"], "2": ["0", "1", "4", "6"],
        "3": ["1", "4", "5", "23"], "4": ["1", "2", "3", "5", "6", "7"], "5": ["3", "4", "7"],
        "6": ["2", "4", "7", "8"], "7": ["4", "5", "6", "8"], "8": ["6", "7", "9"],
        # Güney Amerika
        "9": ["8", "10", "11"], "10": ["9", "11", "12", "13"], "11": ["9", "10", "12"], "12": ["10", "11"],
        # Afrika
        "13": ["10", "14", "17", "18", "19", "20"], "14": ["13", "15", "17", "18"], "15": ["14", "16", "17"],
        "16": ["15", "17"], "17": ["13", "14", "15", "16", "18", "26"], "18": ["13", "14", "17", "19", "26"],
        # Avrupa
        "19": ["13", "18", "20", "22", "25", "26"], "20": ["13", "19", "21", "22"], "21": ["20", "22", "23", "24"],
        "22": ["19", "20", "21", "24", "25"], "23": ["3", "21", "24"], "24": ["21", "22", "23", "25"],
        "25": ["19", "22", "24", "26", "28", "29"],
        # Asya
        "26": ["17", "18", "19", "25", "27", "28"], "27": ["26", "28", "30", "31"], 
        "28": ["25", "26", "27", "29", "30", "38"], "29": ["25", "28", "30", "38"], 
        "30": ["27", "28", "29", "31", "36", "38"], "31": ["27", "30", "32"], 
        "36": ["30", "37", "38", "39", "41"], "37": ["36", "41"], 
        "38": ["29", "30", "36", "39", "40"], "39": ["36", "38", "40", "41"], 
        "40": ["38", "39", "41"], "41": ["36", "37", "39", "40", "0"],
        # Avustralya
        "32": ["31", "33", "34"], "33": ["32", "34", "35"], "34": ["32", "33", "35"], "35": ["33", "34"]
    }

    # Bağlantıları Board üzerindeki metoda göndererek iki yönlü bağla
    for node, neighbors in connections_data.items():
        for neighbor in neighbors:
            board.add_connection(node, neighbor)


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