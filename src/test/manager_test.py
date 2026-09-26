import pytest
import asyncio
import src.settings as settings
import logging
import src.game_manager as Gm
import src.game_engine as ge
from random import shuffle, randint

DELAY = 0

logger = logging.getLogger(__name__)

# ----------- fixtures ------------------

@pytest.fixture
def gm():
    return Gm.GameManager()

@pytest.fixture
async def game(gm: Gm.GameManager):
    g = gm.create_game("pukachu", 5)
    yield g

    try:
        gm.end_game(g.id)   # cleanup runs after every test automatically
    except Exception as e:
        logger.error("Error: Cannot end the game!"+ str(e))
        pass


@pytest.fixture
async def tm():
    return TestManager()

# --------------- helpers ----------------

def gen_list(size=5):
    flat_list = list(range(1, size * size + 1))
    shuffle(flat_list)
    return [[flat_list[i * size + j] for j in range(size)] for i in range(size)]

def random_cords(length: int = 5):
    return randint(0, length * length + 1)

async def join_and_assert(gm: Gm.GameManager, game: ge.GameLogic):
    await asyncio.sleep(DELAY)
    assert game.state == ge.GameState.WAITING_TO_JOIN
    gm.join_game(game.id, "pikachut")
    assert game.state == ge.GameState.WAIT_TO_SET_MATRIX

async def assign_matrix_and_assert(gm: Gm.GameManager, game: ge.GameLogic, player: str):
    await asyncio.sleep(DELAY)
    gm.assign_matrix(game.id, player, gen_list())
    assert game.get_player(player).m.isValid()

async def assert_and_signal_ready(gm: Gm.GameManager, game: ge.GameLogic, player: str):
    assert game.state == ge.GameState.READY
    await asyncio.sleep(DELAY)
    gm.signal_ready(game.id, player)

async def join_and_set_matrix(gm: Gm.GameManager, game: ge.GameLogic):
    await join_and_assert(gm, game)
    await assign_matrix_and_assert(gm, game, "pukachu")
    await asyncio.sleep(DELAY)
    await assign_matrix_and_assert(gm, game, "pikachut")
    assert game.state == ge.GameState.READY

# ---------------- tests -------------------

class TestTimers:
    
    async def test_join_timer(self, gm: Gm.GameManager, game: ge.GameLogic):
        await asyncio.sleep(settings.GAME_JOIN_TIMEOUT + 5)
        assert gm.games.get(game.id, None) is None

    async def test_assign_matrix_timer(self, gm: Gm.GameManager, game: ge.GameLogic):
        await join_and_assert(gm, game)
        await assign_matrix_and_assert(gm, game, "pukachu")
        await asyncio.sleep(settings.MATRIX_SETTING_TIMEOUT + 5)
        assert game.state == ge.GameState.READY
        assert game.player2.m.isValid()

    async def test_ready_timer(self,tm: ManagerTester, gm: Gm.GameManager, game: ge.GameLogic):
        await tm.test_assign_matrix(gm, game)
        assert game.state == ge.GameState.READY
        await asyncio.sleep(settings.START_GAME_TIMEOUT + 5)
        assert game.state == ge.GameState.IN_PROGRESS

    async def test_move_timer(self, tm: ManagerTester, gm: Gm.GameManager, game: ge.GameLogic):
        await tm.test_signal_ready(gm, game)
        await asyncio.sleep(settings.MOVE_TIMEOUT + 5)
        assert gm.games.get(game.id, None) is None

