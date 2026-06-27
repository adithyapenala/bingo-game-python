""" 
This module contains the main Flask application for the Bingo game.
It defines the routes and logic for handling game creation, joining, and gameplay. 
The application interacts with the GameManager to manage game state and player interactions.
"""
# uses websockets
import logging
from fastapi import FastAPI
from .models import *
from .game_manager import GameManager as Gm

app = FastAPI()

gm = Gm()

logger = logging.getLogger(__name__)

@app.post('/create_game')
async def create_game(player_name: str):
    try:
        game = gm.create_game(player_name)
        # logger.info(f"Received create game request")
        return {'game_id': game.id}, 200
    except Exception as e:
        return {'error': str(e)}, 400
    
@app.post('/join_game/{game_id}')
async def join_game(game_id: int, player_name: str):
    try:
        game = gm.join_game(game_id, player_name)
        return {'message': f'Joined game {game.id} successfully.'}, 200
    except Exception as e:
        return {'error': str(e)}, 400
    
@app.post('/join_random_game')
async def join_random_game(player_name: str):
    try:
        game = gm.join_random_game(player_name)
        return {'game_id': game.id, 'message': f'Joined game {game.id} successfully.'}, 200
    except Exception as e:
        return {'error': str(e)}, 400
    
@app.post('/assign_matrix/{game_id}')
async def assign_matrix(request: AssignMatrixRequest):
    try:
        gm.assign_matrix(**request.model_dump())
        return {'message': 'Matrix assigned successfully.'}, 200
    except Exception as e:
        return {'error': str(e)}, 400
    
@app.post('/start_game/{game_id}')
async def signal_ready_to_start(game_id: int, player_name: str):
    try:
        gm.signal_ready(game_id, player_name)
        return {'message': f'Player is ready to start.'}, 200
    except Exception as e:
        return {'error': str(e)}, 400 

