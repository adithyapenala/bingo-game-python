
import logging
from datetime import datetime
from fastapi import WebSocket
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Event:
    game_id: int
    
class GameStartedEvent(Event):
    pass

class GameMoveEvent(Event):
    curr_turn: str
    key: int
    
class WinDeclaredEvent(Event):
    winner_name: str

class DrawDeclaredEvent(Event):
    pass

class GameDroppedEvent(Event):
    pass

class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type: Event, callback):
        self.subscribers[event_type.game_id].append(callback)

    def publish(self, event: Event, *args, **kwargs):
        for callback in self.subscribers[event.game_id]:
            callback(event.game_id, *args, **kwargs)

@dataclass
class ClientConnection:
    player_name: str
    websocket: WebSocket
    game_id: int 
    connected_at: datetime
    last_seen: datetime
    notification_buffer: list[dict] = field(default_factory=list)
    
class ConnectionManager:
    def __init__(self):
        # key: player_name, value: ClientConnection
        self.connections = defaultdict(set)
        # key: game_id, value: set of player_names
        self.games = defaultdict(set)

    async def connect(self, player_name: str, game_id: int, ws: WebSocket):
        await ws.accept()

        old = self.connections.get(player_name, None)

        old_game = self.games.get(game_id, None)

        if old is not None:
            if old_game is not None and old.game_id != game_id:
                logger.warning(f"Player {player_name} is trying to connect to a different game {game_id} while already connected to game {old.game_id}.")
                await ws.close()
                return
            try:
                await old.websocket.close()
                old.websocket = ws
            except Exception as e:
                logger.warning(f"Failed to close old websocket for player {player_name}: {e}")
            finally: 
                old.last_seen = datetime.now()
        else:
            self.connections[player_name].add(ClientConnection(
                player_name=player_name,
                websocket=ws,
                game_id=game_id,
                connected_at=datetime.now(),
                last_seen=datetime.now()
            ))
            self.games[game_id].add(player_name)

    async def disconnect(self, player_name: str):
        self.connections.pop(player_name, None)
        for game_id, players in self.games.items():
            players.discard(player_name)

    async def disconnect_all(self, game_id: int):
        players = self.games.get(game_id, set())
        for player_name in players:
            await self.disconnect(player_name)
        self.games.pop(game_id, None)

    async def send_msg(self, player_name: str, message: dict):
        client = self.connections.get(player_name, None)
        if client is not None:
            ws = client.websocket
            try:
                if not client.notification_buffer:
                    for msg in client.notification_buffer:
                        await ws.send_json(msg)
                    client.notification_buffer.clear()
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to player {player_name}: {e}")
                client.notification_buffer.append(message)

    async def broadcast(self, game_id: int, message: dict):
        players = self.games.get(game_id, set())
        for player_name in players:
            await self.send_msg(player_name, message)

    async def sendall(self, game_id: int,player_name: str, message: dict):
        players = self.games.get(game_id, set())
        for name in players:
            if name != player_name:
                await self.send_msg(name, message)