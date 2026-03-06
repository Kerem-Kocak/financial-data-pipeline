# 📝 How to Put This Project on Your CV

> **Short answer:** Yes, keep it. Using AI tools is a real engineering skill — but you need to understand what was built and be able to talk about it. This guide tells you exactly how.

---

## Should You Keep It or Delete It?

**Keep it.** Here's why:

1. **AI-assisted development is normal now.** Companies like Google, Microsoft, and Meta expect developers to use Copilot, ChatGPT, and similar tools. What matters is that you understand the code and can explain the decisions.

2. **The project is real.** It connects to a live API, stores data in a real database, runs in Docker, and has CI/CD. These are production-level patterns that interviewers care about.

3. **What interviewers test is understanding, not typing.** They won't ask "did you type every character?" — they'll ask "why did you use a stored procedure instead of raw SQL?" If you can answer, the project is valid.

---

## How to Describe It on Your CV

### Option A: Project Section (Recommended)

```
PROJECTS
─────────────────────────────────────────────────────────

Automated Financial Data Pipeline
Python · MySQL · REST API · Docker · Streamlit · GitHub Actions

• Built an ETL pipeline that fetches live cryptocurrency data from the
  Blockchair REST API and stores it in a normalized MySQL database
• Designed a 3NF-compliant schema with stored procedures and BEFORE INSERT
  triggers to auto-calculate price change percentages
• Created an interactive Streamlit dashboard with KPI cards, time-series
  charts, and multi-asset filtering
• Containerized the full stack (Python + MySQL + dashboard) using Docker
  Compose with health checks and persistent volumes
• Implemented CI/CD via GitHub Actions (flake8 linting + pytest unit tests)
  with fully mocked test suites for API and database layers
```

### Option B: Shorter Version (If Space is Limited)

```
Automated Financial Data Pipeline | Python, MySQL, Docker, Streamlit
• ETL pipeline: Blockchair REST API → normalized MySQL (stored procedures,
  triggers) → interactive Streamlit dashboard
• Dockerized full stack with CI/CD (GitHub Actions), 8 unit tests, CSV export
```

### Option C: With Honest AI Mention (Optional — Shows Maturity)

```
Automated Financial Data Pipeline | Python, MySQL, Docker, Streamlit
• Designed and built an ETL pipeline with AI-assisted development, fetching
  live crypto data via REST API into a 3NF MySQL database with triggers
• Independently studied and can explain every architectural decision:
  stored procedures, Docker health checks, mocked unit tests, CI/CD
```

> **Note:** You do NOT have to mention AI assistance — most people don't. But if you're comfortable with it, Option C shows self-awareness and honesty, which interviewers respect.

---

## Skills This Project Proves

Use these as keywords on your CV and LinkedIn:

| Category | Skills |
|----------|--------|
| **Languages** | Python 3 |
| **Databases** | MySQL, SQL, Stored Procedures, Triggers, Normalization (1NF/2NF/3NF) |
| **APIs** | REST APIs, JSON Parsing, HTTP Methods, API Authentication |
| **Data** | ETL Pipelines, Pandas, CSV Export, Time-Series Data |
| **Frontend** | Streamlit, Data Visualization, Interactive Dashboards |
| **DevOps** | Docker, Docker Compose, GitHub Actions, CI/CD |
| **Testing** | pytest, Unit Testing, Mocking, Test Isolation |
| **Tools** | Git, GitHub, Environment Variables, Logging |

---

## What You MUST Know Before an Interview

If this project is on your CV, an interviewer can ask about any part. Here's the minimum you should be able to explain:

### Must-Know (Will Definitely Be Asked)

- [ ] **"Walk me through how the pipeline works."**
  > It fetches live crypto prices from the Blockchair REST API for each tracked asset (Bitcoin, Ethereum), parses the JSON response to extract price, market cap, blocks, and dominance percentage, then inserts each snapshot into MySQL by calling a stored procedure. After all assets are processed, it commits the transaction and exports a CSV report.

- [ ] **"What is a REST API?"**
  > A web service that uses HTTP methods (GET, POST, PUT, DELETE) to access resources at URLs. Our pipeline uses GET requests to `https://api.blockchair.com/{coin}/stats` with an API key as a query parameter. The response comes back as JSON.

