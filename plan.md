# Knowledge Wars – Plan (MVP-first, Core-Proven)

## 1) Objectives
- Build a globally scalable trivia PvP app (web PWA first; path to native) with real-time 1v1 duels, multilanguage (es/en/pt), and **Stripe-powered monetization** for buying game credits (50 games / $99 MXN), plus coupons.
- Prove and harden the hardest cores:
  - **WebSocket duel loop fairness**: server-authoritative timer and **simultaneous answering (race-to-correct)**.
  - **Payments**: real Stripe Checkout redirect + confirmation via webhooks (no demo “confirm immediately”).
- Deliver a modern, competitive UI (mobile-first) with shadcn/ui and rock-solid UX.

## 2) Development Phases

### Phase 1: Core POC (Do not proceed until green) ✅ COMPLETED
Hardest parts to validate in isolation:
- OpenAI: Generate 10Q sets with 6 options (A–F), 1 correct, hint, explanation_short; strict JSON; cache by (language, topic_normalized, prompt_version); schema validation + light sanity checks.
- Real-time engine (FastAPI WebSockets): room lifecycle, per-question timer (server-authoritative), **first-correct wins (+2)**, incorrect locks player; hint event (-1, private to requester, notify rival), scoreboard sync.
- Stripe: test-mode subscription + one-time; coupons/promo-codes; webhook signature verification; user entitlements state machine.

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

#### Phase 3.1: Match Logic – Simultaneous Answering (P0) 🔥 IN PROGRESS
**Why:** User corrected the intended gameplay. Current backend comment indicates “turn-based wrong answers”, and the frontend has remnants of “turns” messaging. We must enforce **simultaneous** answering (race-to-correct) for fairness.

**Target rules (authoritative):**
- Both players can answer immediately when a question starts.
- **First correct answer wins** the +2 points for that question.
- If a player answers incorrectly, they are locked out for the rest of that question.
- The other player remains eligible to answer (if they haven’t answered wrong yet).
- If time expires with **no correct answer**, 0 points for both.

**Implementation tasks:**
1. **Backend (server-authoritative):**
   - Update `/ws/match/{match_id}` handlers to explicitly implement the simultaneous model.
   - Maintain per-question state using `match_events` (already present) or a small per-question state doc:
     - Record first `correct_answer` event and ignore later correct attempts.
     - Ensure each user can have at most one `incorrect_answer` per question (lockout) and cannot spam submissions.
   - Add/ensure a per-question “start timestamp” and server-side timeout behavior (preferably server-triggered).
     - If keeping client-sent `time_up`, ensure idempotency (already present) and prevent double-advancing.
2. **Frontend:**
   - Remove “turn-based” language like “Es tu turno” and replace with “Sigue intentando / Tu rival falló, aún puedes responder” where appropriate.
   - Ensure UI lockout is per-player only:
     - On wrong answer: lock only the local player; don’t imply turns.
     - If opponent wrong: keep local enabled if not answered yet.
   - Keep 15s timer UI consistent with server events.
3. **Testing (must-pass):**
   - Two-player E2E test via WebSocket:
     - Both answer concurrently; first correct gets points.
     - Wrong then opponent correct still awards opponent.
     - Time up with no correct → 0 points.
     - Late submissions after correct/time_up are ignored.

**Acceptance criteria:**
- No “turn” mechanics; both start active.
- Server determines winner of question deterministically.
- No double-scoring; no race conditions across clients.

---

#### Phase 3.2: Stripe Integration for Store – Real Payments for 50 Games (P0) 🔥 NOT STARTED
**Why:** `/store` currently uses a demo flow that confirms purchase immediately. Requirement: when user taps “Comprar Ahora”, they must be redirected to Stripe to pay for **50 games ($99 MXN)**.

**Target flow:**
1. User clicks **Comprar Ahora** on `/store`.
2. Backend creates a Stripe Checkout session for the “50 games” product.
3. Frontend redirects to Stripe Checkout URL.
4. Stripe returns to a success URL.
5. Backend webhook marks payment as completed and credits the user with +50 games.
6. Store page refreshes credits from `/api/users/credits`.

**Implementation tasks:**
1. **Design decisions / alignment:**
   - Use Stripe Checkout (hosted) for fastest and safest launch.
   - Use **webhooks** as the source of truth for granting credits.
   - Coupons:
     - If using existing in-app coupons (discount/free games), decide whether to apply as:
       - (A) Stripe promotion codes, or
       - (B) backend-calculated discounts that change the Checkout amount.
2. **Backend:**
   - Add endpoint (or adapt existing) e.g. `POST /api/games/checkout` that:
     - Validates user auth.
     - Creates Stripe Checkout session for 99 MXN.
     - Stores a purchase intent with `status=pending`, `stripe_session_id`, `user_id`, `games_quantity=50`, `final_price`, coupon info.
   - Update webhook handler to:
     - Verify signature.
     - On `checkout.session.completed` (and/or `payment_intent.succeeded`), find purchase by session id and mark `completed`.
     - Increment user’s `games_remaining` by 50.
     - Ensure idempotency (webhook retries).
3. **Frontend (/store):**
   - Replace demo confirm flow (`/api/games/confirm-purchase/{id}` immediate) with redirect to Stripe:
     - Call backend checkout endpoint → receive `checkout_url` → `window.location.href = checkout_url`.
   - Add return pages (if not existing) e.g. `/payment/success` and `/payment/cancel`:
     - Success page polls backend to confirm payment status then navigates back to `/store`.
4. **Testing:**
   - Test in Stripe test mode end-to-end.
   - Verify: user credits increase only after webhook confirms payment.

**Acceptance criteria:**
- Clicking “Comprar Ahora” always redirects to Stripe Checkout.
- Completing payment credits +50 games reliably (webhook-driven).
- No duplicate credit grants on webhook retries.

---

### Phase 4: Enhancements
- Push notifications (FCM/APNs) (Not Started)
- Ads (later)
- Anti-cheat/observability, PWA install prompts, offline caching

## 3) Status
- **Phase 1 POC:** ✅ Completed
- **Phase 2 Main App:** ✅ Completed
- **Matchmaking notification bug fix:** ✅ Completed
- **Brand identity:** ✅ Completed
- **Google OAuth + Remember Me:** ✅ Completed
- **Credits & coupons system:** ✅ Completed (but Store purchase flow still demo)

### Current P0 Work Items (Next)
1. **Fix match logic to simultaneous (race-to-correct)** (Backend + Frontend + tests)
2. **Integrate real Stripe Checkout for 50 games / $99 MXN** and connect to `/store`

## 4) Success Criteria
- Gameplay fairness:
  - Server-authoritative simultaneous answering; first correct wins; wrong locks only that player; timeouts yield 0 points.
- Monetization correctness:
  - Store purchase uses real Stripe Checkout; webhooks grant credits; idempotent and reliable.
- Quality:
  - No red-screen errors; consistent /api prefix; correct Mongo serialization; E2E tests cover race conditions + payment flows.
