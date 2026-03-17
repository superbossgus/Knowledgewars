# Knowledge Wars – Plan (MVP-first, Core-Proven)

## 1) Objectives
- Build a globally scalable trivia PvP app (web PWA first; path to native) with real-time 1v1 duels, multilanguage (es/en/pt), and Stripe-powered monetization (subscription + consumable + coupons).
- Prove hardest core first: LLM question generation (cache+validation), WebSocket real-time duel loop (timers, fairness), and Stripe (subscription + one-time + webhooks).
- Deliver a stunning, modern UI (mobile-first) with shadcn/ui and rock-solid UX.

## 2) Development Phases

### Phase 1: Core POC (Do not proceed until green) ✅ COMPLETED
Hardest parts to validate in isolation:
- OpenAI (gpt-4o-mini via Emergent Universal Key): Generate 10Q sets with 6 options (A–F), 1 correct, hint, explanation_short; strict JSON; cache by (language, topic_normalized, prompt_version); schema validation + light sanity checks.
- Real-time engine (FastAPI WebSockets): room lifecycle, per-question 10s timer (server-authoritative), first-correct +2, incorrect locks player; hint event (-1, private to requester, notify rival), scoreboard sync.
- Stripe: test-mode subscription ($3.99/mo) + one-time (+100 duels); coupons/promo-codes; webhook signature verification; user entitlements state machine.

POC Deliverables
- One Python test script test_core.py that runs all POCs end-to-end (no frontend):
  1) test_openai_generate_validate(langs=[es,en,pt], topics=["General Knowledge"]) → validate schema & uniqueness; persist mock cache to Mongo
  2) test_websocket_duel_loopback() → spin minimal ws room, simulate two clients, run 1–2 questions, assert server decides first-correct + scoreboard
  3) test_stripe_flows() → create products/prices (test), create checkout sessions (sub + one-time), verify webhook handler locally with sample events; assert DB writes
  4) test_elo() → verify ELO delta and league mapping
- Minimal FastAPI endpoints to support tests: /api/health, /api/questions/generate (server-only), /api/stripe/webhook, /ws/match/{roomId}
- Mongo models: users (stub), question_sets, subscriptions, purchases, duel_counters

POC Tooling/Preparation
- Call integration_playbook_expert_v2: OpenAI (text gen) and Stripe (subscriptions + promotion codes + webhooks).
- Quick web_search_tool_v2 scan: best practices for FastAPI WebSockets + timers + scaling.

POC Acceptance Criteria
- 3 languages question set validated + cached; zero schema violations on retry-once logic
- WebSocket loop produces deterministic “first correct” resolution; hint event penalizes correctly
- Stripe: checkout URLs generated (test mode), webhook verified (HMAC), DB updated for both sub and one-time
- ELO function consistent; league assignment deterministic

Phase 1 User Stories
1) Como jugador, quiero que el servidor decida quién respondió primero para que sea justo.
2) Como jugador, quiero pedir una pista y ver penalización inmediata (-1) sólo para mí.
3) Como operador, quiero validar que el JSON de preguntas sea correcto y cacheado para ahorrar costos.
4) Como administrador, quiero recibir eventos Stripe por webhook y ver el estado actualizado.
5) Como ingeniero, quiero un solo script que pruebe LLM, WS y pagos de punta a punta.
6) Como jugador, quiero que el temporizador de 10s avance sincronizado por el servidor.

---

### Phase 2: Main App Development (Full MVP) ✅ COMPLETED
Architecture
- Backend: FastAPI @ 0.0.0.0:8001, MongoDB, all routes prefixed with /api, WebSockets for /ws/match/{roomId}
- Frontend: React (mobile-first), react-router, react-i18next (es/en/pt), shadcn/ui design system
- Caching: Mongo-backed question_sets; reuse by (language, topic_normalized, prompt_version)