class TestManager:
    @pytest.mark.parametrize(
        "state",
        [
            ge.GameState.WAIT_TO_SET_MATRIX,
            ge.GameState.READY,
            ge.GameState.IN_PROGRESS,
            ge.GameState.FINISHED,
        ],
    )
    def test_join_game_invalid_state(self,gm: Gm.GameManager, game: ge.GameLogic, state):
        game.state = state

        with pytest.raises(Gm.InvalidGameStateTransitionException):
            gm.join_game(game.id, "pikachut")

        assert game.state == state


    async def test_join_game(self, gm: Gm.GameManager, game: ge.GameLogic):
        await join_and_assert(gm, game)

    async def test_join_random_game(self, gm: Gm.GameManager, game: ge.GameLogic):
        await asyncio.sleep(DELAY)
        assert game.state == ge.GameState.WAITING_TO_JOIN
        gm.join_random_game("pikachut")
        assert game.state == ge.GameState.WAIT_TO_SET_MATRIX

    @pytest.mark.parametrize(
        "state",
        [
            ge.GameState.WAIT_TO_SET_MATRIX,
            ge.GameState.READY,
            ge.GameState.IN_PROGRESS,
            ge.GameState.FINISHED,
        ],
    )
    def test_bad_join_random(self, gm: Gm.GameManager, game: ge.GameLogic, state):
        game.state = state
        with pytest.raises(ValueError):
            gm.join_random_game("pikachut")

        assert game.state == state

    async def test_assign_matrix(self, gm: Gm.GameManager, game: ge.GameLogic):
        await join_and_assert(gm, game)
        assert game.state == ge.GameState.WAIT_TO_SET_MATRIX
        await assign_matrix_and_assert(gm, game, "pukachu")
        assert game.state == ge.GameState.WAIT_TO_SET_MATRIX
        await asyncio.sleep(DELAY)
        await assign_matrix_and_assert(gm, game, "pikachut")
        assert game.state == ge.GameState.READY

    @pytest.mark.parametrize(
        "state",
        [
            ge.GameState.WAITING_TO_JOIN,
            ge.GameState.READY,
            ge.GameState.IN_PROGRESS,
            ge.GameState.FINISHED,
        ],
    )
    async def test_bad_assign_matrix(self, gm: Gm.GameManager, game: ge.GameLogic, state):
        await join_and_assert(gm, game)
        game.state = state
        with pytest.raises(Gm.InvalidGameStateTransitionException):
            gm.assign_matrix(game.id, "pukachu", gen_list())
        assert game.state == state
        
        with pytest.raises(Gm.InvalidGameStateTransitionException):
            gm.assign_matrix(game.id, "pikachut", gen_list())
        assert game.state == state

    async def test_signal_ready(self, gm: Gm.GameManager, game: ge.GameLogic):
        await self.test_assign_matrix(gm, game)
        await asyncio.sleep(DELAY)
        await assert_and_signal_ready(gm,game,"pukachu")
        assert game.state == ge.GameState.READY
        await asyncio.sleep(DELAY)
        await assert_and_signal_ready(gm,game,"pikachut")
        assert game.state == ge.GameState.IN_PROGRESS

    @pytest.mark.parametrize(
        "state",
        [
            ge.GameState.WAITING_TO_JOIN,
            ge.GameState.WAIT_TO_SET_MATRIX,
            ge.GameState.IN_PROGRESS,
            ge.GameState.FINISHED,
        ],
    )
    async def test_bad_ready(self, gm: Gm.GameManager, game: ge.GameLogic, state):
        await self.test_assign_matrix(gm, game)
        game.state = state
        with pytest.raises(Gm.InvalidGameStateTransitionException):
            gm.signal_ready(game.id, "pukachu")
        with pytest.raises(Gm.InvalidGameStateTransitionException):
            gm.signal_ready(game.id, "pikachut")
        assert game.state == state

    async def test_bad_move1(self, gm: Gm.GameManager, game: ge.GameLogic):
        await self.test_signal_ready(gm, game)
        state, msg = gm.make_move(game.id, 'pikachut', random_cords())
        assert state == ge.MoveState.INVALID_MOVE

    @pytest.mark.parametrize(
        "state",
        [
            ge.GameState.WAITING_TO_JOIN,
            ge.GameState.READY,
            ge.GameState.WAIT_TO_SET_MATRIX,
            ge.GameState.FINISHED,
        ],
    )
    async def test_bad_move2(self, gm: Gm.GameManager, game: ge.GameLogic, state):
        await self.test_signal_ready(gm, game)
        game.state = state
        with pytest.raises(Gm.InvalidGameStateTransitionException):
            _, msg = gm.make_move(game.id, 'pukachu', random_cords())
        assert game.state == state

    async def test_move(self, gm: Gm.GameManager, game: ge.GameLogic):
        await self.test_signal_ready(gm, game)
        await asyncio.sleep(DELAY)
        state, msg = gm.make_move(game.id, 'pukachu', random_cords())
        assert state == ge.MoveState.VALID_MOVE

    async def test_game_manager(self, gm: Gm.GameManager, game: ge.GameLogic):
        await self.test_signal_ready(gm, game)
        await asyncio.sleep(DELAY)

        move_order = [i for i in range(1, 26)]
        shuffle(move_order)
        p = game.whose_turn()
        state, msg = gm.make_move(game.id, p.name, move_order[0])
        i = 2
        while game.state != ge.GameState.FINISHED:
            await asyncio.sleep(DELAY)
            p = game.whose_turn()
            state, msg = gm.make_move(game.id, p.name, move_order[i])
            i += 1
        assert (
            state == ge.MoveState.WINNER or 
            state == ge.MoveState.DRAW
            )



