
import logging
from enum import StrEnum, auto
from collections import defaultdict
from typing import List
from random import shuffle
from .settings import MAX_MATRIX_SIZE

logger = logging.getLogger(__name__)

class InvalidMatrixException(BaseException):
    pass
class PlayerNotFoundException(BaseException):
    pass
class GameFullException(BaseException):
    pass
# class InvlaidMoveException(BaseException):
#     pass

class MoveState(StrEnum):
    VALID_MOVE = auto()
    INVALID_MOVE = auto()
    WINNER = auto()
    DRAW = auto()

class GameState(StrEnum):
    """
    WAITING_TO_JOIN: game just created by player1, waiting for player to join.

    WAIT_TO_SET_MATRIX: player2 joined, waiting for players to assign matirces

    READY: both players' matrices assigned, waiting for players ready signal

    IN_PROGRESS: game started , moves in progress

    FINISHED: win/termination condition acheived, game stop 
    """
    WAITING_TO_JOIN = auto()        # just created by player1, waiting for player to join
    WAIT_TO_SET_MATRIX = auto()     # player2 joined, waiting for players to assign matirces
    READY = auto()                  # matrices assigned, waiting for players ready signal
    IN_PROGRESS = auto()            # moves in progress
    FINISHED = auto()               # win condition acheived, game stop

class Matrix:
    def __init__(self, size: int, data: List[List[int]] = None):
        self.size: int = size
        if data:
            self._data: List[List[int]] = data

    @classmethod
    def create_matrix(cls, size: int, data: List[List[int]]):
        """ 
        Factory method to create a matrix instance with validation.
        """
        # 1. Perform your validation logic here
        if size > MAX_MATRIX_SIZE:
            raise ValueError(f"Matrix size exceeds maximum allowed size of {MAX_MATRIX_SIZE}.")
        
        if (
            len(data) != size or 
            any(len(row) != size for row in data)
        ):
            raise ValueError("Data dimensions do not match the specified size.")
        
        if (
            not all(
                isinstance(elem, int) for row in data for elem in row
            )
        ):
            raise ValueError("All elements in the matrix must be integers.")
        
        if (
            sorted(elem for row in data for elem in row) != 
            list(range(1, size * size + 1))
        ):
            raise ValueError("Matrix must contain all integers from 1 to size^2 exactly once.")
        
        # 2. Create the matrix instance
        matrix_instance = cls(size, data)
        
        return matrix_instance
    
    @classmethod
    def create_random_matrix(cls, size: int):
        """ 
        Factory method to create a matrix instance with validation.
        """
        # 1. Perform your validation logic here
        if size > MAX_MATRIX_SIZE:
            raise ValueError(f"Matrix size exceeds maximum allowed size of {MAX_MATRIX_SIZE}.")
        flat_list  = [i for i in range(1, size * size + 1)]
        data = [[i for i in range(size)] for _ in range(size)] # list is randomly populated here
        shuffle(flat_list)
        for i in range(size):
            for j in range(size):
                data[i][j] = flat_list[i * size + j]

        return cls(size, data)
        
    
    def insertAt(self: Matrix, i: int, j: int, key: int):
        self._data[i][j] = key

    def find(self, key: int):
        for i, a in enumerate(self._data):
            for j, elem in enumerate(a):
                if elem == key:
                    return i,j
        return None

    def copy(self, m: Matrix):
        if m.isValid():
          self._data = m._data 
        else:
            raise InvalidMatrixException("Invalid matrix!")

    def __contains__(self, key: int):
        for row in self._data:
            if key in row: return True
        return False
    
    def __getitem__(self, index):
        row, col = index
        return self._data[row][col]
    
    def __setitem__(self, index, key: int):
        row, col = index
        self._data[row][col] = key

    def isValid(self):
        """
        Validate that matrix contains all elems from
        1 to size^2.
        """
        flat_list = [elem for row in self._data for elem in row]
        return sorted(flat_list) == list(range(1, self.size * self.size + 1))
    
    
    def shuffle_matrix(self):
        """
        Shuffle the matrix elements in place.
        """
        flat_list = [elem for row in self._data for elem in row]
        shuffle(flat_list)
        for i in range(self.size):
            for j in range(self.size):
                self._data[i][j] = flat_list[i * self.size + j]

    def to_list(self) -> List[List[int]]:
        """ Returns the matrix as a list of lists. """
        return self._data

    def calculate_score(self) -> int:
        """ Calculates the score of the given player."""
        return (
            self.score_row_wise() +
            self.score_col_wise() +
            self.score_main_diagonal_wise() +
            self.score_anti_diagonal_wise()
        )

    def score_row_wise(self) -> int:
        return sum(1 for row in self._data if not any(row))

    def score_col_wise(self) -> int :
        transposed = zip(*self._data)
        return sum(1 for col in transposed if not any(col))         

    def score_main_diagonal_wise(self) -> int:
        return 0 if all(self._data[i][i] for i in range(self.size)) else 1

    def score_anti_diagonal_wise(self) -> int:
        return 0 if all(self._data[i][self.size -1 - i] for i in range(self.size)) else 1