Core Backend Features
- Auth: email/password with JWT; minimal admin role; dev-bypass for testing agent
- Users: profile (country_code, display_name, favorite_topic, dnd_enabled), ELO/league, win/loss, premium flags
- Topics: top-10 global, weekly global theme, top-50 suggestions; moderation via OpenAI moderation before generation
- Questions: GET set (cache-first → generate+validate → persist, never mutate correct answers after persist)
- Matchmaking: random global pool (no tiers), DND respected, presence list (online/recent), challenge flow
- WebSockets duel: server-authoritative timestamps, 10s/question, 6 options A–F, first correct +2; incorrect locks; hint (-1) private; per-question and match events persisted in match_events
- Scoring/ELO: update both players; leagues thresholds (Bronce<1000, Plata 1000–1199, Oro 1200–1399, Diamante 1400–1599, Maestro 1600–1799, Gran Maestro ≥1800)
- Limits: duel_counters enforce 100/mo + consumable_extra_100*100; premium unlimited via feature flag
- Leaderboards: global ELO, weekly delta, by-topic, weekly-theme
- Payments (Stripe):
  - Subscription: $3.99/mo; entitlements in subscriptions collection; webhook-driven state
  - One-time +100: 50 MXN (local tiers via Stripe); record in purchases; increment counters
  - Coupons: admin-defined (coupons collection) + Stripe promotion codes; apply to checkout (pref: Stripe promos for sub, custom codes for one-time)
  - Webhooks: invoice.paid, checkout.session.completed, customer.subscription.updated, charge.refunded → update entitlements/counters
- Admin: coupons CRUD, block users, basic stats (duels/month, ARPU, conversion, top topics)
- Notifications: email-based (web alternative) for challenge accepted, duel result, weekly summary (respect DND)
- Analytics: funnels (onboarding, duels, paywall), retention D1/D7/D30, latency averages (ws timestamps)
- Security/Ops: rate limiting (IP/user), content moderation, anti-cheat heuristics (extreme latency/patterns)

Core Frontend Features (PWA)
- Onboarding: signup/login, language auto+manual, country select, favorite topic set
- Home: Play Random, Top 10 topics, Weekly theme, DND toggle, Premium status, duel counter
- Lobby: online/recent players with flags, Random, Challenge flow
- Match: question view (6 options), 10s timer, live scoreboard, Hint button with confirmation (-1), rival hint notifications, latency badge
- Results: winner, score breakdown, ELO delta, rematch CTA
- Rankings: Global/Semanal/Por tema/Weekly Theme
- Profile: league badge, ELO, stats, history
- Paywall: subscription + +100 flow, coupon entry (if applicable), feature-flag premium unlimited toggle visual
- Admin: coupons, moderation queue, stats dashboard
- i18n: translations for es/en/pt; UI language selector persistent

Design & Implementation Steps
- After POC pass → call design_agent with problem statement; apply shadcn/ui, micro-interactions, skeletons, loading states, toasts
- Implement backend endpoints (CRUD + real-time) matching frontend API calls; ensure /api prefix & proper serialization for Mongo (datetime, ObjectId)
- Implement Stripe client flows on FE (checkout redirect) + webhook handling on BE; coupon UX in Paywall
- Validate topic moderation before question generation
- Thorough error states: no questions available, WS reconnect, out-of-duels paywall gating

Phase 2 Testing
- Call testing_agent_v3 (both FE+BE). Provide scenarios:
  - Auth/signup/login, i18n switch
  - Create+reuse question set cache, never expose correct_letter during match
  - Full duel: join, 10s timer, incorrect lock, first-correct +2, hint -1, scoreboard updates
  - Limits: 100/month guard; paywall shown; +100 purchase increments counters (simulate checkout success)
  - Stripe webhook updates subscription state
  - Leaderboards visible; profile stats consistent
  - Admin coupons CRUD; applying valid/expired/overused codes

Phase 2 User Stories
1) Como usuario, quiero jugar Random en 2 toques y ver siempre el marcador.
2) Como usuario, quiero cambiar el idioma de la UI entre ES/EN/PT.
3) Como usuario FREE, quiero ver mi contador de duelos y un paywall claro al agotarlos.
4) Como usuario Premium, quiero acceso a temas especiales y sin límites (flag configurable).
5) Como rival, quiero recibir notificación cuando el otro pide pista.
6) Como jugador, quiero ver ELO y liga en mi perfil y resultados.
7) Como jugador, quiero retar a usuarios con bandera del país visible.
8) Como admin, quiero crear cupones con expiración y máximo de usos.
9) Como usuario, quiero usar un cupón en el checkout.
10) Como jugador, quiero historial de resultados y rematch rápido.

