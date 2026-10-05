# Risk: a two-player online version (Python, TCP sockets, PyQt5)

An unofficial, student-built online version of the board game **Risk**: two players conquer a world map by placing armies, attacking neighbouring territories with dice, and moving troops. It was built for a Computer Networks course (April to May 2026). A multithreaded TCP server hosts the game rooms and enforces the rules; a PyQt5 client talks to it with newline-delimited JSON messages.

> Risk is a trademark of Hasbro. This is an independent course project, not affiliated with or endorsed by Hasbro.

## Gameplay (as implemented in the server)

- Two players per room. A room is identified by a 4-character code; both players press READY to start.
- **Map:** 42 territories on 6 continents with the same continent sizes as the classic board (North America 9, South America 4, Europe 7, Africa 6, Asia 12, Australia 4); the neighbour graph is in `Server.py` (`NEIGHBORS`). Owning a whole continent gives bonus troops (see the table below).
- **Setup:** territories are split 21/21 at random; each player starts with 50 troops (at most 7 per territory); the first player is random.
- **A turn has three timed phases:**
  1. *Reinforcement* (30 s): receive `max(3, owned territories / 3)` troops plus continent bonuses and place them one by one. Troops left unplaced when the time runs out are spread randomly.
  2. *Attack* (45 s): attack a neighbouring enemy territory. The attacker rolls up to 3 dice (at most troops − 1), the defender up to 2; the highest dice are compared pairwise and ties go to the defender. A conquest moves troops into the new territory.
  3. *Fortify* (30 s): move troops between your own territories if they are connected through a path of your own territories (breadth-first search). The move ends the turn.
- You win by owning all 42 territories, or when your opponent disconnects.

### Differences from the board game

- Exactly two players per room; automatic setup; per-phase time limits.
- No territory cards and no mission cards.
- Continent bonuses differ from the classic values (classic values as listed on [Wikipedia](https://en.wikipedia.org/wiki/Risk_(game))):

| Continent | Classic game | This implementation |
|---|---|---|
| North America | 5 | 4 |
| South America | 2 | 3 |
| Europe | 5 | 5 |
| Africa | 3 | 4 |
| Asia | 7 | 6 |
| Australia | 2 | 2 |

## Architecture

| File | Role |
|---|---|
| `Server.py` | TCP server: one thread per client, one timer thread per game, shared state in module-level dictionaries, rule enforcement |
| `models.py` | `Player`, `Room`, `Board`, `Territory`, `Continent` |
| `game_engine.py` | game setup and turn start |
| `client_main.py`, `Form/*.ui` | PyQt5 client; screens (login, lobby, room, game, game over) designed in Qt Designer |
| `network_worker.py` | `QThread` that keeps socket I/O off the UI thread |

**Protocol:** one JSON object per line over TCP port 5555.
Client to server: `LOGIN`, `CREATE_ROOM`, `JOIN_ROOM`, `READY`, `PLACE_TROOP`, `NEXT_PHASE`, `ATTACK_TERRITORY`, `FORTIFY_MOVE`.
Server to client: `LOGIN_SUCCESS`, `ROOM_UPDATED`, `GAME_START`, `BOARD_UPDATE`, `PHASE_CHANGED`, `TIME_TICK`, `BATTLE_REPORT`, `GAME_OVER`, `ERROR`.

## Run locally

```bash
pip install -r requirements.txt     # PyQt5
python Server.py                    # listens on 0.0.0.0:5555
python client_main.py               # start it twice, one window per player
```

The client connects to `127.0.0.1` by default; set the `RISK_SERVER_HOST` environment variable to use another host. The original build used a cloud-hosted server; its address is not part of this repository.

## Verification and limitations

- When this repository was published, the server flow was checked with two scripted TCP clients on localhost: login, room creation and joining (a third player is rejected), READY to game start (42 territories, 21 each, 50 troops each), troop placement, rejection of out-of-turn and wrong-territory placement, phase changes, and "opponent disconnects, remaining player wins". **The PyQt5 client was not run, and the attack and fortify handlers were only read, not exercised.**
- Shared state is not protected by locks. For example, if both players send READY at almost the same instant, the game can be set up twice.
- There is no authentication and nicknames are not validated.
- Ports, timers and rules are hard-coded constants.
- Before publishing, the history was rewritten to drop non-source files (course documents, bytecode caches, editor settings, a credentials file) and the server address. Authorship and dates are unchanged.

## Türkçe özet

Bilgisayar Ağları dersi için geliştirilen, **Risk** masa oyununun iki kişilik çevrimiçi uygulaması (resmi değildir). Çok iş parçacıklı bir TCP sunucusu odaları ve kuralları yönetir (42 bölge, 6 kıta, takviye/saldırı/kaydırma evreleri, zar savaşları, süre sayacı); PyQt5 istemcisi sunucuyla satır başına bir JSON mesajıyla konuşur. Oyunda iki oyuncu, bölge/görev kartları ve klasik kıta bonus değerleri yoktur. Sunucu akışı iki betikli istemciyle yerelde doğrulandı; arayüz çalıştırılmadı. Kilit (lock) kullanılmaması gibi bilinen sınırlar yukarıda listelenmiştir.

## License

No license is specified: this is a shared course project published for reference.
