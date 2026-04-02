"""
Test WebSocket synchronization with player_ready protocol.
Simulates 2 players connecting, sending ready signals, and verifying game_start.
"""
import asyncio
import json
import requests
import websockets

API_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001"

USER1_EMAIL = "test1@knowledgewars.app"
USER2_EMAIL = "test2@knowledgewars.app"
PASSWORD = "test123"

def login(email, password):
    r = requests.post(f"{API_URL}/api/auth/login", json={"email": email, "password": password})
    data = r.json()
    return data["token"], data["user"]["id"]

async def test_match_sync():
    print("=== WebSocket Sync Test (player_ready protocol) ===\n")
    
    token1, user1_id = login(USER1_EMAIL, PASSWORD)
    token2, user2_id = login(USER2_EMAIL, PASSWORD)
    print(f"Users: {user1_id[:8]}... / {user2_id[:8]}...")
    
    # Connect notification WS
    notify_ws1 = await websockets.connect(f"{WS_URL}/ws/notify/{user1_id}?token={token1}")
    await notify_ws1.recv()  # connected msg
    notify_ws2 = await websockets.connect(f"{WS_URL}/ws/notify/{user2_id}?token={token2}")
    await notify_ws2.recv()  # connected msg
    print("Notification WS connected for both")
    
    # Create match
    r = requests.post(
        f"{API_URL}/api/matches/create",
        json={"opponent_id": user2_id, "topic": "Test Sync v2", "language": "es"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    match_id = r.json()["match"]["id"]
    print(f"Match created: {match_id[:12]}...")
    
    # User2 receives challenge
    msg = json.loads(await asyncio.wait_for(notify_ws2.recv(), timeout=5))
    assert msg['type'] == 'challenge_received'
    print("PASS: Challenge delivered instantly")
    
    # User2 accepts
    r = requests.post(
        f"{API_URL}/api/matches/{match_id}/accept",
        headers={"Authorization": f"Bearer {token2}"}
    )
    print(f"Match accepted: {r.json().get('message','?')}")
    
    # Drain notification messages
    for ws in [notify_ws1, notify_ws2]:
        try:
            while True:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except asyncio.TimeoutError:
            pass
    
    # Both connect to match WS
    print("\n--- Match WebSocket Phase ---")
    match_ws1 = await websockets.connect(f"{WS_URL}/ws/match/{match_id}?token={token1}")
    state1 = json.loads(await match_ws1.recv())
    assert state1['type'] == 'match_state'
    print(f"Player1 connected, got match_state")
    
    match_ws2 = await websockets.connect(f"{WS_URL}/ws/match/{match_id}?token={token2}")
    state2 = json.loads(await match_ws2.recv())
    assert state2['type'] == 'match_state'
    print(f"Player2 connected, got match_state")
    
    # TEST 1: Only Player1 sends ready — no game_start yet
    print("\nTest 1: Only Player1 sends ready...")
    await match_ws1.send(json.dumps({"type": "player_ready"}))
    
    try:
        msg = json.loads(await asyncio.wait_for(match_ws1.recv(), timeout=2))
        if msg['type'] == 'game_start':
            print("FAIL: game_start sent with only 1 ready player!")
            return False
    except asyncio.TimeoutError:
        print("PASS: No game_start with only 1 player ready")
    
    # TEST 2: Player2 sends ready — should trigger game_start for both
    print("\nTest 2: Player2 sends ready (should trigger game_start)...")
    await match_ws2.send(json.dumps({"type": "player_ready"}))
    
    gs = {user1_id: False, user2_id: False}
    
    async def wait_gs(ws, label, uid):
        try:
            for _ in range(5):
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                if msg['type'] == 'game_start':
                    gs[uid] = True
                    print(f"   {label}: game_start received!")
                    return
        except asyncio.TimeoutError:
            print(f"   {label}: TIMEOUT - no game_start")
    
    await asyncio.gather(
        wait_gs(match_ws1, "Player1", user1_id),
        wait_gs(match_ws2, "Player2", user2_id)
    )
    
    print(f"\nPlayer1 game_start: {'PASS' if gs[user1_id] else 'FAIL'}")
    print(f"Player2 game_start: {'PASS' if gs[user2_id] else 'FAIL'}")
    
    # TEST 3: Retry player_ready (simulating the client retry)
    print("\nTest 3: Retry player_ready (should be idempotent)...")
    await match_ws1.send(json.dumps({"type": "player_ready"}))
    # Already started, extra ready signals should still trigger game_start (idempotent)
    try:
        msg = json.loads(await asyncio.wait_for(match_ws1.recv(), timeout=2))
        print(f"   Received after retry: {msg['type']} (OK - idempotent)")
    except asyncio.TimeoutError:
        print("   No extra message (OK - already started)")
    
    all_pass = all(gs.values())
    print(f"\n=== {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'} ===")
    
    for ws in [notify_ws1, notify_ws2, match_ws1, match_ws2]:
        await ws.close()
    
    return all_pass

if __name__ == "__main__":
    result = asyncio.run(test_match_sync())
    exit(0 if result else 1)
