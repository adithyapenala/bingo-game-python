

from pydantic import BaseModel

class HasJoinedIn(BaseModel):
    game_id: int

class CreateIn(BaseModel):
    player_name: str

class SignalReadyIn(CreateIn):
    game_id: int

class AssignMatrixRequest(SignalReadyIn):
    data: list[list[int]] | None

class GameMoveIn(SignalReadyIn):
    key: int