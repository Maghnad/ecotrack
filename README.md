# EcoTrack v2.0 — Carbon Footprint Backend

EcoTrack helps individuals understand, track, and reduce their carbon footprint through simple logging, personalised AI insights, **gamification**, and **weekly community challenges**.

---

## What's New in v2.0

| Feature | Description |
|---|---|
| 🍽️ **Diet Logging** | Track meal carbon footprints (beef → vegan) with relatable comparisons |
| ⚡ **Energy Logging** | Log electricity and natural gas usage with per-source CO₂ breakdown |
| 🌱 **Eco-Actions** | Quick-log positive actions (reusable bags, planted trees) with fun facts |
| 🔥 **Streaks & XP** | Daily streaks, XP per action, 7-level progression (Seedling → EcoChampion) |
| 🏅 **10 Badges** | Unlock achievements for milestones (first log, zero emissions, 100 kg saved…) |
| 🏆 **Leaderboard** | Global XP leaderboard with current-user rank always shown |
| 📅 **Weekly Challenges** | 3 auto-generated challenges per week (same for all users — social!) |
| 📊 **Emissions History** | 30-day daily breakdown by category vs global per-capita average |
| 🤖 **Gemini AI Insights** | Personalised reduction tips from the last 14 days of activity |

---

## Architecture

```
app/
├── main.py                   # FastAPI app assembly & CORS
├── api/
│   ├── footprint.py          # POST /footprint/commute|diet|energy
│   ├── users.py              # GET /users/me, leaderboard
│   └── actions.py            # eco-actions, challenges, insights, history
├── services/
│   ├── calculation_service.py  # All emission factor math (IPCC/DEFRA sources)
│   ├── gamification_service.py # XP, levels, streaks, badge engine
│   ├── challenge_service.py    # Weekly challenge generation & progress
│   ├── analytics_service.py    # History aggregation & leaderboard
│   ├── ai_insight_service.py   # Gemini AI prompt & response handling
│   └── database_service.py     # Firestore abstraction + in-memory mock
├── models/
│   └── schemas.py            # All Pydantic request/response models
└── core/
    ├── config.py             # pydantic-settings configuration
    ├── security.py           # Firebase JWT validation middleware
    └── secrets.py            # Google Secret Manager integration
tests/
└── test_ecotrack.py          # 66 tests across 11 test classes
```

### Design Principles

- **Low coupling:** Every API router calls exactly one service method. Routers never touch Firestore directly.
- **High cohesion:** `calculation_service` does only math. `gamification_service` does only XP/badges. No overlap.
- **Testability:** `database_service` uses an in-memory dict mock when `ENVIRONMENT=testing`. No mocking libraries needed — all 66 tests run with zero live API calls.
- **Readability:** `carbon_emissions_kg`, `primary_transport_mode`, `CalculationService` — every name is self-documenting.

---

## Google Products Used (6+)

| # | Product | Where |
|---|---|---|
| 1 | **Firebase Authentication** | `app/core/security.py` — JWT validation on every route |
| 2 | **Cloud Firestore** | `app/services/database_service.py` — user profiles, logs, challenge progress |
| 3 | **Maps Platform (Distance Matrix)** | `app/services/calculation_service.py` — precise commute distances |
| 4 | **Gemini 1.5 Flash** | `app/services/ai_insight_service.py` — personalised reduction tips |
| 5 | **Cloud Secret Manager** | `app/core/secrets.py` — zero hardcoded credentials |
| 6 | **Cloud Run** *(proposed)* | Containerised deployment target — stateless, auto-scaling |

---

## API Reference

### Footprint Logging
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/footprint/commute` | Log a commute (calls Maps API for distance) |
| `POST` | `/footprint/diet` | Log a meal by protein category |
| `POST` | `/footprint/energy` | Log electricity + gas usage |

### Eco-Actions & Challenges
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/eco-actions` | Log a positive eco-action |
| `GET` | `/challenges` | This week's challenges + your progress |
| `GET` | `/insights` | Gemini AI personalised tips |
| `GET` | `/history?days=30` | Daily emissions breakdown |

### Users & Gamification
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/users/me` | Full profile: XP, level, streak, badges |
| `PATCH` | `/users/me/display-name` | Update leaderboard display name |
| `GET` | `/users/leaderboard` | Global XP leaderboard |
| `GET` | `/health` | Public health check (no auth) |

---

## Gamification Design

### XP & Levels
| Level | Name | XP Required |
|---|---|---|
| 0 | 🌱 Seedling | 0 |
| 1 | 🌿 Sprout | 100 |
| 2 | 🌳 Sapling | 250 |
| 3 | 🏕️ Grove | 500 |
| 4 | 🌲 Forest | 1,000 |
| 5 | 🌴 Rainforest | 2,000 |
| 6 | ⚡ EcoChampion | 5,000 |

**XP per action:** +10 (log), +5 (streak bonus), +50–100 (challenge completion)

### Badges (10 total)
`First Step` · `Week Warrior` · `Consistent Eco-Tracker` · `Habit Forming` · `Seven-Day Streak` · `Eco Obsessed` · `Sapling` · `Rainforest Guardian` · `10 kg Saved` · `Carbon Crusher` · `Zero Emissions Commuter`

### Weekly Challenges (pool of 7, 3 active per week)
Auto-rotated every Monday by ISO week number — identical for all users, enabling social comparison:
- 🚌 Car-Free Commuter · 🌱 Green Week · 🥗 Plant-Based Days
- ♻️ Eco-Action Hero · 📅 Daily Devotion · 🚴 Pedal Power · 💪 Save 5 kg of CO₂

---

## Installation & Setup

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:
```env
PROJECT_ID=your-gcp-project-id
ENVIRONMENT=development
GOOGLE_MAPS_API_KEY=mock_key   # Replace with real key for Maps
GEMINI_API_KEY=mock_key        # Replace with real key for Gemini
```

Run the server:
```bash
uvicorn app.main:app --reload
```

Open Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Testing

```bash
pytest tests/ -v
```

**66 tests across 11 classes** covering:
- Emission calculations (all transport modes, diet types, energy sources, eco-actions)
- All API endpoints (status codes, response shapes, validation)
- Gamification engine (XP accumulation, level thresholds, badge unlocks, streaks)
- Challenge progress calculation and weekly rotation consistency
- Analytics aggregation and leaderboard ranking
- AI insight fallback behaviour

All tests run with **zero live API calls** — the mock environment intercepts all Google service calls.

---

## Emission Factors

| Category | Source | Factor |
|---|---|---|
| Driving | UK DEFRA 2023 | 0.171 kg CO₂/km |
| Transit (bus) | UK average | 0.089 kg CO₂/km |
| Beef | IPCC AR6 | 6.61 kg CO₂e/serving |
| Electricity | UK Grid 2023 | 0.233 kg CO₂/kWh |
| Natural Gas | Standard | 2.04 kg CO₂/m³ |
