"""
This module is for testing fastapi endpoint
"""

import pytest
import asyncio
import logging
from random import randint
# from ..settings import *
from .. import game_manager as Gm
from .. import game_engine as ge
from fastapi.testclient import TestClient
from ..main import app

# if True, use sleep() for mimicking real world network delays.
DELAYS = True

logger = logging.getLogger(__name__)

# ----- fixtures ------

@pytest.fixture
def client1():
    return TestClient(app)

@pytest.fixture
def client2():
    return TestClient(app)

@pytest.fixture
async def game(gm):
    g = gm.create_game("pukachu", 5)
    yield g

    try:
        gm.end_game(g.id)   # cleanup runs after every test automatically
    except Exception as e:
        # logger.error("Error: Cannot end the game!"+ str(e))
        pass

# -------- helpers ----------
async def check_game_state(client, game_id, target_state: ge.GameState):
    res = client.get(f'/{game_id}/status')
    assert res.status_code == 200
    assert res.json()[0]['state'] == str(target_state)
        
async def assign_and_signal(client: TestClient, game_id, p_name):

    await check_game_state(client, game_id, ge.GameState.WAIT_TO_SET_MATRIX)
    
    m = ge.Matrix.create_random_matrix(5).to_list()
    body = {
        'game_id': game_id,
        'player_name': p_name,
        'data': m
    }
    res = client.post(f'/assign_matrix/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(f"{p_name}+{res.json()[0].get('message', None)}")

    while True:
        await asyncio.sleep(1)
        params = {'player_name': p_name}
        res = client.get(f'/{game_id}/has_assigned_matrix', params=params)
        if res.status_code == 200:
            logger.debug(f"Other +{res.json()[0].get('message', None)}")
            break

    await check_game_state(client, game_id, ge.GameState.READY)

    body = {'player_name': p_name}
    res = client.post(f'/start_game/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(f"{p_name}+{res.json()[0].get('message', None)}")

    while True:
        await asyncio.sleep(1)
        res = client.get(f'/{game_id}/has_signalled', params=params)
        if res.status_code == 200:
            logger.debug(f"Other +{res.json()[0].get('message', None)}")
            break
    
async def making_move(client: TestClient, game_id, p_name):

    await asyncio.sleep(1)
    key = randint(1,25)
    body = {
            'game_id': game_id,
            'player_name': p_name,
            'key': key
        }
    res = client.post(f'/move/{game_id}', json=body)
    assert res.status_code == 200
    state = res.json()[0].get('state', None)
    msg = res.json()[0].get('message', None)
    assert state is not None
    assert msg is not None
    logger.debug(f"{p_name}+{state}+{msg}")
    return state, msg

async def opp_move(client: TestClient, game_id, p_name):
    state = None
    while True:
        await asyncio.sleep(1)
        params = {'player_name': p_name}
        res = client.get(f'/{game_id}/has_opponent_moved', params=params)
        if res.status_code == 200:
            state = res.json()[0].get('state', None)
            msg = res.json()[0].get('message', None)
            assert state is not None
            logger.debug(f"{p_name}+{state}+{msg}")
            break  
    return state

def check_state(state):
    if state == str(ge.MoveState.INVALID_MOVE):
        return 0
    elif state == str(ge.MoveState.WINNER) or state == str(ge.MoveState.DRAW):
        return -1
    assert state == str(ge.MoveState.VALID_MOVE)
    return 1

# --------- test suit -----------
@pytest.mark.asyncio
async def test_full(client1, client2):
    p_name = 'pukachu'
    body = {'player_name': p_name}
    res =  client1.post('/create_game', json=body)
    data = res.json()[0]
    game_id = data.get('game_id', None)
    assert res.status_code == 200
    assert game_id is not None

    res1, res2 = await asyncio.gather(
       p1_full_test(client1, game_id),
       p2_full_test(client2, game_id)
    )
    # await check_game_state(client1, game_id, ge.GameState.FINISHED)

    # logger.debug(res1)
    # logger.debug(res2)

    # t1.cancel()
    # t2.cancel()
  
async def p2_full_test(client: TestClient, game_id): 
    await asyncio.sleep(5)
    p_name = "pikachut"
    res = client.post(f'/join_game/{game_id}', json={'player_name': p_name, 'game_id': game_id})
    game_id = res.json()[0].get('game_id', None)
    logger.debug(f"{p_name}+ {res.json().get('message', None)}")

    assert res.status_code == 200
    assert game_id is not None

    await assign_and_signal(client, game_id, p_name)

    msg = None
    while True:
        state = await opp_move(client, game_id, p_name)
        c = check_state(state)
        if c == 0:
            continue
        elif c == -1:
            break
        state , msg = await making_move(client, game_id, p_name)
        c = check_state(state)
        if c == 0:
            continue
        elif c == -1:
            break

    return msg
  

async def p1_full_test(client: TestClient, game_id):
    p_name = 'pukachu'
    
    logger.debug(f"{p_name} created game {game_id}")
    
    while True:
        await asyncio.sleep(1)
        res = client.get(f'/{game_id}/has_joined')
        if res.status_code == 200 and res.json()[0].get('has_joined', None) == 'true':
            logger.debug(f"{p_name} {res.json()[0].get('message', None)}")
            break

    await assign_and_signal(client, game_id, p_name)

    msg = None
    await check_game_state(client, game_id, ge.GameState.IN_PROGRESS)
    while True:
        state , msg = await making_move(client, game_id, p_name)

        if state == str(ge.MoveState.INVALID_MOVE):
            continue
        elif state == str(ge.MoveState.WINNER) or state == str(ge.MoveState.DRAW):
            break
        assert state == str(ge.MoveState.VALID_MOVE)

        state = await opp_move(client, game_id, p_name)

        if state == str(ge.MoveState.INVALID_MOVE):
            continue
        elif state == str(ge.MoveState.WINNER) or state == str(ge.MoveState.DRAW):
            break
        assert state == str(ge.MoveState.VALID_MOVE)

    return msg


# @pytest.mark.asyncio
# async def test_full_1_thread(client1, client2):
    p_name1 = 'pukachu'
    body = {'player_name': p_name1}
    res =  client1.post('/create_game', json=body)
    data = res.json()[0]
    game_id = data.get('game_id', None)
    assert res.status_code == 200
    assert game_id is not None

    p_name2 = "pikachut"
    res = client2.post(f'/join_game/{game_id}', json={'player_name': p_name2, 'game_id': game_id})
    game_id = res.json()[0].get('game_id', None)
    logger.debug(f"{p_name2}+ {res.json()[0].get('message', None)}")
    assert res.status_code == 200
    assert game_id is not None

    m = ge.Matrix.create_random_matrix(5).to_list()
    body = {
        'game_id': game_id,
        'player_name': p_name1,
        'data': m
    }
    res = client1.post(f'/assign_matrix/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(f"{p_name1}+{res.json()[0].get('message', None)}")

    m = ge.Matrix.create_random_matrix(5).to_list()
    body = {
        'game_id': game_id,
        'player_name': p_name2,
        'data': m
    }
    res = client2.post(f'/assign_matrix/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(f"{p_name2}+{res.json()[0].get('message', None)}")

    body = {'player_name': p_name1}
    res = client1.post(f'/start_game/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(f"{p_name1}+{res.json()[0].get('message', None)}")

    body = {'player_name': p_name2}
    res = client2.post(f'/start_game/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(f"{p_name2}+{res.json()[0].get('message', None)}")

    while True:
        await asyncio.sleep(1)
        key = randint(1,25)
        body = {
                'game_id': game_id,
                'player_name': p_name1,
                'key': key
            }
        res = client1.post(f'/move/{game_id}', json=body)
        assert res.status_code == 200
        state = res.json()[0].get('state', None)
        msg = res.json()[0].get('message', None)
        assert state is not None
        assert msg is not None
        logger.debug(f"{p_name1}+{state}+{msg}")
        if state == str(ge.MoveState.INVALID_MOVE):
            continue
        elif state == str(ge.MoveState.WINNER) or state == str(ge.MoveState.DRAW):
            break
        assert state == str(ge.MoveState.VALID_MOVE)
    
        await asyncio.sleep(1)
        key = randint(1,25)
        body = {
                'game_id': game_id,
                'player_name': p_name2,
                'key': key
            }
        res = client2.post(f'/move/{game_id}', json=body)
        assert res.status_code == 200
        state = res.json()[0].get('state', None)
        msg = res.json()[0].get('message', None)
        assert state is not None
        assert msg is not None
        logger.debug(f"{p_name2}+{state}+{msg}")
            
        if state == str(ge.MoveState.INVALID_MOVE):
            making_move(client2,game_id, p_name2)
        elif state == str(ge.MoveState.WINNER) or state == str(ge.MoveState.DRAW):
            break
        assert state == str(ge.MoveState.VALID_MOVE)