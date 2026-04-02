# Knowledge Wars - Product Requirements Document

## Original Problem Statement
Global mobile trivia app "Knowledge Wars" — a real-time 1v1 PvP trivia game with simultaneous gameplay. Both players see the question at the same time; the first to answer correctly wins the points. If one player answers incorrectly, they are locked out, but the other player is NOT notified.

## Core Features
- **Authentication**: Email/password + Google SSO (Emergent-managed)
- **Real-time PvP**: WebSocket-based simultaneous gameplay (chess.com pattern)
- **ELO System**: Starting at 500, +2 win / -1 loss, league tiers (Bronce → Gran Maestro)
- **Matchmaking**: Search by username, filter by rank, custom topics, 15s timer
- **Monetization**: Stripe Checkout ($99 MXN for 50 games), coupon system
- **Admin Panel**: Coupon management, ELO resets, game credit management
- **Sound Effects**: Web Audio API beeps for correct/incorrect answers
- **Surrender**: Players can forfeit mid-match with ELO penalty

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn/UI, Framer Motion, Zustand
- **Backend**: FastAPI, WebSockets (ConnectionManager with separate pools), MongoDB (Motor)
- **Integrations**: OpenAI GPT-4o-mini (Emergent LLM Key), Stripe (Test Mode), Google Auth (Emergent)

## Architecture
```
/app/
├── backend/
│   ├── server.py       # API routes, WebSocket endpoints, Stripe webhook
│   ├── utils.py        # ELOCalculator, Auth utils, QuestionGenerator
│   └── models.py       # Pydantic models
├── frontend/
│   ├── src/
│   │   ├── App.js      # Router, Notification WS, ChallengeNotification popup
│   │   ├── pages/
│   │   │   ├── MatchPage.jsx   # Match gameplay, Timer, Match WS
│   │   │   ├── HomePage.jsx    # Dashboard
│   │   │   ├── LobbyPage.jsx   # Matchmaking
│   │   │   ├── AdminPage.jsx   # Admin panel
│   │   │   └── StorePage.jsx   # Stripe checkout
```

## What's Been Implemented
- [x] Email/password authentication + Google SSO
- [x] Real-time 1v1 PvP with simultaneous answering
- [x] WebSocket sync: separate pools for notifications and match gameplay (chess.com pattern)
- [x] ELO ranking system with league tiers
- [x] Matchmaking (username search, custom topics)
- [x] Stripe Checkout + Webhook for credit purchases
- [x] Admin panel (coupons, ELO resets, credit management)
- [x] Web Audio API sound effects
- [x] Surrender functionality
- [x] Challenge notification popup (dark background, instant delivery)
- [x] **Rematch feature**: After match ends, players can request rematch with same or new topic. Opponent receives golden "REVANCHA" notification and can accept/reject.

## Critical Fix Log (Feb 2026)
- **WebSocket Connection Collision**: Rewrote `ConnectionManager` to use separate `notify_connections` and `match_connections` pools. Previously, connecting to match WS overwrote the notification WS. Now they are independent.
- **Synchronized Start (player_ready protocol)**: Server waits for EXPLICIT `player_ready` signals from both players before broadcasting `game_start`. Client retries every 2s. This replaces the fragile connection-count approach.
- **Challenge Notification Speed**: Now delivered instantly through dedicated notification pool.

## Remaining Backlog
### P0
- [ ] TikTok SSO Implementation

### P2
- [ ] Native In-App Purchases (Apple StoreKit 2, Google Play Billing)
- [ ] Push Notifications (FCM/APNs)

### P3
- [ ] User-Created Topics Moderation
- [ ] Tournaments
- [ ] MongoDB to PostgreSQL Migration

### Refactoring
- [ ] Split server.py (~2400 lines) into modules (routes/, handlers/)
