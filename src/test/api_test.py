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
        logger.error("Error: Cannot end the game!"+ str(e))
        pass

# -------- helpers ----------

async def assign_and_signal(client: TestClient, game_id, p_name):
    m = ge.Matrix.create_random_matrix().to_list()
    body = {
        'game_id': game_id,
        'player_name': p_name,
        'data': m
    }
    res = client.post(f'/assign_matrix/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(p_name+res.json().get('message', None))

    while True:
        await asyncio.sleep(1)
        params = {'player_name': p_name}
        res = client.get(f'/{game_id}/has_assigned_matrix', params=params)
        if res.status_code == 200:
            logger.debug("Other Player "+res.json().get('message', None))
            break

    body = {'player_name': p_name}
    res = client.post(f'/start_game/{game_id}', json=body)
    assert res.status_code == 200
    logger.debug(p_name+res.json().get('message', None))

    while True:
        await asyncio.sleep(1)
        res = client.get(f'/{game_id}/has_signalled', params=params)
        if res.status_code == 200:
            logger.debug("Other "+res.json().get('message', None))
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
    state = res.json().get('state', None)
    msg = res.json().get('message', None)
    assert state is not None
    assert msg is not None
    logger.debug(p_name+state+msg)
    return state, msg

async def opp_move(client: TestClient, game_id, p_name):
    state = None
    while True:
        await asyncio.sleep(1)
        params = {'player_name': p_name}
        res = client.get(f'/{game_id}/has_opponent_moved', params=params)
        if res.status_code == 200:
            state = res.json().get('state', None)
            msg = res.json().get('message', None)
            assert state is not None
            logger.debug(p_name+state+msg)
            break  
    return state

def check_state(state):
    if state == ge.MoveState.INVALID_MOVE:
        return 0
    elif state == ge.MoveState.WINNER or state == ge.MoveState.DRAW:
        return -1
    assert state == ge.MoveState.VALID_MOVE
    return 1

# --------- test suit -----------
@pytest.mark.asyncio
async def test_full(client1, client2):
    res1, res2 = await asyncio.gather(
       p1_full_test(client1),
       p2_full_test(client2)
    )

    logger.debug(res1)
    logger.debug(res2)

    # t1.cancel()
    # t2.cancel()
  
async def p2_full_test(client: TestClient): 
    await asyncio.sleep(5)
    p_name = "pikachut"
    res = client.post('/join_random_game', json={'player_name': 'pikachut'})
    game_id = res.json().get('game_id', None)
    logger.debug(p_name+ res.json().get('message', None))

    assert res.status_code == 200
    assert game_id is not None

    await assign_and_signal(client, game_id, 'pikachut')

    msg = None
    while True:
        state = await opp_move(client, game_id, 'pukachu')
        c = check_state(state)
        if c == 0:
            continue
        elif c == -1:
            break
        state , msg = await making_move(client, game_id, "pukachu")
        if c == 0:
            continue
        elif c == -1:
            break

    return msg
  

async def p1_full_test(client: TestClient):
    p_name = 'pukachu'
    body = {'player_name': "pukachu"}
    res =  client.post('/create_game', json=body)
    game_id = res.json().get('game_id', None)
    assert res.status_code == 200
    assert game_id is not None
    logger.debug(p_name+" created game "+game_id)
    
    while True:
        await asyncio.sleep(1)
        res = client.get(f'/{game_id}/has_joined')
        if res.status_code == 200:
            logger.debug(p_name+ res.json().get('message', None))
            break

    await assign_and_signal(client, game_id, 'pukachu')

    msg = None
    while True:
        state , msg = await making_move(client, game_id, "pukachu")

        if state == ge.MoveState.INVALID_MOVE:
            continue
        elif state == ge.MoveState.WINNER or state == ge.MoveState.DRAW:
            break
        assert state == ge.MoveState.VALID_MOVE

        state = await opp_move(client, game_id, 'pukachu')

        if state == ge.MoveState.INVALID_MOVE:
            continue
        elif state == ge.MoveState.WINNER or state == ge.MoveState.DRAW:
            break
        assert state == ge.MoveState.VALID_MOVE

    return msg

        






            
            