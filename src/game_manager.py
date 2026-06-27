

import asyncio
import logging
from enum import Enum, auto
from inspect import iscoroutinefunction
from typing import List, Callable, Optional, Awaitable

from .settings import (
    MAX_GAMES, GAME_ID_LENGTH, GAME_JOIN_TIMEOUT, MOVE_TIMEOUT,
    START_GAME_TIMEOUT, MATRIX_SETTING_TIMEOUT
)
from functools import wraps
from random import randint
from . import game_engine as ge

logger = logging.getLogger(__name__)

validGameStateTransitions = {
    ge.GameState.WAITING_TO_JOIN: [
        ge.GameState.WAIT_TO_SET_MATRIX, 
        ge.GameState.FINISHED
            ],
    ge.GameState.WAIT_TO_SET_MATRIX: [
        ge.GameState.READY, 
        ge.GameState.FINISHED
            ],
    ge.GameState.READY: [
        ge.GameState.IN_PROGRESS, 
        ge.GameState.FINISHED
            ],
    ge.GameState.IN_PROGRESS: [
        ge.GameState.IN_PROGRESS,
        ge.GameState.FINISHED
            ]
}

class InvalidGameStateTransitionException(Exception):
    pass

def isValidTranstion(curr: ge.GameState, target: ge.GameState):
    trans = validGameStateTransitions.get(curr, None)
    if trans and target in trans:
        return True
    return False

def GameIdCheck(target_state):
    def decorator(func):
        # 1. Base validation logic shared by both sync and async paths
        def _validate_and_get_game(self, game_id: int):
            game = self.games.get(game_id, None)
            
            if game is None:
                msg = f"Game_{game_id} not found."
                logger.error(msg)
                raise ValueError(msg)
                
            if not isValidTranstion(game.state, target_state):
                msg = f"Cannot call {func.__qualname__} for Game_{game_id} at {game.state} stage."
                logger.warning(msg)
                raise InvalidGameStateTransitionException(msg)
            
            return game

        # 2. Asynchronous wrapper path
        if iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(self, game_id: int, *args, **kwargs):
                _validate_and_get_game(self, game_id)
                return await func(self, game_id, *args, **kwargs)
            return async_wrapper

        # 3. Synchronous wrapper path
        else:
            @wraps(func)
            def sync_wrapper(self, game_id: int, *args, **kwargs):
                _validate_and_get_game(self, game_id)
                return func(self, game_id, *args, **kwargs)
            return sync_wrapper

    return decorator

class TimerKind(Enum):
    MATCHMAKING = GAME_JOIN_TIMEOUT
    READY_TO_START = START_GAME_TIMEOUT
    SET_MATRIX = MATRIX_SETTING_TIMEOUT
    PLAYER_MOVE = MOVE_TIMEOUT


class GameTimerManager:
    """Owns at most one active timer-task per game_id."""

    def __init__(self):
        self._tasks: dict[int, asyncio.Task] = {}
        self._kinds: dict[int, TimerKind] = {}

        logger.debug("GameTimer Manager crreated!")

    def __contains__(self, item):
        return (
            item in self._kinds and 
            item in self._tasks
        )

    def start(self, game_id: int, kind: TimerKind,
              callback: Callable[[int, TimerKind], Awaitable[None]]) -> None:
        self.cancel(game_id)  # sync — just flags the old task for cancellation

        task = asyncio.create_task(self._run(game_id, kind, callback))
        self._tasks[game_id] = task
        self._kinds[game_id] = kind

        logger.debug(f"<GameTimerManager> timer task created for {game_id} with callback {callback.__qualname__}")

    async def _run(self, game_id: int, kind: TimerKind,
                    callback: Callable[[int], Awaitable[None]]) -> None:
        try:
            await asyncio.sleep(kind.value)
        except asyncio.CancelledError:
            return  # superseded or explicitly cancelled — don't fire, don't touch state
        # Only the still-current task for this game_id should fire and clean up.
        if self._kinds.get(game_id) is kind and self._tasks.get(game_id) is asyncio.current_task():
            del self._tasks[game_id]
            del self._kinds[game_id]
            await callback(game_id)

    def cancel(self, game_id: int) -> bool:
        task = self._tasks.pop(game_id, None)
        self._kinds.pop(game_id, None)
        if task and not task.done():
            task.cancel()
            logger.debug(f"<GameTimerManager> task {task.get_name()} cancelled!")
            return True
        return False

    def active_kind(self, game_id: int) -> Optional[TimerKind]:
        return self._kinds.get(game_id)
    
