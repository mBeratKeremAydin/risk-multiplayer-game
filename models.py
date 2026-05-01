# Dosya Adı: models.py
# İşlevi: Oyunun temel veri yapılarını (Sınıfları) barındırır.

import uuid

# ==========================================
# 1. OYUNCU SINIFI
# ==========================================
class Player:
    def __init__(self, nickname, address, connection=None):
        self.id = str(uuid.uuid4())[:8]  # Benzersiz 8 haneli ID
        self.nickname = nickname
        self.address = address           # (IP, Port) tuple'ı
        self.connection = connection     # Sunucu-istemci soket bağlantısı
        self.room_code = None
        self.is_ready = False

    def to_dict(self):
        # Client'a gönderilecek veriler (Socket nesnesi JSON'a çevrilemez)
        return {"id": self.id, "nickname": self.nickname, "is_ready": self.is_ready}


# ==========================================
# 2. KITA SINIFI
# ==========================================
class Continent:
    def __init__(self, name, bonus_troops, territories):
        self.name = name
        self.bonus_troops = bonus_troops  # Kıtanın tamamına sahip olunca verilecek ekstra asker
        self.territories = territories    # Bu kıtaya ait bölgelerin isim listesi ['Türkiye', 'Irak', ...]
        self.owner_id = None              # Kıtaya tamamen sahip olan oyuncunun ID'si


# ==========================================
# 3. BÖLGE (NODE) SINIFI
# ==========================================
class Territory:
    def __init__(self, name, continent_name):
        self.name = name
        self.continent = continent_name   # Hangi kıtada olduğu
        self.owner_id = None              # Sahibi olan oyuncunun ID'si
        self.troop_count = 0              # İçindeki asker sayısı
        self.neighbors = []               # Komşu bölgelerin isim listesi (Graph Edges)

    def add_neighbor(self, neighbor_name):
        if neighbor_name not in self.neighbors:
            self.neighbors.append(neighbor_name)


# ==========================================
# 4. HARİTA / OYUN DURUMU (GRAPH) SINIFI
# ==========================================
class Board:
    def __init__(self):
        self.territories = {}  # Tüm Graph düğümleri (Key: Bölge Adı, Value: Territory nesnesi)
        self.continents = {}   # Key: Kıta Adı, Value: Continent nesnesi

    def add_territory(self, name, continent_name):
        self.territories[name] = Territory(name, continent_name)

    def add_connection(self, t1_name, t2_name):
        # İki yönlü bağlantı (Undirected Graph Edge)
        if t1_name in self.territories and t2_name in self.territories:
            self.territories[t1_name].add_neighbor(t2_name)
            self.territories[t2_name].add_neighbor(t1_name)

    def is_path_exists(self, start_name, target_name, player_id):
        """
        Asker kaydırma için BFS Algoritması.
        Sadece oyuncuya ait komşular üzerinden ilerleyerek hedef bölgeye yol var mı kontrol eder.
        """
        if self.territories[start_name].owner_id != player_id or self.territories[target_name].owner_id != player_id:
            return []

        queue = [[start_name]]  
        visited = set([start_name])

        while queue:
            path = queue.pop(0)
            current_node = path[-1]

            if current_node == target_name:
                return path  

            for neighbor in self.territories[current_node].neighbors:
                if neighbor not in visited and self.territories[neighbor].owner_id == player_id:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return []

    def update_continent_ownership(self):
        """
        Haritadaki tüm kıtaları gezer. Eğer bir kıtanın tüm bölgeleri 
        tek bir oyuncuya aitse, o kıtanın sahibini (owner_id) günceller.
        """
        for continent in self.continents.values():
            if not continent.territories:
                continue

            first_territory_name = continent.territories[0]
            first_owner = self.territories[first_territory_name].owner_id

            if first_owner is None:
                continent.owner_id = None
                continue
            
            owns_all = all(self.territories[t_name].owner_id == first_owner for t_name in continent.territories)
            
            if owns_all:
                continent.owner_id = first_owner
            else:
                continent.owner_id = None

    def get_player_bonus(self, player_id):
        """
        Tur başında çağrılır. Oyuncunun tamamen sahip olduğu kıtalardan 
        gelen toplam bonus asker sayısını döndürür.
        """
        self.update_continent_ownership() 
        
        total_bonus = 0
        for continent in self.continents.values():
            if continent.owner_id == player_id:
                total_bonus += continent.bonus_troops
        return total_bonus


# ==========================================
# 5. ODA SINIFI
# ==========================================
class Room:
    def __init__(self, room_code):
        self.room_code = room_code
        self.players = []          # Odaya katılan Player nesneleri (Maks 2)
        self.is_playing = False
        self.board = Board()       # Odaya özel harita (Graph)
        
        # OYUN AKIŞI İÇİN DEĞİŞKENLER
        self.current_turn_player_id = None  # Sıradaki oyuncunun ID'si
        self.phase = "REINFORCEMENT"        # REINFORCEMENT, ATTACK, FORTIFY
        self.turn_count = 1
        
        # AŞAĞIDAKİ İKİ DEĞİŞKEN EKLENDİ!
        self.remaining_time = 0             # Tur süresi sayacı
        self.remaining_bonus_troops = 0     # Takviye evresinde dağıtılacak asker sayısı

    def add_player(self, player):
        if len(self.players) < 2:
            self.players.append(player)
            player.room_code = self.room_code
            return True
        return False

    def next_phase(self):
        """
        Oyunun evrelerini döndürür: Takviye -> Saldırı -> Kaydırma -> (Sonraki Oyuncu) Takviye...
        """
        if self.phase == "REINFORCEMENT":
            self.phase = "ATTACK"
        elif self.phase == "ATTACK":
            self.phase = "FORTIFY"
        elif self.phase == "FORTIFY":
            self.phase = "REINFORCEMENT"
            self.switch_turn()

    def switch_turn(self):
        """Sırayı diğer oyuncuya geçirir."""
        current_id = self.current_turn_player_id
        # Odadaki oyuncular arasından diğerini bul
        for p in self.players:
            if p.id != current_id:
                self.current_turn_player_id = p.id
                break
        self.turn_count += 1

    def is_it_players_turn(self, player_id):
        """Gelen isteğin sırası olan oyuncudan gelip gelmediğini kontrol eder."""
        return self.current_turn_player_id == player_id