class Player:
    def __init__(self, name: str, matrix_size: int):
        self.name: str = name
        self.matrix_size: int = matrix_size
        self.m: Matrix = None
        self.score: int = 0
    
    
    def assign_matrix(self, matrix: Matrix):
        """ 
        Factory method to create a player instance with validation.
        """
        # 1. Perform your validation logic here
        if matrix.size != self.matrix_size:
            raise InvalidMatrixException(f"Matrix size doesn't match player's expected size.")
        
        if not matrix.isValid():
            raise InvalidMatrixException("Invalid matrix!")
            
        self.m = Matrix.create_matrix(matrix.size, matrix._data)

class GameLogic:
    """
    Params:
        id (int):
            4 digit id of the game. Randomly generated by Game Manager.

        player1 (Player):

        player2 (Player):

        turn (int):

        state (GameState):

        max_score (int):

        assigned_matrix (set):
            set of names (str) of players who assigned their matrix for the game.

        ready_to_play (set):
            set of names (str) of players who signalled ready-to-play.

        listeners (list):
            list of Callable objects which are
    """
    def __init__(self,game_id: int, player_name: str, matrix_size: int):
        self.id : int = game_id
        self.player1 : Player = Player(player_name, matrix_size)
        self.player2 : Player = None
        self.turn : int = 0
        self.state : GameState = GameState.WAITING_TO_JOIN
        self.max_score : int = matrix_size

        self.assigned_matrix = set()

        self.ready_to_play = set()

        self.listeners = dict()

    @classmethod
    def create_game(cls, game_id: int, player_name: str, matrix_size: int):
        """ 
        Factory method to create a game instance with validation.
        """
        
        if matrix_size > MAX_MATRIX_SIZE:
            raise InvalidMatrixException("Invalid matrix!")
    
        return cls(game_id, player_name, matrix_size)
    
    def add_player(self, player_name: str):
        """ Adds a second player to the game."""
        if self.player2 is not None:
            raise GameFullException("Game already has two players.")
        self.player2 = Player(player_name, self.player1.matrix_size)

    def get_player(self, player_name: str) -> Player:
        """ returns the player object for the given player name."""
        if player_name == self.player1.name:
            return self.player1
        elif player_name == self.player2.name:
            return self.player2
        else:
            raise PlayerNotFoundException("player not found!")  

    def get_other_player(self, player_name: str) -> Player:
            """ returns the player object for the given player name."""
            if player_name == self.player1.name:
                return self.player2
            elif player_name == self.player2.name:
                return self.player1
            else:
                raise PlayerNotFoundException("player not found!")

    def other_p_ready(self, p_name):
        other = self.get_other_player(p_name)
        return other in self.ready_to_play
    
    def whose_turn(self) -> Player:
        """ Returns the player whose turn it is. """
        return self.player1 if self.turn % 2 == 0 else  self.player2

    def validateMove(self, key: int, player_name: str):
        """ 
        Validates the move and returns the winner if any, 
        else None or 'DRAW' if both players have won. 
        
        """
        if self.state == GameState.READY:
            self.state = GameState.IN_PROGRESS
        elif self.state == GameState.FINISHED:
            return MoveState.INVALID_MOVE, "Game already finished!"
        
        if not player_name == self.whose_turn().name:
            return MoveState.INVALID_MOVE, f"player {self.whose_turn().name}'s turn not player {player_name}"

        cord1 = self.player1.m.find(key)
        cord2 = self.player2.m.find(key)
        if ( 
           cord1 is None or 
           cord2 is None
        ):
            return MoveState.INVALID_MOVE, "Number already striked off"
        
        self.turn += 1
        self.player1.m[*cord1] = 0
        self.player2.m[*cord2] = 0

        return self.any_winner()

    def any_winner(self) -> List[MoveState, str]:
        """ 
        Returns the state of the game if any,
          else None or 'DRAW' if both players have won.
        """
        self.player1.score = self.calculate_score(self.player1)
        self.player2.score = self.calculate_score(self.player2)

        if (
            self.player1.score >= self.max_score and 
            self.player2.score < self.max_score
        ):
            self.state = GameState.FINISHED
            return MoveState.WINNER, self.player1.name
        elif (
            self.player2.score >= self.max_score and 
            self.player1.score < self.max_score
        ):
            self.state = GameState.FINISHED
            return MoveState.WINNER, self.player2.name
        elif ( 
            self.player1.score >= self.max_score and 
            self.player2.score >= self.max_score
        ):
            self.state = GameState.FINISHED
            return MoveState.DRAW, "DRAW"
        else: 
            return MoveState.VALID_MOVE, "VALID_MOVE"

    def calculate_score(self, player: Player) -> int:
        """ Calculates the score of the given player."""
        return player.m.calculate_score()