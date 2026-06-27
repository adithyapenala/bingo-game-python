import pytest
import asyncio
import settings
import logging
import game_manager as Gm
import game_engine as ge
from random import shuffle, randint


logger = logging.getLogger(__name__)

# --- fixtures ---

@pytest.fixture
def gm():
    return Gm.GameManager()

@pytest.fixture
async def game(gm):
    g = gm.create_game("pukachu", 5)
    yield g

    try:
        gm.end_game(g.id)   # cleanup runs after every test automatically
    except Exception as e:
        logger.error("Error: Cannot end the game!"+ str(e))
        pass


# --- helpers ---

def gen_list(size=5):
    flat_list = list(range(1, size * size + 1))
    shuffle(flat_list)
    return [[flat_list[i * size + j] for j in range(size)] for i in range(size)]

def random_cords(length: int = 5):
    return randint(0, length * length + 1)

async def join_and_assert(gm, game, delay=5):
    # await asyncio.sleep(delay)
    assert game.state == ge.GameState.WAITING_TO_JOIN
    gm.join_game(game.id, "pikachut")
    assert game.state == ge.GameState.WAIT_TO_SET_MATRIX

async def assign_matrix_and_assert(gm: Gm.GameManager, game: ge.GameLogic, player: str, delay=5):
    # await asyncio.sleep(delay)
    gm.assign_matrix(game.id, player, gen_list())
    assert game.get_player(player).m.isValid()

async def assert_and_signal_ready(gm: Gm.GameManager, game: ge.GameLogic, player: str, delay=5):
    assert game.state == ge.GameState.READY
    # await asyncio.sleep(delay)
    gm.signal_ready(game.id, player)

async def join_and_set_matrix(gm: Gm.GameManager, game: ge.GameLogic, delay=5):
    await join_and_assert(gm, game)
    await assign_matrix_and_assert(gm, game, "pukachu")
    # await asyncio.sleep(delay)
    await assign_matrix_and_assert(gm, game, "pikachut")
    assert game.state == ge.GameState.READY
# --- tests ---

async def test_join_timer(gm, game):
    await asyncio.sleep(settings.GAME_JOIN_TIMEOUT + 5)
    assert gm.games.get(game.id, None) is None

async def test_join_game(gm, game):
    await join_and_assert(gm, game)

async def test_join_random_game(gm, game):
    # await asyncio.sleep(5)
    assert game.state == ge.GameState.WAITING_TO_JOIN
    gm.join_random_game("pikachut")
    assert game.state == ge.GameState.WAIT_TO_SET_MATRIX

async def test_assign_matrix_timer(gm, game):
    await join_and_assert(gm, game)
    await assign_matrix_and_assert(gm, game, "pukachu")
    await asyncio.sleep(settings.MATRIX_SETTING_TIMEOUT + 5)
    assert game.state == ge.GameState.READY
    assert game.player2.m.isValid()


async def test_assign_matrix(gm, game):
    await join_and_assert(gm, game)
    await assign_matrix_and_assert(gm, game, "pukachu")
    # await asyncio.sleep(5)
    await assign_matrix_and_assert(gm, game, "pikachut")
    assert game.state == ge.GameState.READY

async def test_ready_timer(gm, game):
    await test_assign_matrix(gm, game)
    await asyncio.sleep(settings.START_GAME_TIMEOUT + 5)
    assert game.state == ge.GameState.IN_PROGRESS

async def test_signal_ready(gm, game):
    await test_assign_matrix(gm, game)
    # await asyncio.sleep(5)
    await assert_and_signal_ready(gm,game,"pukachu")
    # await asyncio.sleep(5)
    await assert_and_signal_ready(gm,game,"pikachut")
    assert game.state == ge.GameState.IN_PROGRESS

async def test_move_timer(gm, game):
    await test_signal_ready(gm, game)
    await asyncio.sleep(settings.MOVE_TIMEOUT + 5)
    assert gm.games.get(game.id, None) is None
    # assert that callback notified subscribers

async def test_move(gm, game):
    await test_signal_ready(gm, game)
    # await asyncio.sleep(5)
    state, msg = gm.make_move(game.id, 'pikachut', random_cords())
    assert state == ge.MoveState.INVALID_MOVE
    # await asyncio.sleep(5)
    state, msg = gm.make_move(game.id, 'pukachu', random_cords())
    assert state == ge.MoveState.VALID_MOVE

async def test_game_manager(gm: Gm.GameManager, game: ge.GameLogic):

    await test_move(gm, game)

    move_order = [i for i in range(1, 26)]
    shuffle(move_order)
    p = game.whose_turn()
    state, msg = gm.make_move(game.id, p.name, move_order[0])
    i = 2
    while game.state != ge.GameState.FINISHED:
        # await asyncio.sleep(1)
        p = game.whose_turn()
        state, msg = gm.make_move(game.id, p.name, move_order[i])
        i += 1
    assert (
        state == ge.MoveState.WINNER or 
        state == ge.MoveState.DRAW
        )



