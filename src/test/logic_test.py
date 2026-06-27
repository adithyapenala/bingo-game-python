import random
import logging
import game_engine as ge

logger = logging.getLogger(__name__)

def random_cords(length: int = 5):
    return random.randint(0, length * length - 1)

def test_score_calulator():
    data1 = [[0] * 5 for _ in range(5)]
    m = ge.Matrix(5, data1)

    # assert m.isValid() == True

    assert m.score_row_wise() == 5

    assert m.score_col_wise() == 5

    assert m.score_anti_diagonal_wise() == 1

    assert m.score_main_diagonal_wise() == 1

def test_game_engine():

    game = ge.GameLogic.create_game(1, "player1", 5)
    game.add_player("player2")

    game.player1.assign_matrix(ge.Matrix.create_random_matrix(5))
    game.player2.assign_matrix(ge.Matrix.create_random_matrix(5))

    assert game.player1.m.isValid() == True
    assert game.player2.m.isValid() == True

    assert game.whose_turn().name == "player1"
    
    state, msg = game.validateMove(random_cords(), game.player1.name)

    while game.state != ge.GameState.FINISHED:
        cord = random_cords()
        logger.debug(f"Player {game.whose_turn().name} is making a move at {cord}\n")
        state, msg = game.validateMove(cord, game.whose_turn().name)
        logger.debug(f"Move result: {state}, Message: {msg}\n")
        logger.debug(f"player {game.player1.name} score: {game.player1.score}")
        logger.debug(f"player {game.player2.name} score: {game.player2.score}")

if __name__ == "__main__":
    test_game_engine()

    


