# EcoTrack v2 - Gamified Carbon Footprint Tracker 🌍

EcoTrack is an interactive, gamified web application designed to help users track, understand, and reduce their carbon footprint. By combining data analytics, an engaging 3D visualizer, and Google Gemini-powered AI insights, EcoTrack turns the fight against climate change into a rewarding daily habit.

---

## 🚀 Features Implemented

### 1. Interactive Dashboard & Gamification
- **XP & Leveling System:** Users earn XP for logging sustainable actions (e.g., using public transit, having a meatless meal), leveling up from "Seedling" to "EcoChampion".
- **Dynamic Challenges:** Weekly rotating challenges (e.g., "Transit Hero", "Plant a Tree") offer bonus XP for completing specific environmental goals.
- **Global Leaderboard:** Users compete globally based on Total XP and Total Carbon Saved, driving community engagement.

### 2. Comprehensive Footprint Tracking
- **Baseline Quiz:** New users take a quiz to establish their initial yearly carbon footprint based on diet, commute, and home energy sources.
- **Emission vs. Savings Logging:** Users can log both *Carbon Savings* (positive eco-actions) and *Carbon Emissions* (daily diet, transport, and energy usage), providing a holistic view of their impact.

### 3. Analytics & 3D Visualizations
- **3D Eco-World:** A living 3D planet built with Three.js that visually reacts to the user's 30-day footprint. 
  - 🟢 **Healthy (< 10kg):** Lush green and full size.
  - 🟠 **Warning (> 10kg):** Turns orange and shrinks slightly.
  - 🔴 **Critical (> 25kg):** Turns red and shrinks drastically, indicating an unsustainable footprint.
- **Emissions Breakdown:** A dynamic Doughnut chart (Chart.js) visualizing the exact distribution of emissions across Diet, Transport, and Energy.
- **Offset & Act Hub:** Offset unavoidable emissions by directly funding verified green projects (Tree planting, Solar) or redeeming XP for discounts at partner eco-brands.

### 4. Google Gemini AI Integration
- **Context-Aware AI Insights:** The app analyzes the user's recent logs to generate highly personalized reduction tips using the Gemini 1.5 Flash API.
- **Conversational EcoBot:** A floating chatbot interface that allows users to ask natural language questions (e.g., "What is the footprint of a beef burger?"). The bot can automatically detect and log emissions directly from the conversation!

---

## 🛡️ Project Standards: Quality, Security & Accessibility

We strictly adhered to core engineering pillars throughout development:

### 🧪 Testing
- **Robust Test Suite:** The backend is covered by over **70 passing Pytest tests** (`tests/test_ecotrack.py`).
- **Scope:** Tests rigorously verify the Gamification math, Carbon calculation logic, API routing, and AI fallback mechanisms.

### 💎 Code Quality & Architecture
- **Backend (Python/FastAPI):** Built with strict type hinting, modular service architecture (separating `analytics_service`, `gamification_service`, etc.), and Pydantic schemas for request/response validation.
- **Frontend (Vanilla JS/HTML/CSS):** Highly performant vanilla Javascript without heavy framework bloat.
- **Accessibility (a11y):** The frontend is fully audited for **WCAG 2.1 AA Compliance**. It includes ARIA roles, semantic HTML, dynamic `aria-live` regions, and complete keyboard navigation support (Space/Enter activation) for all interactive elements and tabs.

### 🔒 Security
- **Content Security Policy (CSP):** Implemented in `main.py` with `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff` to protect against clickjacking and MIME-sniffing. Secure CDNs are whitelisted for Chart.js and Three.js.
- **API Protection:** Backend routes are protected via JWT Bearer Token dependency injection (`get_current_user`), ready for enterprise authentication integration.

---

## 🔮 Future Work & Roadmap

To take this application to a production-ready enterprise level, the following modifications and tool integrations are recommended:

### 1. Authentication & Database Migration
- **Implement Auth0 or Firebase Auth:** Replace the current mock JWT token system with real OAuth2/OIDC providers to handle user signup, login, and secure session management.
- **Migrate to PostgreSQL:** Replace the lightweight JSON file-based database (`database_service.py`) with a robust relational database (PostgreSQL) using an ORM like SQLAlchemy or Prisma for better scaling, indexing, and concurrent writes.

### 2. Advanced Integrations
- **Google Maps API Integration:** Swap the mock distance calculator in `calculation_service.py` with a live Google Maps Distance Matrix API key to calculate real-world commute distances and precise transport emissions based on live traffic and routes.
- **Smart Home API (IoT):** Integrate with smart meter APIs to automatically fetch and log real-time home electricity and gas usage (Energy footprint).

### 3. Progressive Web App (PWA) & Mobile
- **Service Workers:** Implement standard PWA service workers and a `manifest.json` so users can install EcoTrack directly to their mobile home screens.
- **Offline Mode:** Use `IndexedDB` to cache footprint logs when the user is offline, syncing them to the FastAPI backend once a connection is re-established.

### 4. CI/CD & Infrastructure Tools
- **Dockerization:** Create `Dockerfile` and `docker-compose.yml` to containerize the FastAPI backend and frontend for consistent cross-platform deployment.
- **GitHub Actions:** Set up automated CI/CD pipelines to automatically run the Pytest suite, linting (Ruff/Black), and deploy to platforms like Render, Heroku, or AWS Elastic Beanstalk upon merging to the `main` branch.
