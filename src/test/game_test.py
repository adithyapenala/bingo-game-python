"""
This module is for end-2-end testing of game logic
"""
import json
import time
import threading
from flask.testing import FlaskClient


# def test_create_game(client: FlaskClient, player_name: str) -> int:

#     res = client.post('/create_game', json={'playerName': player_name})
#     assert res.status_code == 200

#     data = res.get_json()
#     assert data is not None
#     assert data['success'] == True
#     assert isinstance(data['gameId'], int)
#     assert data['playerName'] == player_name
#     return data['gameId']

# def test_join_game(
#         client: FlaskClient, 
#         player_name: str, 
#         game_id: int
#         ) -> str:
#     res = client.post(f'/join_game/{game_id}', json={
#         'playerName': player_name,
#         'gameId' : game_id
#     })
#     assert res.status_code == 200

#     data = res.get_json()
#     assert data is not None
#     assert isinstance(data['gameId'], int)
#     assert game_id == data['gameId']
#     assert data['playerName'] == player_name
#     assert data['opponentName'] is not None

#     return data['opponentName']

# def test_get_game_opponent(client: FlaskClient, 
#         player_name: str, 
#         game_id: int
#         ) -> str: 
#     res = client.get(
#         f'/join_game/{game_id}?playerName={player_name}'
#     )
#     assert res.status_code == 200

#     data = res.get_json()

#     assert data is not None
#     assert data['opponentName'] is not None

#     return data['opponentName']

# def test_wait_for_player2(client: FlaskClient):


#     game_id = test_create_game(client, "pukachu")

#     # trigger join after a short delay, from a separate thread
#     def join_late():
#         time.sleep(0.1)
#         test_join_game(client, "psyfuck", game_id)

#     t = threading.Thread(target=join_late)
#     t.start()

#     # consume the SSE stream
#     with client.get(
#         f'/game/{game_id}/wait',
#         headers={'Accept': 'text/event-stream'},
#     ) as res:
#         assert res.status_code == 200
#         assert res.mimetype == 'text/event-stream'

#         for line in res.iter_lines():
#             if line and line.startswith(b'data:'):
#                 data = json.loads(line[len(b'data:'):].strip())
#                 assert data['event'] == 'player2_joined'
#                 assert data['player2name'] == 'psyfuck'
#                 break  # ✅ got the event, stop consuming

#     t.join()

# def test_full_test(client: FlaskClient):
#     player1 = "adit"
#     player2 = "Rai_p"

#     game_id = test_create_game(client, player1)
#     opponent_name = test_join_game(client,player2,game_id)

#     assert opponent_name == player1

#     player1_oppoenent = test_get_game_opponent(client, player1, game_id)

#     assert player1_oppoenent == player2



