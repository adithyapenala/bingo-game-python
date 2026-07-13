""" 
This module contains the main Flask application for the Bingo game.
It defines the routes and logic for handling game creation, joining, and gameplay. 
The application interacts with the GameManager to manage game state and player interactions.
"""
# uses websockets
import logging
import asyncio
from fastapi import ( 
    FastAPI, WebSocket, WebSocketDisconnect
)
from .models import *
from .game_manager import GameManager as Gm
from .game_engine import MoveState, GameState
from .pubsub_utils import *

app = FastAPI()

gm = Gm()

conn_manager = ConnectionManager()

logger = logging.getLogger(__name__)

# ------ Websocket Endpoints ------

@app.websocket('/create_game')
async def create_game(ws: WebSocket, player_name: str):
    await conn_manager.connect(player_name, None, ws)
    try:
        game = gm.create_game(player_name)
        gm.subscribe(
            game.id,
            GameDroppedEvent(game_id=game.id),
            notify_game_dropped
        )
        # logger.info(f"Received create game request")
        return ws.send_json({'game_id': game.id, 'message': f'Game {game.id} created successfully.'})
    except Exception as e:
        return ws.send_json({'error': str(e)})

@app.websocket('/join_game/{game_id}')
async def join_game(ws: WebSocket, game_id: int, player_name: str):
    await conn_manager.connect(player_name, game_id, ws)
    try:
        game = gm.join_game(game_id, player_name)
        return ws.send_json({'message': f'Joined game {game.id} successfully.'})
    except Exception as e:
        return ws.send_json({'error': str(e)})
    
@app.websocket('/join_random_game')
async def join_random_game(ws: WebSocket, player_name: str):
    await conn_manager.connect(player_name, None, ws)
    try:
        game = gm.join_random_game(player_name)
        return ws.send_json({'game_id': game.id, 'message': f'Joined game {game.id} successfully.'})
    except Exception as e:
        return ws.send_json({'error': str(e)})

@app.websocket('/assign_matrix/{game_id}')
async def assign_matrix(ws: WebSocket, game_id: int, player_name: str):
    await conn_manager.connect(player_name, game_id, ws)
    try:
        data = await ws.receive_json()
        req = AssignMatrixRequest(**data)
        gm.assign_matrix(**req.model_dump())
        return ws.send_json({'message': 'Matrix assigned successfully.'})
    except Exception as e:
        return ws.send_json({'error': str(e)})
    
@app.websocket('/start_game/{game_id}')
async def signal_ready_to_start(ws: WebSocket, game_id: int, player_name: str):
    await conn_manager.connect(player_name, game_id, ws)
    try:
        data = await ws.receive_json()
        req = SignalReadyIn(**data)
        gm.signal_ready(**req.model_dump())
        gm.subscribe(
            game_id,
            GameStartedEvent(game_id=game_id),
            notify_game_started
        )
        gm.subscribe(
            game_id,
            WinDeclaredEvent(game_id=game_id, winner_name=None),
            notify_win_declared
        )
        gm.subscribe(
            game_id,
            DrawDeclaredEvent(game_id=game_id),
            notify_draw_declared
        )
        return await ws.send_json({'message': f'Player is ready to start.'})
    except Exception as e:
        return await ws.send_json({'error': str(e)})


@app.websocket('/game/{game_id}/move')
async def game_move(ws: WebSocket, game_id: int, player_name: str):
    await conn_manager.connect(player_name, game_id, ws)
    try:
        data = await ws.receive_json()
        req = GameMoveIn(**data)
        move_state, msg = gm.make_move(**req.model_dump())
        if move_state == MoveState.VALID_MOVE:
            await conn_manager.sendall(game_id, player_name, {'event': 'player_moved', 'player_name': player_name, 'key': req.key})
        return await ws.send_json({'message': msg, 'move_state': move_state.name})
    except Exception as e:
        return await ws.send_json({'error': str(e)})
    

# -------- PubSub Event Handlers --------

def notify_game_started(event: GameStartedEvent):
    logger.info(f"Game {event.game_id} has started.")
    # Broadcast to all players in the game that the game has started
    asyncio.create_task(conn_manager.broadcast(event.game_id, {'event': 'game_started'}))

def notify_game_dropped(event: GameDroppedEvent):
    logger.info(f"Game {event.game_id} has been dropped.")
    # Broadcast to all players in the game that the game has been dropped
    asyncio.create_task(conn_manager.broadcast(event.game_id, {'event': 'game_dropped'}))
    conn_manager.disconnect_all(event.game_id)  # Disconnect all players from the dropped game

def notify_win_declared(event: WinDeclaredEvent):
    logger.info(f"Player {event.winner_name} has won the game {event.game_id}.")
    # Broadcast to all players in the game that a win has been declared
    asyncio.create_task(conn_manager.broadcast(event.game_id, {'event': 'win_declared', 'winner_name': event.winner_name}))

def notify_draw_declared(event: DrawDeclaredEvent):
    logger.info(f"Game {event.game_id} has ended in a draw.")
    # Broadcast to all players in the game that a draw has been declared
    asyncio.create_task(conn_manager.broadcast(event.game_id, {'event': 'draw_declared'}))


# -------- REST Api endpoint --------

@app.get('/game_state/{game_id}')
async def get_game_state(game_id: int, player_name: str):
    """
     fetches the game state, mainly for reconnected players.
    """
    if game_id not in gm.games:
        return {'error': 'Game not found'}, 404 
    if player_name not in gm.games[game_id].players:
        return {'error': 'Player not found in the game'}, 400
    return {
        'game_id': game_id,
        'player_name': player_name,
        'matrix': gm.games[game_id].players[player_name].matrix.to_list(),
    }


        


