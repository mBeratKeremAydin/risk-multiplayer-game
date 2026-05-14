# Dosya Adı: models.py
# İşlevi: Oyunun temel veri yapılarını (sınıflarını) barındırır.
#         Bu dosyadaki nesneler hem sunucu hem de game_engine tarafından kullanılır.

import uuid

# Projede kullanılan veri yapılarını (Player, Room, Territory) tutan sınıf (Class) dosyasıdır.
# Bu OOP yapısı sayesinde verilerin sunucu ile istemci arasında düzenli kalması sağlanır.

# ==========================================
# 1. OYUNCU SINIFI
# Her bağlanan istemci için bir Player nesnesi oluşturulur.
# ==========================================
class Player:
    def __init__(self, nickname, address, connection=None):
        # uuid4 ile benzersiz 8 karakterlik kısa bir ID üretilir
        self.id = str(uuid.uuid4())[:8]
        self.nickname = nickname
        self.address = address        # (IP, Port) tuple'ı
        self.connection = connection  # Sunucu tarafındaki soket bağlantısı
        self.room_code = None         # Oyuncunun bulunduğu odanın kodu
        self.is_ready = False         # Oyuncu hazır mı?

    def to_dict(self):
        # Sunucudan istemciye JSON ile gönderilecek oyuncu verisi
        # (Socket nesnesi JSON'a çevrilemez, bu yüzden dışarıda bırakılır)
        return {"id": self.id, "nickname": self.nickname, "is_ready": self.is_ready}


# ==========================================
# 2. KITA SINIFI
# Her kıta; bölge listesini ve tam sahiplik bonusunu tutar.
# ==========================================
class Continent:
    def __init__(self, name, bonus_troops, territories):
        self.name = name
        self.bonus_troops = bonus_troops  # Kıtanın tamamına sahip olunca verilen ekstra asker
        self.territories = territories    # Bu kıtadaki node ID'lerinin listesi
        self.owner_id = None              # Kıtayı tamamen elinde bulunduran oyuncunun ID'si


# ==========================================
# 3. BÖLGE (NODE) SINIFI
# Harita üzerindeki her düğümü (bölgeyi) temsil eder.
# ==========================================
class Territory:
    def __init__(self, name, continent_name):
        self.name = name
        self.continent = continent_name  # Hangi kıtada olduğu
        self.owner_id = None             # Bu bölgenin sahibi olan oyuncunun ID'si
        self.troop_count = 0             # Bölgedeki asker sayısı


# ==========================================
# 4. HARİTA (GRAPH) SINIFI
# Tüm bölge ve kıtaları tutan ana veri yapısıdır.
# Komşuluk kontrolü sunucudaki NEIGHBORS sözlüğü üzerinden yapılır.
# ==========================================
class Board:
    def __init__(self):
        # Tüm bölgeler: Key = node ID (str), Value = Territory nesnesi
        self.territories = {}
        # Tüm kıtalar: Key = kıta adı (str), Value = Continent nesnesi
        self.continents = {}

    def add_territory(self, name, continent_name):
        # Yeni bir bölge (node) oluşturur ve haritaya ekler
        self.territories[name] = Territory(name, continent_name)

    def update_continent_ownership(self):
        # Haritadaki tüm kıtaları dolaşır.
        # Bir kıtanın tüm bölgeleri tek oyuncuya aitse o oyuncuyu kıtanın sahibi yapar.
        for continent in self.continents.values():
            if not continent.territories:
                continue

            first_territory_name = continent.territories[0]
            first_owner = self.territories[first_territory_name].owner_id

            if first_owner is None:
                continent.owner_id = None
                continue

            owns_all = all(
                self.territories[t_name].owner_id == first_owner
                for t_name in continent.territories
            )
            continent.owner_id = first_owner if owns_all else None

    def get_player_bonus(self, player_id):
        # Tur başında çağrılır.
        # Oyuncunun tamamen sahip olduğu kıtaların bonus asker toplamını döndürür.
        self.update_continent_ownership()
        total_bonus = 0
        for continent in self.continents.values():
            if continent.owner_id == player_id:
                total_bonus += continent.bonus_troops
        return total_bonus


# ==========================================
# 5. ODA SINIFI
# Her oyun oturumunu (odayı) temsil eder.
# Oyuncuları, oyun durumunu ve haritayı bir arada tutar.
# ==========================================
class Room:
    def __init__(self, room_code):
        self.room_code = room_code
        self.players = []        # Odadaki Player nesneleri (maksimum 2)
        self.is_playing = False  # Oyun başladı mı?
        self.board = Board()     # Bu odaya ait harita nesnesi

        # Oyun akışı değişkenleri
        self.current_turn_player_id = None  # Sırası gelen oyuncunun ID'si
        self.phase = "REINFORCEMENT"        # Mevcut evre: REINFORCEMENT / ATTACK / FORTIFY
        self.turn_count = 1                 # Kaçıncı turda olunduğu
        self.remaining_time = 0             # Mevcut evrenin kalan süresi (saniye)
        self.remaining_bonus_troops = 0     # Takviye evresinde dağıtılacak kalan asker sayısı

    def add_player(self, player):
        # Odaya oyuncu ekler. Oda doluysa (2 kişi) False döner.
        if len(self.players) < 2:
            self.players.append(player)
            player.room_code = self.room_code
            return True
        return False

    def switch_turn(self):
        # Sırayı diğer oyuncuya geçirir ve tur sayacını artırır.
        current_id = self.current_turn_player_id
        for p in self.players:
            if p.id != current_id:
                self.current_turn_player_id = p.id
                break
        self.turn_count += 1

    def is_it_players_turn(self, player_id):
        # Gelen isteğin sırası olan oyuncudan gelip gelmediğini doğrular.
        return self.current_turn_player_id == player_id