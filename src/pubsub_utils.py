
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
