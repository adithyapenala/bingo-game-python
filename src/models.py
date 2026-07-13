

from pydantic import BaseModel

class SignalReadyIn(BaseModel):
    game_id: int
    player_name: str

class AssignMatrixRequest(SignalReadyIn):
    data: list[list[int]] | None

class GameMoveIn(SignalReadyIn):
    key: int