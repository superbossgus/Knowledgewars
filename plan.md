# Knowledge Wars – Plan (MVP-first, Core-Proven)

## 1) Objectives
- Build a globally scalable trivia PvP app (web PWA first; path to native) with real-time 1v1 duels, multilanguage (es/en/pt), and **Stripe-powered monetization** for buying game credits (**50 games / $99 MXN**), plus coupons.
- Prove and harden the hardest cores:
  - **WebSocket duel loop fairness**: server-authoritative resolution and **simultaneous answering (race-to-correct)**.
  - **Payments**: real **Stripe Checkout redirect** + **confirmation via webhooks** + **client-side polling** after return from Stripe (no demo “confirm immediately”).
- Deliver a modern, competitive UI (mobile-first) with shadcn/ui and rock-solid UX.

## 2) Development Phases

### Phase 1: Core POC (Do not proceed until green) ✅ COMPLETED
Hardest parts validated in isolation:
- OpenAI: Generate 10Q sets with 6 options (A–F), 1 correct, hint, explanation_short; strict JSON; cache by (language, topic_normalized, prompt_version); schema validation + sanity checks.
- Real-time engine (FastAPI WebSockets): room lifecycle, per-question timer, **first-correct wins (+2)**, incorrect locks player; hint event (-1), scoreboard sync.
- Stripe: test-mode checkout creation + webhook signature verification; transaction persistence.

POC Deliverables ✅
- test_core.py: LLM schema/cache, WS duel loopback, Stripe flows, ELO.

POC Acceptance Criteria ✅
- Deterministic “first correct” resolution; hint penalty works; webhook verified.

---

### Phase 2: Main App Development (Full MVP) ✅ COMPLETED
Architecture ✅
- Backend: FastAPI @ 0.0.0.0:8001, MongoDB, all routes prefixed with /api, WebSockets for /ws/match/{matchId}
- Frontend: React (mobile-first), react-router, shadcn/ui

Core features delivered ✅
- Auth (incl. Google OAuth + Remember Me)
- Matchmaking & notifications
- Match UI (timer, answers, hint flow)
- ELO/rankings/profile
- Credits & coupon system
- Admin panel

---

### Phase 3: Hardening / Production Fixes (Current Focus)

#### Phase 3.1: Match Logic – Simultaneous Answering (P0) ✅ COMPLETED
**Why:** Gameplay requirement clarified: **both players start at the same time**, no turns.

**Authoritative rules implemented:**
- Both players can answer immediately when a question starts.
- **First correct answer wins** the +2 points for that question.
- If a player answers incorrectly, they are locked out for the rest of that question.
- The other player remains eligible to answer (if they haven’t answered wrong yet).
- If time expires with **no correct answer**, 0 points for both.

**Implementation (done):**
1. **Backend (server-authoritative):**
   - Updated `/ws/match/{match_id}` gameplay handler `handle_answer_submission()`:
     - Records only the first `correct_answer` event per question.
     - Locks out only the user who answered incorrectly.
     - Prevents answer spamming by rejecting repeated submissions per user/question.
   - `handle_time_up()` keeps 0 points if no correct answer.
2. **Frontend:**
   - Updated Match UI to remove turn-based messaging.
   - Lockout is per-player (local `isLocked` state), not “turn passing”.
3. **Testing:**
   - Verified by testing agent: **100% of simultaneous-logic requirements**.

**Acceptance criteria:** ✅ Met
- No “turn” mechanics.
- Deterministic first-correct resolution.
- No double-scoring; spam prevention in place.

---

#### Phase 3.2: Stripe Integration for Store – Real Payments for 50 Games (P0) ✅ COMPLETED
**Why:** `/store` previously used a demo flow. Requirement: “Comprar Ahora” must redirect to Stripe to pay for **50 games ($99 MXN)**.

**Target flow implemented:**
1. User clicks **Comprar Ahora** on `/store`.
2. Backend creates a Stripe Checkout session (amount defined server-side).
3. Frontend redirects to Stripe Checkout URL.
4. Stripe returns to a success URL with `session_id`.
5. Backend webhook marks payment as completed and credits the user with +50 games.
6. Success page polls backend for payment status and then refreshes user credits.

**Implementation (done):**
1. **Backend:**
   - `POST /api/games/purchase` now creates a real Stripe Checkout session for **MXN 99.00** (discounts applied server-side), stores purchase + transaction records.
   - `POST /api/webhook/stripe` updated to grant credits for the `50_games` product with **idempotency** (updates purchase from `pending`→`completed` before incrementing credits).
   - `GET /api/payments/checkout/status/{session_id}` added for post-return polling and “finalization” safety.
   - Legacy `POST /api/games/confirm-purchase/{id}` is now deprecated (returns error).
2. **Frontend:**
   - `/store` updated to redirect to `checkout_url` returned by backend.
   - Added `/payment-success` page with polling UI and automatic redirect.
   - Router updated to include `/payment-success` protected route.
3. **Testing:**
   - Verified by testing agent: **100% integration pass**.

**Acceptance criteria:** ✅ Met
- Clicking “Comprar Ahora” redirects to Stripe Checkout.
- Completing payment credits +50 games (webhook-driven).
- No duplicate credits from webhook retries or polling.

---

### Phase 4: Enhancements (Next)
- **Server-authoritative timer** (optional hardening): move from client-sent `time_up` to server-driven per-question timeout to remove any reliance on the client.
- Push notifications (FCM/APNs) (Not Started)
- Ads (later)
- Anti-cheat/observability, PWA install prompts, offline caching

## 3) Status
- **Phase 1 POC:** ✅ Completed
- **Phase 2 Main App:** ✅ Completed
- **Matchmaking notification bug fix:** ✅ Completed
- **Brand identity:** ✅ Completed
- **Google OAuth + Remember Me:** ✅ Completed
- **Credits & coupons system:** ✅ Completed
- **Phase 3.1 Simultaneous match logic:** ✅ Completed (tested)
- **Phase 3.2 Stripe Checkout for 50 games:** ✅ Completed (tested)

### Current P0 Work Items (Next)
1. **Production hardening of timers** (server-authoritative timeouts, reduce client dependence) – optional but recommended.
2. **Operational readiness**:
   - Ensure Stripe webhook endpoint is reachable in production and configured in Stripe Dashboard.
   - Add monitoring/logging for failed webhooks and payment reconciliation.

## 4) Success Criteria
- Gameplay fairness:
  - Server-authoritative simultaneous answering; first correct wins; wrong locks only that player; timeouts yield 0 points.
- Monetization correctness:
  - Store purchase uses real Stripe Checkout; webhooks grant credits; idempotent and reliable.
  - Post-return polling confirms status and updates UI reliably.
- Quality:
  - No red-screen errors; consistent /api prefix; correct Mongo serialization.
  - E2E tests cover race conditions + payment flows.
