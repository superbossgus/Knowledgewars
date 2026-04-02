"""
E2E Test: 2-Player Countdown Synchronization
Tests the player_ready protocol for synchronized game start.

This test verifies:
1. Player 1 creates a challenge
2. Player 2 receives and accepts the challenge
3. Both players connect to match WebSocket
4. Both send player_ready signals
5. Server broadcasts game_start when 2/2 ready
6. Both clients receive game_start simultaneously
"""
import asyncio
import json
import requests
import websockets
import time
import os

# Use internal URL for testing (from inside container)
# The public URL doesn't work for WebSocket from inside the container
API_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001"

USER1_EMAIL = "test1@knowledgewars.app"
USER2_EMAIL = "test2@knowledgewars.app"
PASSWORD = "test123"

def login(email, password):
    """Login and return token + user_id"""
    r = requests.post(f"{API_URL}/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise Exception(f"Login failed for {email}: {r.text}")
    data = r.json()
    return data["token"], data["user"]["id"]

def check_credits(token):
    """Check user has credits to play"""
    r = requests.get(f"{API_URL}/api/users/credits", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        return 0
    return r.json().get("games_remaining", 0)

async def test_countdown_sync():
    """
    Full E2E test for countdown synchronization.
    Simulates 2 players going through the entire match flow.
    """
    print("=" * 60)
    print("E2E TEST: 2-Player Countdown Synchronization")
    print("=" * 60)
    
    results = {
        "login": False,
        "credits_check": False,
        "notification_ws": False,
        "challenge_created": False,
        "challenge_received": False,
        "challenge_accepted": False,
        "match_ws_connected": False,
        "player_ready_sent": False,
        "game_start_received": {"player1": False, "player2": False},
        "countdown_sync": False
    }
    
    try:
        # Step 1: Login both users
        print("\n[1/8] Logging in both users...")
        token1, user1_id = login(USER1_EMAIL, PASSWORD)
        token2, user2_id = login(USER2_EMAIL, PASSWORD)
        print(f"  ✓ User1: {user1_id[:12]}...")
        print(f"  ✓ User2: {user2_id[:12]}...")
        results["login"] = True
        
        # Step 2: Check credits
        print("\n[2/8] Checking credits...")
        credits1 = check_credits(token1)
        credits2 = check_credits(token2)
        print(f"  User1 credits: {credits1}")
        print(f"  User2 credits: {credits2}")
        if credits1 > 0 and credits2 > 0:
            results["credits_check"] = True
            print("  ✓ Both users have credits")
        else:
            print("  ✗ One or both users have no credits!")
            return results
        
        # Step 3: Connect notification WebSockets
        print("\n[3/8] Connecting notification WebSockets...")
        notify_ws1 = await websockets.connect(f"{WS_URL}/ws/notify/{user1_id}?token={token1}")
        msg1 = json.loads(await notify_ws1.recv())
        assert msg1['type'] == 'connected', f"Expected 'connected', got {msg1['type']}"
        
        notify_ws2 = await websockets.connect(f"{WS_URL}/ws/notify/{user2_id}?token={token2}")
        msg2 = json.loads(await notify_ws2.recv())
        assert msg2['type'] == 'connected', f"Expected 'connected', got {msg2['type']}"
        
        results["notification_ws"] = True
        print("  ✓ Both notification WebSockets connected")
        
        # Step 4: Player 1 creates challenge
        print("\n[4/8] Player 1 creating challenge...")
        r = requests.post(
            f"{API_URL}/api/matches/create",
            json={"opponent_id": user2_id, "topic": "Countdown Sync Test", "language": "es"},
            headers={"Authorization": f"Bearer {token1}"}
        )
        if r.status_code != 200:
            print(f"  ✗ Failed to create match: {r.text}")
            return results
        
        match_data = r.json()
        match_id = match_data["match"]["id"]
        results["challenge_created"] = True
        print(f"  ✓ Match created: {match_id[:12]}...")
        
        # Step 5: Player 2 receives challenge notification
        print("\n[5/8] Waiting for challenge notification...")
        try:
            msg = json.loads(await asyncio.wait_for(notify_ws2.recv(), timeout=10))
            if msg['type'] == 'challenge_received':
                results["challenge_received"] = True
                print(f"  ✓ Challenge received by Player 2")
                print(f"    Topic: {msg['match'].get('topic', 'N/A')}")
            else:
                print(f"  ✗ Unexpected message type: {msg['type']}")
        except asyncio.TimeoutError:
            print("  ✗ Timeout waiting for challenge notification")
            return results
        
        # Step 6: Player 2 accepts challenge
        print("\n[6/8] Player 2 accepting challenge...")
        r = requests.post(
            f"{API_URL}/api/matches/{match_id}/accept",
            headers={"Authorization": f"Bearer {token2}"}
        )
        if r.status_code != 200:
            print(f"  ✗ Failed to accept match: {r.text}")
            return results
        
        results["challenge_accepted"] = True
        print(f"  ✓ Challenge accepted: {r.json().get('message', 'OK')}")
        
        # Drain notification messages (challenge_accepted, match_started)
        for ws in [notify_ws1, notify_ws2]:
            try:
                while True:
                    await asyncio.wait_for(ws.recv(), timeout=1)
            except asyncio.TimeoutError:
                pass
        
        # Step 7: Both connect to match WebSocket
        print("\n[7/8] Connecting to match WebSocket...")
        match_ws1 = await websockets.connect(f"{WS_URL}/ws/match/{match_id}?token={token1}")
        state1 = json.loads(await match_ws1.recv())
        assert state1['type'] == 'match_state', f"Expected match_state, got {state1['type']}"
        print(f"  ✓ Player 1 connected, received match_state")
        
        match_ws2 = await websockets.connect(f"{WS_URL}/ws/match/{match_id}?token={token2}")
        state2 = json.loads(await match_ws2.recv())
        assert state2['type'] == 'match_state', f"Expected match_state, got {state2['type']}"
        print(f"  ✓ Player 2 connected, received match_state")
        
        results["match_ws_connected"] = True
        
        # Step 8: Test player_ready protocol
        print("\n[8/8] Testing player_ready protocol...")
        
        # Test A: Only Player 1 sends ready - should NOT trigger game_start
        print("  [A] Player 1 sends ready (should NOT trigger game_start yet)...")
        await match_ws1.send(json.dumps({"type": "player_ready"}))
        
        try:
            msg = json.loads(await asyncio.wait_for(match_ws1.recv(), timeout=2))
            if msg['type'] == 'game_start':
                print("  ✗ FAIL: game_start sent with only 1 player ready!")
                return results
            else:
                print(f"    Received: {msg['type']} (not game_start, OK)")
        except asyncio.TimeoutError:
            print("    ✓ No game_start with only 1 player ready (correct)")
        
        # Test B: Player 2 sends ready - should trigger game_start for BOTH
        print("  [B] Player 2 sends ready (should trigger game_start for both)...")
        await match_ws2.send(json.dumps({"type": "player_ready"}))
        results["player_ready_sent"] = True
        
        # Wait for game_start on both connections
        game_start_times = {}
        
        async def wait_for_game_start(ws, player_name, user_id):
            try:
                for _ in range(5):
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    if msg['type'] == 'game_start':
                        game_start_times[player_name] = time.time()
                        results["game_start_received"][player_name.lower()] = True
                        print(f"    ✓ {player_name}: game_start received!")
                        return True
            except asyncio.TimeoutError:
                print(f"    ✗ {player_name}: TIMEOUT - no game_start received")
            return False
        
        await asyncio.gather(
            wait_for_game_start(match_ws1, "Player1", user1_id),
            wait_for_game_start(match_ws2, "Player2", user2_id)
        )
        
        # Check synchronization
        if results["game_start_received"]["player1"] and results["game_start_received"]["player2"]:
            time_diff = abs(game_start_times.get("Player1", 0) - game_start_times.get("Player2", 0))
            print(f"\n  Time difference between game_start events: {time_diff*1000:.2f}ms")
            if time_diff < 1.0:  # Within 1 second is considered synchronized
                results["countdown_sync"] = True
                print("  ✓ COUNTDOWN SYNCHRONIZED!")
            else:
                print(f"  ✗ Countdown NOT synchronized (diff > 1s)")
        
        # Cleanup
        for ws in [notify_ws1, notify_ws2, match_ws1, match_ws2]:
            await ws.close()
        
    except Exception as e:
        print(f"\n✗ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        if isinstance(passed, dict):
            for sub_name, sub_passed in passed.items():
                status = "✓ PASS" if sub_passed else "✗ FAIL"
                print(f"  {test_name}.{sub_name}: {status}")
                if not sub_passed:
                    all_passed = False
        else:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name}: {status}")
            if not passed:
                all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Countdown synchronization working!")
    else:
        print("❌ SOME TESTS FAILED - See details above")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_countdown_sync())
    # Exit with appropriate code
    all_passed = all(
        v if not isinstance(v, dict) else all(v.values())
        for v in results.values()
    )
    exit(0 if all_passed else 1)
