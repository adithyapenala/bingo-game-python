""" 
This module contains the main Flask application for the Bingo game.
It defines the routes and logic for handling game creation, joining, and gameplay. 
The application interacts with the GameManager to manage game state and player interactions.
"""
# uses websockets
import logging
from typing import Optional
from fastapi import FastAPI, Query
from .models import *
from .game_manager import GameManager as Gm
from .game_engine import GameState

app = FastAPI()

gm = Gm()

logger = logging.getLogger(__name__)

@app.get('/{game_id}/status')
async def get_status(game_id: int):
    try:
        g = gm.games.get(game_id, None)
        if g is not None:
            return {'state': g.state}, 200
        else:
            return {'state': None, 'message': "game not found"}, 500
    except Exception as e:
        return {'error': str(e)}, 400

@app.post('/create_game')
async def create_game(request: CreateIn):
    try:
        game = gm.create_game(**request.model_dump())
        # logger.info(f"Received create game request")
        return {'game_id': game.id}, 200
    except Exception as e:
        return {'error': str(e)}, 400
    
@app.post('/join_game/{game_id}')
async def join_game(request: SignalReadyIn):
    try:
        game = gm.join_game(**request.model_dump())
        return {'message': f'Joined game {game.id} successfully.', 'game_id': game.id}, 200
    except Exception as e:
        logger.warning(f'Cannot join game, {str(e)}')
        return {'error': str(e)}, 400
    
@app.post('/join_random_game')
async def join_random_game(request: CreateIn):
    try:
        game = gm.join_random_game(**request.model_dump())
        return {'game_id': game.id, 'message': f'Joined game {game.id} successfully.'}, 200
    except Exception as e:
        return {'error': str(e)}, 400

@app.get('/{game_id}/has_joined')
async def has_2nd_player_joined(game_id: int):
    """
        returns http status code `200` if other player has joined, Else `202`
    """
    try:
        game = gm.games.get(game_id, None)
        if game is not None:
            if game.state == GameState.WAIT_TO_SET_MATRIX:
                logger.debug(f'{game.player1.name} , {game.player2.name} are the players')
                return {'has_joined': 'true','game_id': game.id, 'message': f'Player 2 joined game {game.id} successfully.'}, 200
            elif game.state == GameState.WAITING_TO_JOIN:
                return {'has_joined': 'true','game_id': game.id, 'message': f'Player 2 not joined game {game.id}.'}, 202
            else:
                return {'message': 'invalid request'}, 500
        else:
            return {'error': "Invalid game id"}, 500
    except Exception as e:
        return {'error': str(e)}, 400

@app.post('/assign_matrix/{game_id}')
async def assign_matrix(request: AssignMatrixRequest):
    try:
        gm.assign_matrix(**request.model_dump())
        return {'message': 'Matrix assigned successfully.'}, 200
    except Exception as e:
        return {'error': str(e)}, 400

@app.get('/{game_id}/has_assigned_matrix')
async def has_other_player_assigned_matrix(game_id: int):
    """
        returns http status code `200` if other player has assigned matrix, Else `202`
    """
    try:
        game = gm.games.get(game_id, None)
        if game is not None:
            if game.state == GameState.READY:
                return {'game_id': game.id, 'message': f'All players assigned matrix successfully.', 'state': 'ready'}, 200
            else :
                return {'game_id': game.id, 'message': f'Some players not assigned matrix.', 'state': 'wait'}, 202
        else:
            return {'error': "Invalid game id"}, 500
    except Exception as e:
        return {'error': str(e)}, 400

@app.post('/start_game/{game_id}')
async def signal_ready_to_start(game_id: int, request: CreateIn):
    try:
        gm.signal_ready(game_id, **request.model_dump())
        return {'message': f'Player is ready to start.'}, 200
    except Exception as e:
        return {'error': str(e)}, 400 


@app.get('/{game_id}/has_signalled')
async def has_other_signalled_ready(game_id: int, request: CreateIn):
    """
    returns http status code `200` if other player is ready, Else `202`
    """
    try:
        if gm.has_other_player_signalled(game_id,**request.model_dump()):
            return {'message': f'Player is ready to start.'}, 200
        else:
            return {'message': f'Player is not ready to start.'}, 202
    except Exception as e:
        return {'error': str(e)}, 400 
        
@app.post('/move/{game_id}')
async def make_move(request: GameMoveIn):
    try:
        state, msg = gm.make_move(**request.model_dump())
        return {'message': msg, 'state': state}, 200
    except Exception as e:
        return {'error': str(e)}, 400 

@app.get('/{game_id}/has_opponent_moved')
async def has_opponent_moved(game_id: int, request: CreateIn):
    """
        returns http status code `200` if other player made their move, Else `202`.
    """
    state, key = gm.other_p_move(game_id,**request.model_dump())
    try:
        if gm.other_p_move(game_id,**request.model_dump()) != None:
            return {'message': f'other Player is made move.', 'key': key, 'state': state}, 200
        else:
            return {'message': f'other Player is not yet made move.'}, 202
    except Exception as e:
        return {'error': str(e)}, 400 