### Phase 3+: Enhancements
- Push: migrate to FCM/APNs for native; PWA push later
- Ads: AdMob (nativo) o AdSense (web) cuando se habilite
- Anti-cheat avanzada, Observabilidad (traces/metrics), PWA install prompts, offline cache for static assets

## 3) Status: ✅ MATCHMAKING BUG FIXED

**Phase 1 POC:** ✅ All core tests passed (OpenAI, WebSocket, Stripe, ELO)
**Phase 2 Main App:** ✅ Full implementation completed
**Phase 2 Testing:** ✅ 100% success rate (20/20 tests passed)
**Deployment Check:** ✅ PASS - Ready for Kubernetes deployment

---

### Phase 8: Matchmaking Bug Fix (Status: COMPLETED ✅)

**Bug Reported:**
- User challenged opponent but credits were deducted before acceptance
- Opponent did not receive challenge notification
- Game was unplayable

**Fixes Implemented:**
- [x] Credits ONLY deducted when match is ACCEPTED (not on creation)
- [x] Fixed route ordering: `/api/matches/pending` now BEFORE `/api/matches/{match_id}`
- [x] Added WebSocket endpoint `/ws/notify/{user_id}` for real-time notifications
- [x] Added WebSocket connection hook in frontend (`useNotificationSocket`)
- [x] Polling backup every 3 seconds for reliability
- [x] Better notification UI with sound effects
- [x] Added favicon.svg with Knowledge Wars branding

**Test Results (100% success):**
- Credits: 20 → 20 on match creation (no deduction)
- Credits: 20 → 19 for BOTH players on match acceptance
- Credits: 19 → 19 on match rejection (no deduction)
- /api/matches/pending: Returns 200 (not 500)

**Test Accounts Created:**
- test1@knowledgewars.app / test123 (TestPlayer1)
- test2@knowledgewars.app / test123 (TestPlayer2)

---

### Phase 4: Brand Identity Implementation (Status: COMPLETED ✅)

**Official Brand Manual Colors Applied:**
- Azul Energía: #0066FF ✅
- Naranja Guerra: #FF6A00 ✅
- Oro Escudo: #F2B705 ✅
- Negro: #0D0D0D ✅
- Blanco: #FFFFFF ✅

**Typography Applied:**
- Principal: Montserrat ExtraBold ✅
- Secundaria: Inter Regular / Medium ✅

**UI Guidelines Implemented:**
- Dark backgrounds with blue-to-orange gradients ✅
- Orange primary buttons ✅
- Gold ranking elements ✅
- Modern competitive gaming aesthetic ✅

**Pages Updated:**
- [x] Login/Register Page - Blue/Orange branding, glow effects
- [x] Home Page - Orange PLAY button, gold accents, progress bar
- [x] Lobby Page - Blue theme with challenge buttons
- [x] Match Page - Timer, scoreboard, answer options with brand colors
- [x] Rankings Page - Gold trophy, blue/orange tabs, ELO in gold
- [x] Premium Page - Gold subscription card, blue duel pack
- [x] Results Page - Victory/defeat styling with brand colors

**Components Updated:**
- [x] EloBadge - League colors with glows
- [x] TimerRing - Blue/orange for warning
- [x] AnswerOption - Blue idle, green correct, red wrong
- [x] ScoreBoard - Blue vs Orange styling

### Phase 5: Push Notifications (FCM/APNs) (Status: Not Started)

**Objective:** Replace unreliable polling with real-time push notifications

**Tasks:**
- [ ] Get integration playbook for FCM
- [ ] Implement backend notification service  
- [ ] Configure Firebase project
- [ ] Implement frontend notification handling
- [ ] Test end-to-end notification flow

---

## Summary of Brand Identity Implementation (March 2026)

### Colors Applied According to Manual:
| Element | Color | Hex Code |
|---------|-------|----------|
| Primary (Blue) | Azul Energía | #0066FF |
| Accent (Orange) | Naranja Guerra | #FF6A00 |
| Gold | Oro Escudo | #F2B705 |
| Background | Negro | #0D0D0D |
| Text | Blanco | #FFFFFF |

### Typography:
- **Headings:** Montserrat ExtraBold
- **Body:** Inter Regular/Medium