class GameManager:
    """
    Params:
        games (dict): 
            tracks active games.
       
        players(set): 
            Track players to prevent duplicates.

        game_timer(GameTimerManager):
            tracks timers for matchmaking, ready-to-start, player moves. 

    """
    def __init__(self):
        # tracks active games.
        self.games: dict[int, ge.GameLogic] = {} 

        self.timers = GameTimerManager() # tracks timers for matchmaking, ready-to-start, player moves.
       
        self.players = set()  # Track players to prevent duplicates.

    def create_game(self, player_name: str, matrix_size: int = 5):
        if len(self.games) >= MAX_GAMES:
            logger.error("Maximum number of games reached.")
            raise Exception("Maximum number of games reached.")
        if player_name in self.players:
            msg = f"Player {player_name} already in a game."
            logger.error(msg)
            raise Exception(msg)
        
        self.players.add(player_name)

        game_id = self.gen_gameid()
        game = ge.GameLogic(game_id, player_name, matrix_size)
        self.games[game_id] = game
        self.timers.start(
            game_id = game_id, 
            kind=TimerKind.MATCHMAKING, 
            callback=self._handle_game_timeout
        )
        logger.info(f"Game_{game_id} created by player {player_name}!")
        return game
    
    async def _handle_game_timeout(self, game_id: int):
        """
        Handle the timeout for a game. This method is called when the matchmaking timer expires.
        """
        if game_id in self.games:
            logger.info(f"matchmaking timer expired for the game_{game_id}!")
            self.end_game(game_id)


    def gen_gameid(self):
        """
        Generate a unique game ID.
        """
        min_game_id = 10 ** (GAME_ID_LENGTH - 1)
        max_game_id = 10 ** GAME_ID_LENGTH - 1
        while True:
            game_id = randint(min_game_id, max_game_id)
            if game_id not in self.games:
                return game_id
    
    def add_listener(self, game_id: int, cb: Callable):
        if game_id in self.games:
            self.games[game_id].listeners.append(cb)
        

    def remove_listener(self, game_id: int, cb: Callable):
        if game_id in self.games:
            self.games[game_id].listeners.remove(cb)


    @GameIdCheck(target_state = ge.GameState.WAIT_TO_SET_MATRIX)
    def join_game(self, game_id: int, player_name: str):
        
        game = self.games[game_id]
        try:
            game.add_player(player_name)
            self.players.add(player_name)

            self.timers.start(
                game_id=game.id, 
                kind=TimerKind.SET_MATRIX,
                callback=self._handle_matrix_timeout
            )
            game.state = ge.GameState.WAIT_TO_SET_MATRIX
            logger.info(f"Player {player_name} joined game_{game_id}!")
            return game
        except ge.GameFullException as e:
            logger.warning(f"player {player_name} tries to join full game {game_id}!")
            raise ValueError(f"Game is full: {e}")
    
    def join_random_game(self, player_name: str):
        for game in self.games.values():
            if game.player2 is None and game.state == ge.GameState.WAITING_TO_JOIN:
                try:
                    game.add_player(player_name)
                    self.players.add(player_name)
                    self.timers.start(
                        game_id=game.id, 
                        kind=TimerKind.SET_MATRIX,
                        callback=self._handle_matrix_timeout
                    )
                    game.state = ge.GameState.WAIT_TO_SET_MATRIX
                    logger.info(f"Player {player_name} joined game_{game.id}!")
                    return game
                except ge.GameFullException as e:
                    continue  # This should not happen, but just in case
        logger.warning("No available games to join.")
        raise ValueError("No available games to join.")
    
    @GameIdCheck(target_state = ge.GameState.READY)
    async def _handle_matrix_timeout(self, game_id: int):
        game = self.games.get(game_id)
        if game.player1.m is None:
            logger.info(f"Random matrix assigned to player {game.player1.name} for game_{game.id}")
            game.player1.assign_matrix(ge.Matrix.create_random_matrix(game.player1.matrix_size))
        if game.player2.m is None:
            logger.info(f"Random matrix assigned to player {game.player2.name} for game_{game.id}")
            game.player2.assign_matrix(ge.Matrix.create_random_matrix(game.player1.matrix_size))
        game.state = ge.GameState.READY
    
    @GameIdCheck(target_state = ge.GameState.READY)    
    def assign_matrix(
        self, game_id: int, 
        player_name:str, 
        data: List[List[int]] | None = None
    ):
        game = self.games.get(game_id, None)
       
        msg = None
        try:
            player = game.get_player(player_name)
            if data is not None:
                matrix = ge.Matrix.create_matrix(player.matrix_size, data)
            else: 
                matrix = ge.Matrix.create_random_matrix(player.matrix_size)
            player.assign_matrix(matrix)
            
            game.assigned_matrix.add(player_name)

            logger.info(f"Player {player_name} assigned matrix for the game_{game_id}!")
            if (
                game_id in self.timers and 
                len(game.assigned_matrix) >= 2
            ):
                logger.info("All players assigned the matrix!")
                game.state = ge.GameState.READY
                self.timers.start(
                    game_id,
                    TimerKind.READY_TO_START,
                    self._handle_ready_timeout
                )

        except ge.PlayerNotFoundException as e:
            msg = f"Player {player_name} not found!"
            raise ValueError(msg + e)
        except ValueError as e:
            msg = f"Invalid data!"
            raise ValueError(msg + e)
        except ge.InvalidMatrixException as e:
            msg = f"Error assigning matrix!"
            raise ValueError(msg + e)
        finally:
            if msg is not None:
                logger.warning(msg)

    @GameIdCheck(target_state=ge.GameState.IN_PROGRESS)    
    async def _handle_ready_timeout(self, game_id: int):
        """
        Handle the timeout for signalling to ready for the game. 
        This method is called when the start game timer expires.
        """
        logger.info(f"start timer expired for game_{game_id}")
        self.games[game_id].state = ge.GameState.IN_PROGRESS
        self.start_game(game_id)

    @GameIdCheck(target_state=ge.GameState.IN_PROGRESS)  
    def signal_ready(self, game_id: int, player_name: str):
        """
        
        """
        game = self.games.get(game_id, None)
        if (
            game.player1.name == player_name or
            game.player2.name == player_name
        ):  
            game.ready_to_play.add(player_name)
            logger.debug(f"player {player_name} signalled ready for game_{game_id}!")

        if len(game.ready_to_play) >= 2:
            logger.info(f"All players signalled for ready to start the game_{game_id}")
            game.state = ge.GameState.IN_PROGRESS
            self.start_game(game_id)
    
                
    @GameIdCheck(target_state=ge.GameState.IN_PROGRESS)  
    def start_game(self, game_id: int):
        game = self.games.get(game_id, None)
    
        if game.player2 is None:
            msg = f"Cannot start game_{game_id} without two players."
            logger.warning(msg)
            raise ValueError(msg)
        if (
            game.player1.m is None or 
            game.player2.m is None or 
            len(game.assigned_matrix) < 2
        ):
            msg = f"Both players must have assigned matrices to start the game_{game_id}."
            logger.warning(msg)
            raise ValueError(msg)
                    
        logger.info(f"Game_{game_id} has started.")

        self.timers.start(
            game_id=game_id, 
            kind=TimerKind.PLAYER_MOVE, 
            callback=self._handle_move_timeout
        )
    
    @GameIdCheck(target_state = ge.GameState.IN_PROGRESS)        
    def make_move(self, game_id: int , player_name: str, key: int):
        game = self.games.get(game_id, None)
        
        try:
            player = game.get_player(player_name)
            self.timers.start(
                game_id=game_id, 
                kind=TimerKind.PLAYER_MOVE, 
                callback=self._handle_move_timeout
            )
            logger.debug(f"player {player.name} striked off {key} in game_{game_id}.")
            return game.validateMove(key, player_name)
        
        except ge.PlayerNotFoundException as e:
            msg = f"Player {player_name} not found!"
            logger.warning(msg)
            raise ValueError(msg + e)
        
    @GameIdCheck(target_state = ge.GameState.IN_PROGRESS)      
    async def _handle_move_timeout(self, game_id: int):
        """
        Handle the timeout for a move. This method is called when the move timer expires.
        """
        g = self.games.get(game_id, None)
        p = g.whose_turn().name if g is not None else "player"
        logger.warning(f"move timer expired for player {p} game_{game_id}.")
        # notify players, winner is other player
        self.end_game(game_id)
  
    def end_game(self, game_id: int):
        game = self.games.get(game_id, None)
        if game is not None:
            game.state = ge.GameState.FINISHED
            del self.games[game_id]
            p1 = game.player1
            p2 = game.player2
            if(
                p1 is not None and 
                p1.name in self.players
            ):
                self.players.remove(p1.name)
            if(
                p2 is not None and 
                p2.name in self.players
            ):
                self.players.remove(p2.name)
        self.timers.cancel(game_id)  # Cancel any active start game timer
        logger.info(f"Game_{game_id} finished!")

