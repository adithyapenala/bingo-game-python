

from pydantic import BaseModel

class AssignMatrixRequest(BaseModel):
    game_id: int
    player_name: str
    data: list[list[int]] | None