### All Pages Redesigned:
1. ✅ Login/Register - Blue/Orange split, glow effects
2. ✅ Home - Orange PLAY button, gold accents
3. ✅ Lobby - Blue matchmaking theme
4. ✅ Match - Blue/Orange scoreboard, timer
5. ✅ Rankings - Gold trophies, blue/orange tabs
6. ✅ Premium - Gold subscription, blue duel pack
7. ✅ Results - Victory/defeat theming

---

## Phase 6: Google OAuth + Remember Me (Status: COMPLETED ✅)

**Implemented:**
- [x] Google OAuth via Emergent Auth integration
- [x] "Continuar con Google" button on login page
- [x] "Recordarme" checkbox for persistent sessions
- [x] Backend endpoint `/api/auth/google/session` for session exchange
- [x] Session cookie management with configurable expiry
- [x] Logout endpoint to clear sessions
- [x] Support for both JWT and cookie-based authentication
- [x] Graceful handling of Google-only accounts (no password)

**Session Duration:**
- Remember Me OFF: 7 days
- Remember Me ON: Indefinite (~100 years)

**Files Modified:**
- `/app/backend/server.py` - Added Google OAuth endpoints and session management
- `/app/frontend/src/pages/LoginPage.jsx` - Added Google button and remember me checkbox

---

## Phase 7: Game Credits & Coupons System (Status: COMPLETED ✅)

**Implemented:**

### Nuevo Modelo de Monetización:
- [x] 50 partidas por $99 MXN
- [x] Contador de partidas por cuenta
- [x] 5 partidas gratis para nuevos usuarios
- [x] Aviso cuando quedan 5 partidas o menos
- [x] Bloqueo cuando se agotan las partidas

### Sistema de Cupones:
- [x] Cupones de partidas gratis (ej: 10 partidas gratis)
- [x] Cupones de descuento porcentual (ej: 20% off)
- [x] Límite de usos por cupón
- [x] Fecha de expiración configurable
- [x] Un solo uso por usuario por cupón

### Recuperación de Contraseña:
- [x] Endpoint `/api/auth/forgot-password` - genera código de 6 dígitos
- [x] Endpoint `/api/auth/verify-reset-code` - verifica el código
- [x] Endpoint `/api/auth/reset-password` - cambia la contraseña
- [x] Expiración de código a 15 minutos
- [x] UI completa de 4 pasos en `/forgot-password`

### Panel de Administrador:
- [x] Login con clave secreta (`/admin`)
- [x] Dashboard con estadísticas (usuarios, partidas, ingresos, cupones)
- [x] CRUD completo de cupones
- [x] Activar/Desactivar cupones
- [x] Ver usos de cada cupón

### Nuevas Páginas:
- [x] `/store` - Tienda de partidas con cupones
- [x] `/forgot-password` - Recuperación de contraseña
- [x] `/admin` - Panel de administrador

### API Endpoints Nuevos:
- `GET /api/users/credits` - Estado de créditos del usuario
- `POST /api/coupons/redeem` - Canjear cupón
- `POST /api/games/purchase` - Iniciar compra
- `POST /api/games/confirm-purchase/{id}` - Confirmar compra
- `POST /api/games/use-credit` - Usar 1 crédito (al jugar)
- `POST /api/admin/coupons/create` - Crear cupón (Admin)
- `GET /api/admin/coupons` - Listar cupones (Admin)
- `PATCH /api/admin/coupons/{code}/toggle` - Activar/Desactivar (Admin)
- `DELETE /api/admin/coupons/{code}` - Eliminar cupón (Admin)
- `GET /api/admin/stats` - Estadísticas (Admin)

### Cupones Creados de Ejemplo:
- `GRATIS10` - 10 partidas gratis
- `DESC20` - 20% de descuento

## 4) Success Criteria
- POC: All core tests pass; valid cached question sets in 3 languages; WS duel loop deterministic; Stripe checkout + webhook updates DB
- MVP: End-to-end flows functional (auth→match→results→leaderboards→paywall→purchase→entitlements), multilanguage UI polished, caches stable, limits enforced
- Quality: No red-screen errors; /api prefix everywhere; proper Mongo serialization; delightful modern UI; testing_agent_v3 passes all critical scenarios