- [ ] **"Why MySQL? Why not just a CSV file?"**
  > MySQL gives us relational integrity (foreign keys prevent orphaned records), indexing for fast queries, concurrent access, stored procedures for encapsulating logic, and triggers for automatic calculations. A CSV can't do any of that.

- [ ] **"What does your database schema look like?"**
  > Two tables: `assets` (dimension table with symbol and name) and `market_snapshots` (fact table with price, market cap, blocks, dominance, timestamp). They're linked by `asset_id` as a foreign key. This follows 3NF — asset info isn't repeated in every snapshot row.

- [ ] **"What is Docker and why did you use it?"**
  > Docker packages the app and its dependencies into containers that run identically on any machine. We use Docker Compose to run 3 services (MySQL, pipeline, dashboard) with one command. The `depends_on` with health checks ensures MySQL is ready before the pipeline starts.

### Should-Know (Likely to Be Asked)

- [ ] **"What is a stored procedure?"**
  > Pre-compiled SQL code stored in the database. Our `sp_insert_snapshot` takes 5 parameters and runs an INSERT. Benefits: separation of concerns, security against SQL injection, and reusability.

- [ ] **"What is a database trigger?"**
  > Code that runs automatically on a database event. Our `BEFORE INSERT` trigger on `market_snapshots` calculates `price_change_pct` by comparing the incoming price against the most recent snapshot for the same asset.

- [ ] **"How do your tests work without a real database?"**
  > We use Python's `unittest.mock` to replace real HTTP calls and database connections with controlled fake objects. This means tests run in milliseconds, don't need credentials, and only test our logic — not external services.

- [ ] **"What is CI/CD?"**
  > Continuous Integration automatically runs linting (flake8) and tests (pytest) on every push to `main`. If anything fails, the build fails. This catches bugs before they reach production.

- [ ] **"How does the dashboard work?"**
  > Streamlit is a Python framework that turns scripts into web apps. Our dashboard queries MySQL with a JOIN (snapshots + assets), loads data into a Pandas DataFrame, then renders sidebar filters, KPI metric cards, a price history line chart, and a data table.

### Nice-to-Know (Bonus Points)

- [ ] **"What is database normalization?"**
  > Organizing data to eliminate redundancy. 1NF: atomic values. 2NF: no partial dependencies. 3NF: no transitive dependencies. We separate asset metadata from time-series snapshots.

- [ ] **"What happens if the API is down?"**
  > `fetch_market_data` returns `None`, and `run_pipeline` skips that asset with `continue`. The pipeline doesn't crash — other assets still get processed. There's also a 30-second timeout on requests.

- [ ] **"How would you scale this?"**
  > Add more assets (just insert a DB row + append to the list), schedule with cron or Airflow, add Redis caching for the dashboard, or switch to a time-series database like TimescaleDB for better performance at scale.

---

## Red Flags to Avoid in Interviews

| ❌ Don't Say | ✅ Say Instead |
|---|---|
| "I just followed a tutorial" | "I built a data pipeline that uses REST APIs, MySQL, and Docker" |
| "I don't know what a stored procedure does" | "It encapsulates INSERT logic server-side for clean separation of concerns" |
| "Docker is just a thing I used" | "Docker ensures the same environment runs everywhere — I used Compose for multi-container orchestration with health checks" |
| "The tests just check stuff" | "Tests use mocking to isolate our logic from external dependencies — no real API or DB needed" |
| "I don't really understand triggers" | "The BEFORE INSERT trigger auto-calculates price change percentage by comparing against the latest historical record" |

---

## Quick Study Checklist

Before your interview, make sure you can:

- [ ] Run the pipeline locally and explain what each log line means
- [ ] Draw the data flow diagram from memory (API → pipeline → MySQL → dashboard)
- [ ] Explain why we use a stored procedure instead of raw INSERT statements
- [ ] Explain what the BEFORE INSERT trigger does and why
- [ ] Describe 3NF normalization using the assets/snapshots tables as an example
- [ ] Explain how mocking works in the tests
- [ ] Explain what Docker Compose `depends_on: condition: service_healthy` does
- [ ] Name 3 things you'd add if you had more time (alerting, more assets, scheduling)

---

## Final Advice

> **The project is yours if you understand it.** Spend 1-2 hours reading through `ARCHITECTURE.md` and this guide, then try explaining each component out loud. If you can do that, you'll ace any question about it.
>
> Using AI tools to build software is like using a calculator in math class — the skill is knowing *what* to calculate and *why*, not doing arithmetic by hand.
