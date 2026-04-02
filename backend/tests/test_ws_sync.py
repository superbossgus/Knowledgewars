"""
Test WebSocket synchronization for Knowledge Wars match flow.
Simulates 2 players connecting to a match and verifying the game_start signal.
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
    print("=== Knowledge Wars WebSocket Sync Test ===\n")
    
    # 1. Login both users (sync HTTP)
    print("1. Logging in both users...")
    token1, user1_id = login(USER1_EMAIL, PASSWORD)
    token2, user2_id = login(USER2_EMAIL, PASSWORD)
    print(f"   User1: {user1_id}")
    print(f"   User2: {user2_id}")
    
    # 2. Connect notification WebSockets
    print("\n2. Connecting notification WebSockets...")
    notify_ws1 = await websockets.connect(f"{WS_URL}/ws/notify/{user1_id}?token={token1}")
    msg = json.loads(await notify_ws1.recv())
    print(f"   User1 notify: {msg['type']}")
    
    notify_ws2 = await websockets.connect(f"{WS_URL}/ws/notify/{user2_id}?token={token2}")
    msg = json.loads(await notify_ws2.recv())
    print(f"   User2 notify: {msg['type']}")
    
    # 3. User1 creates a match (sync HTTP)
    print("\n3. User1 creates match (challenges User2)...")
    r = requests.post(
        f"{API_URL}/api/matches/create",
        json={"opponent_id": user2_id, "topic": "Test Sync", "language": "es"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    create_data = r.json()
    if "match" not in create_data:
        print(f"   FAIL: {create_data}")
        await notify_ws1.close()
        await notify_ws2.close()
        return False
    match_id = create_data["match"]["id"]
    print(f"   Match created: {match_id}")
    
    # 4. User2 should receive challenge notification
    print("\n4. Checking challenge notification delivery...")
    try:
        msg = json.loads(await asyncio.wait_for(notify_ws2.recv(), timeout=5))
        print(f"   User2 received: {msg['type']}")
        assert msg['type'] == 'challenge_received', f"Expected challenge_received, got {msg['type']}"
        print("   PASS: Challenge notification delivered instantly!")
    except asyncio.TimeoutError:
        print("   FAIL: No notification within 5 seconds")
        return False
    
    # 5. User2 accepts the match (sync HTTP)
    print("\n5. User2 accepts match...")
    r = requests.post(
        f"{API_URL}/api/matches/{match_id}/accept",
        headers={"Authorization": f"Bearer {token2}"}
    )
    accept_data = r.json()
    print(f"   Accept: {accept_data.get('message','?')}")
    
    # 6. Check User1 gets notifications
    print("\n6. Checking User1 receives notifications...")
    u1_types = []
    try:
        for _ in range(5):
            msg = json.loads(await asyncio.wait_for(notify_ws1.recv(), timeout=3))
            u1_types.append(msg['type'])
            print(f"   User1 got: {msg['type']}")
            if msg['type'] == 'match_started':
                break
    except asyncio.TimeoutError:
        pass
    
    has_match_started_u1 = 'match_started' in u1_types
    print(f"   match_started received: {'PASS' if has_match_started_u1 else 'FAIL'}")
    
    # 7. Check User2 gets match_started
    print("\n7. Checking User2 receives match_started...")
    u2_types = []
    try:
        for _ in range(5):
            msg = json.loads(await asyncio.wait_for(notify_ws2.recv(), timeout=3))
            u2_types.append(msg['type'])
            print(f"   User2 got: {msg['type']}")
            if msg['type'] == 'match_started':
                break
    except asyncio.TimeoutError:
        pass
    
    has_match_started_u2 = 'match_started' in u2_types
    print(f"   match_started received: {'PASS' if has_match_started_u2 else 'FAIL'}")
    
    # 8. Both connect to match WebSocket
    print("\n8. Both players connecting to match WebSocket...")
    match_ws1 = await websockets.connect(f"{WS_URL}/ws/match/{match_id}?token={token1}")
    state1 = json.loads(await match_ws1.recv())
    print(f"   User1 got: {state1['type']}")
    
    match_ws2 = await websockets.connect(f"{WS_URL}/ws/match/{match_id}?token={token2}")
    state2 = json.loads(await match_ws2.recv())
    print(f"   User2 got: {state2['type']}")
    
    # 9. CRITICAL: Both should receive game_start
    print("\n9. CRITICAL: Waiting for synchronized game_start...")
    gs = {user1_id: False, user2_id: False}
    
    async def wait_gs(ws, label, uid):
        try:
            for _ in range(5):
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                print(f"   {label}: {msg['type']}")
                if msg['type'] == 'game_start':
                    gs[uid] = True
                    return
        except asyncio.TimeoutError:
            pass
    
    await asyncio.gather(
        wait_gs(match_ws1, "User1", user1_id),
        wait_gs(match_ws2, "User2", user2_id)
    )
    
    print(f"\n   User1 game_start: {'PASS' if gs[user1_id] else 'FAIL'}")
    print(f"   User2 game_start: {'PASS' if gs[user2_id] else 'FAIL'}")
    
    all_pass = all(gs.values()) and has_match_started_u1 and has_match_started_u2
    
    if all_pass:
        print("\n=== ALL TESTS PASSED ===")
    else:
        print("\n=== SOME TESTS FAILED ===")
    
    # Cleanup
    for ws in [notify_ws1, notify_ws2, match_ws1, match_ws2]:
        await ws.close()
    
    return all_pass

if __name__ == "__main__":
    result = asyncio.run(test_match_sync())
    exit(0 if result else 1)
