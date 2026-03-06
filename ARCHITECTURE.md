# 🏗 Architecture & Complete Project Guide

> **Purpose:** This document explains every part of the Financial Data Pipeline project — backend, frontend, API, database, DevOps, and testing — so you can fully understand and confidently discuss it in interviews.

---

## Table of Contents

1. [What This Project Does (The Big Picture)](#1-what-this-project-does-the-big-picture)
2. [How Data Flows Through the System](#2-how-data-flows-through-the-system)
3. [Backend Deep-Dive](#3-backend-deep-dive)
4. [Frontend Deep-Dive (Streamlit Dashboard)](#4-frontend-deep-dive-streamlit-dashboard)
5. [API Integration (Blockchair REST API)](#5-api-integration-blockchair-rest-api)
6. [Database Design (MySQL)](#6-database-design-mysql)
7. [DevOps & Deployment](#7-devops--deployment)
8. [Testing Strategy](#8-testing-strategy)
9. [Project File Map](#9-project-file-map)
10. [Interview Questions & Answers](#10-interview-questions--answers)

---

## 1. What This Project Does (The Big Picture)

This is an **automated financial data pipeline** that:

1. **Fetches** live cryptocurrency prices (Bitcoin, Ethereum) from the Blockchair REST API
2. **Stores** the data in a normalized MySQL database using stored procedures and triggers
3. **Exports** the data to CSV reports
4. **Visualizes** everything in a real-time Streamlit web dashboard
5. **Runs in Docker** with one command (`docker-compose up`)
6. **Tests automatically** via GitHub Actions CI/CD on every push

### Why It Matters

This project demonstrates a **complete production-grade data engineering workflow**: ingestion → storage → transformation → visualization — the same pattern used at companies like Netflix, Uber, and Stripe for their data pipelines.

---

## 2. How Data Flows Through the System

```
┌──────────────────────────────────────────────────────────────────┐
│                       DATA FLOW DIAGRAM                          │
└──────────────────────────────────────────────────────────────────┘

Step 1: FETCH DATA                    Step 2: STORE IN DATABASE
┌──────────────┐   HTTP GET    ┌──────────────┐  SQL CALL   ┌─────────┐
│  Blockchair   │ ◄──────────  │  pipeline.py  │ ──────────► │  MySQL   │
│  REST API     │  JSON reply  │  (Python)     │  Stored     │  DB      │
└──────────────┘               └──────────────┘  Procedure   └─────────┘
                                      │                          │
                                      │                    TRIGGER fires:
                                      │                    calculates
                                      │                    price_change_pct
                                      ▼
Step 3: EXPORT                  Step 4: VISUALIZE
┌──────────────┐               ┌──────────────────┐
│  CSV File     │               │  Streamlit        │
│  (report)     │               │  Dashboard        │
└──────────────┘               │  (localhost:8501)  │
                                └──────────────────┘
```

### Detailed Step-by-Step

| Step | What Happens | File | How |
|------|-------------|------|-----|
| 1 | Load API key and DB credentials from `.env` | `pipeline.py` | `python-dotenv` reads `.env` |
| 2 | Loop through each asset (BTC, ETH) | `pipeline.py` | `for asset in ASSETS` |
| 3 | Call Blockchair API for live prices | `pipeline.py` | `requests.get()` with API key |
| 4 | Parse JSON response, extract 4 metrics | `pipeline.py` | `response.json()['data']` |
| 5 | Insert into MySQL via stored procedure | `pipeline.py` | `cursor.callproc('sp_insert_snapshot', ...)` |
| 6 | MySQL trigger auto-calculates price change % | `database/setup.sql` | `BEFORE INSERT` trigger |
| 7 | Commit the transaction | `pipeline.py` | `connection.commit()` |
| 8 | Export all data to CSV | `export_report.py` | `SELECT ... JOIN` → `csv.writer` |
| 9 | Dashboard queries DB and renders charts | `dashboard.py` | `pd.read_sql()` → Streamlit widgets |

---

## 3. Backend Deep-Dive

The backend consists of 4 Python files, each with a single responsibility:

### 3.1 `pipeline.py` — The Main Orchestrator

**What it does:** Fetches live crypto data from the API and stores it in MySQL.

**Key components:**

```python
# Configuration (lines 13-29)
load_dotenv()                          # Loads .env file into environment
API_KEY = os.getenv('BLOCKCHAIR_API_KEY')  # API credentials
DB_HOST = os.getenv('DB_HOST')         # Database connection details

ASSETS = [                             # Coins to track
    {'coin': 'bitcoin',  'asset_id': 1},
    {'coin': 'ethereum', 'asset_id': 2},
]
```

**Three core functions:**

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `fetch_market_data(coin)` | Calls Blockchair API for one coin | `"bitcoin"` | `dict` with price, market_cap, blocks, dominance — or `None` on failure |
| `store_snapshot(cursor, asset_id, data)` | Calls MySQL stored procedure | cursor + asset_id + market data dict | Inserts row into `market_snapshots` |
| `run_pipeline()` | Orchestrates the full flow | Nothing | Fetches all assets, stores them, commits |

**How `fetch_market_data` works:**

```python
def fetch_market_data(coin: str) -> dict | None:
    # 1. Build the URL: https://api.blockchair.com/bitcoin/stats
    url = f"{BASE_URL}/{coin}/stats"

    # 2. Make HTTP GET request with API key and 30-second timeout
    response = requests.get(url, params={'key': API_KEY}, timeout=30)

    # 3. Check for errors
    if response.status_code != 200:
        return None  # API returned an error

    # 4. Parse the JSON response
    data = response.json().get('data')
    if not data:
        return None  # Empty response

    # 5. Extract only the 4 metrics we need
    return {
        'price':      data['market_price_usd'],
        'market_cap': data['market_cap_usd'],
        'blocks':     data['blocks'],
        'dominance':  data['market_dominance_percentage'],
    }
```

**How `run_pipeline` works:**

```python
def run_pipeline():
    connection = mysql.connector.connect(...)  # Open DB connection
    cursor = connection.cursor()

    for asset in ASSETS:                       # Loop: BTC, ETH
        market_data = fetch_market_data(asset['coin'])  # Call API
        if market_data is None:
            continue                           # Skip failed fetches

        store_snapshot(cursor, asset['asset_id'], market_data)  # Insert

    connection.commit()     # Save all changes at once (transaction)
    cursor.close()
    connection.close()
```

**Key design decisions:**
- **Transaction pattern**: All inserts happen, then one `commit()`. If anything fails, nothing is saved (atomicity).
- **Graceful error handling**: Failed API calls return `None` and are skipped — they don't crash the whole pipeline.
- **Separation of concerns**: Fetching, storing, and orchestrating are separate functions.

---

### 3.2 `export_report.py` — CSV Export

**What it does:** Queries the database and exports all market snapshots to a CSV file.

```python
def export_to_csv(filename='market_report.csv'):
    # 1. Connect to MySQL
    # 2. Run a JOIN query: market_snapshots + assets
    # 3. Write headers + rows to CSV file
    # 4. Close connection
```

**The SQL query it runs:**
```sql
SELECT
    a.name            AS 'Asset',
    s.price_usd       AS 'Price (USD)',
    s.price_change_pct AS 'Change (%)',
    s.market_cap_usd  AS 'Market Cap',
    s.dominance_pct   AS 'Dominance (%)',
    s.snapshot_time    AS 'Timestamp'
FROM market_snapshots s
JOIN assets a ON s.asset_id = a.asset_id
ORDER BY s.snapshot_time DESC;
```

**Why this matters:** The `JOIN` is important — it combines the time-series data (snapshots) with the static asset names. This is a core SQL concept called a **foreign key relationship**.

---

### 3.3 `crypto_stats.py` — Quick Stats Viewer

**What it does:** A standalone CLI tool that fetches and logs Bitcoin stats without touching the database. Good for quick checks.

**When to use it:** When you just want to see current prices without running the full pipeline.

---

### 3.4 `logger.py` — Centralized Logging

**What it does:** Provides a **factory function** that creates configured loggers for any module.

```python
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:          # Prevent duplicate handlers
        logger.setLevel(logging.DEBUG)

        # Console: shows INFO and above (user-facing)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)

        # File: saves DEBUG and above (full audit trail)
        file_handler = logging.FileHandler('logs/pipeline.log')
        file_handler.setLevel(logging.DEBUG)

    return logger
```

**Two output levels:**
| Handler | Level | Purpose |
|---------|-------|---------|
| Console | INFO+ | User sees important messages |
| File (`logs/pipeline.log`) | DEBUG+ | Full audit trail for debugging |

**Log format:** `2026-03-04 12:00:00 | pipeline          | INFO     | Fetching data for BITCOIN ...`

**Design pattern:** This is the **Factory Pattern** — a single function creates and configures objects (loggers) consistently across the whole project.

---

## 4. Frontend Deep-Dive (Streamlit Dashboard)

### What is Streamlit?

Streamlit is a Python library that turns Python scripts into web apps. You write Python code, and Streamlit automatically renders it as a web page with interactive widgets. **No HTML/CSS/JavaScript needed.**

### File: `dashboard.py`

The dashboard has 5 sections:

#### Section 1: Data Loading

```python
def load_data() -> pd.DataFrame:
    connection = mysql.connector.connect(...)
    query = """
        SELECT a.symbol AS Symbol, a.name AS Asset,
               s.price_usd AS Price, s.price_change_pct AS 'Change (%)',
               ...
        FROM market_snapshots s
        JOIN assets a ON s.asset_id = a.asset_id
        ORDER BY s.snapshot_time DESC;
    """
    df = pd.read_sql(query, connection)  # SQL → Pandas DataFrame
    connection.close()
    return df
```

**Key concept:** `pd.read_sql()` converts a SQL query result directly into a Pandas DataFrame — the standard data structure for data analysis in Python.

#### Section 2: Page Configuration

```python
st.set_page_config(
    page_title="Crypto Pipeline Dashboard",
    page_icon="📊",
    layout="wide",      # Uses full browser width
)
st.title("📊 Crypto Market Dashboard")
```

#### Section 3: Sidebar Filters

```python
assets = df["Asset"].unique().tolist()       # ['Bitcoin', 'Ethereum']
selected = st.sidebar.multiselect(           # Dropdown filter
    "Filter by asset", assets, default=assets
)
filtered = df[df["Asset"].isin(selected)]    # Filter DataFrame
```

**How it works:** The user can select/deselect assets in the sidebar. The DataFrame is filtered accordingly, and all charts/tables update automatically.

#### Section 4: KPI Metric Cards

```python
latest = filtered.drop_duplicates(subset="Asset", keep="first")  # Latest per asset
cols = st.columns(len(latest))  # Dynamic column layout

for col, (_, row) in zip(cols, latest.iterrows()):
    col.metric(
        label=f"{row['Asset']} ({row['Symbol']})",  # "Bitcoin (BTC)"
        value=f"${row['Price']:,.2f}",                # "$87,432.15"
        delta=f"{row['Change (%)']:.2f}%",            # "+2.50%"
    )
```

**What `st.metric` does:** Shows a big number with an optional green/red delta indicator — exactly like a stock ticker.

#### Section 5: Price History Chart

```python
chart_data = filtered.pivot_table(
    index="Timestamp", columns="Asset", values="Price"
).sort_index()
st.line_chart(chart_data)
```

**What `pivot_table` does:** Reshapes the data so each asset becomes its own column, with timestamps as rows. This is required for multi-line charts.

**Before pivot:**
| Timestamp | Asset | Price |
|-----------|-------|-------|
| 12:00 | Bitcoin | 87432 |
| 12:00 | Ethereum | 3215 |

**After pivot:**
| Timestamp | Bitcoin | Ethereum |
|-----------|---------|----------|
| 12:00 | 87432 | 3215 |

#### Section 6: Raw Data Table + Footer

```python
st.dataframe(filtered, use_container_width=True, hide_index=True)
st.caption(f"Total records: {len(filtered)} | Assets tracked: {len(assets)}")
```

---

## 5. API Integration (Blockchair REST API)

### What is a REST API?

A REST API is a web service that lets you send HTTP requests (like a browser does) and get structured data back (usually JSON). REST stands for **Representational State Transfer**.

### The Blockchair API

| Property | Value |
|----------|-------|
| **Provider** | Blockchair (blockchain data aggregator) |
| **Base URL** | `https://api.blockchair.com` |
| **Endpoint Used** | `GET /{coin}/stats` |
| **Authentication** | API key passed as query parameter |
| **Response Format** | JSON |

### Example Request

```
GET https://api.blockchair.com/bitcoin/stats?key=YOUR_API_KEY
```

### Example Response (simplified)

```json
{
  "data": {
    "market_price_usd": 87432.15,
    "market_cap_usd": 1720000000000,
    "blocks": 890123,
    "market_dominance_percentage": 61.34,
    "transactions": 1050000000,
    "difficulty": 110568060256992,
    ...
  }
}
```

### What We Extract

| JSON Field | Our Variable | What It Means |
|-----------|-------------|---------------|
| `market_price_usd` | `price` | Current price in USD |
| `market_cap_usd` | `market_cap` | Total value of all coins (price × supply) |
| `blocks` | `blocks` | Total blocks mined on the blockchain |
| `market_dominance_percentage` | `dominance` | This coin's share of total crypto market |

### How Authentication Works

```python
# API key stored in .env file (never in code)
API_KEY = os.getenv('BLOCKCHAIR_API_KEY')

# Passed as query parameter in the URL
response = requests.get(url, params={'key': API_KEY}, timeout=30)
# Results in: https://api.blockchair.com/bitcoin/stats?key=abc123
```

### Error Handling

```python
# Check HTTP status code
if response.status_code != 200:    # 200 = success
    return None                     # Graceful failure

# Check for empty data
data = response.json().get('data')
if not data:
    return None
```

**Common HTTP status codes:**
| Code | Meaning | Our Handling |
|------|---------|-------------|
| 200 | Success | Parse the data |
| 401 | Unauthorized (bad API key) | Return `None`, log error |
| 429 | Rate limited (too many requests) | Return `None`, log error |
| 500 | Server error | Return `None`, log error |

---

## 6. Database Design (MySQL)

### Schema Overview

The database uses **two tables** with a foreign key relationship:

```
┌───────────────────┐         ┌─────────────────────────────┐
│      assets       │         │      market_snapshots        │
├───────────────────┤         ├─────────────────────────────┤
│ asset_id (PK)     │◄────────│ asset_id (FK)               │
│ symbol            │   1:N   │ snapshot_id (PK, AUTO_INCR) │
│ name              │         │ price_usd                   │
└───────────────────┘         │ price_change_pct  ← TRIGGER │
                               │ market_cap_usd              │
                               │ total_blocks                │
                               │ dominance_pct               │
                               │ snapshot_time (DEFAULT NOW) │
                               └─────────────────────────────┘
```

### Table: `assets` (Dimension Table)

| Column | Type | Description |
|--------|------|-------------|
| `asset_id` | INT, PRIMARY KEY | Unique identifier |
| `symbol` | VARCHAR | Ticker symbol (BTC, ETH) |
| `name` | VARCHAR | Full name (Bitcoin, Ethereum) |

**Seed data (from `setup.sql`):**

```sql
INSERT IGNORE INTO assets (asset_id, symbol, name) VALUES
    (1, 'BTC', 'Bitcoin'),
    (2, 'ETH', 'Ethereum');
```

`INSERT IGNORE` makes this **idempotent** — safe to run multiple times without duplicating rows.

### Table: `market_snapshots` (Fact Table)

| Column | Type | Description |
|--------|------|-------------|
| `snapshot_id` | INT, AUTO_INCREMENT, PK | Unique row ID |
| `asset_id` | INT, FOREIGN KEY → assets | Links to asset |
| `price_usd` | DECIMAL(18,2) | Price in USD |
| `price_change_pct` | DECIMAL | % change from last snapshot (trigger-calculated) |
| `market_cap_usd` | BIGINT | Total market capitalization |
| `total_blocks` | INT | Blocks mined |
| `dominance_pct` | DECIMAL(5,2) | Market share % |
| `snapshot_time` | TIMESTAMP, DEFAULT NOW | When the data was recorded |

### Database Normalization (1NF, 2NF, 3NF)

| Normal Form | Rule | How We Follow It |
|-------------|------|-------------------|
| **1NF** | No repeating groups, atomic values | Each column has one value; no arrays |
| **2NF** | No partial dependencies | Asset name/symbol stored separately in `assets`, not repeated in every snapshot |
| **3NF** | No transitive dependencies | Every column depends only on the primary key |

**Why this matters:** Without normalization, we'd repeat "Bitcoin" and "BTC" in every single snapshot row. With 1000 snapshots, that's 1000 redundant copies. Normalization eliminates this waste.

### Stored Procedure: `sp_insert_snapshot`

```sql
CREATE PROCEDURE sp_insert_snapshot(
    IN p_asset_id    INT,
    IN p_price       DECIMAL(18, 2),
    IN p_market_cap  BIGINT,
    IN p_blocks      INT,
    IN p_dominance   DECIMAL(5, 2)
)
BEGIN
    INSERT INTO market_snapshots
        (asset_id, price_usd, market_cap_usd, total_blocks, dominance_pct)
    VALUES
        (p_asset_id, p_price, p_market_cap, p_blocks, p_dominance);
END
```

**Why use a stored procedure instead of raw SQL?**
1. **Separation of concerns**: SQL logic lives in the database, not scattered in Python code
2. **Security**: Prevents SQL injection (parameters are typed)
3. **Reusability**: Any application can call the same procedure
4. **Maintainability**: Change the INSERT logic in one place

**How Python calls it:**
```python
cursor.callproc('sp_insert_snapshot', (
    asset_id,                    # 1 (Bitcoin) or 2 (Ethereum)
    market_data['price'],        # 87432.15
    market_data['market_cap'],   # 1720000000000
    market_data['blocks'],       # 890123
    market_data['dominance'],    # 61.34
))
```

### BEFORE INSERT Trigger

The database has a `BEFORE INSERT` trigger on `market_snapshots` that **automatically calculates `price_change_pct`** before each row is saved:

```
When a new snapshot is inserted:
  1. Look up the previous snapshot for the same asset
  2. Calculate: ((new_price - old_price) / old_price) × 100
  3. Store the result in price_change_pct
```

**Why use a trigger?**
- The calculation happens at the **database level**, not in Python
- Every insert — from any source — gets the calculation automatically
- It's **impossible** to forget to calculate it

### Foreign Key Relationship

```sql
market_snapshots.asset_id → assets.asset_id
```

This is a **one-to-many** relationship:
- One asset (Bitcoin) → many snapshots (one per pipeline run)
- The FK constraint ensures you can't insert a snapshot for a non-existent asset

### SQL JOIN (Used in Dashboard and Export)

```sql
SELECT a.name, s.price_usd, s.price_change_pct, ...
FROM market_snapshots s
JOIN assets a ON s.asset_id = a.asset_id
ORDER BY s.snapshot_time DESC;
```

This combines data from both tables. Without the JOIN, you'd only see `asset_id: 1` instead of `name: Bitcoin`.

---

## 7. DevOps & Deployment

### 7.1 Docker

#### What is Docker?

Docker packages your application and all its dependencies into a **container** — a lightweight, isolated environment that runs the same on any machine.

#### Dockerfile (How the Container is Built)

```dockerfile
FROM python:3.13-slim          # Start from official Python image

WORKDIR /app                   # Set working directory inside container

COPY requirements.txt .        # Copy dependencies file first
RUN pip install --no-cache-dir -r requirements.txt  # Install packages

COPY . .                       # Copy all project files

CMD ["python", "pipeline.py"]  # Default command when container starts
```

**Why copy `requirements.txt` first?**
Docker uses a **layer cache**. If your code changes but dependencies don't, Docker reuses the cached dependency layer — making builds much faster.

### 7.2 Docker Compose (Multi-Container Orchestration)

Docker Compose runs **multiple containers** together. Our `docker-compose.yml` defines 3 services:

```
┌─────────────────────────────────────────────────────────┐
│                  Docker Compose Network                   │
│                                                           │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │   MySQL   │    │   Pipeline    │    │   Dashboard    │   │
│  │   (db)    │◄───│   (Python)   │    │  (Streamlit)   │   │
│  │  :3306    │    │              │    │    :8501       │   │
│  └──────────┘    └──────────────┘    └───────────────┘   │
│       ▲                                      │           │
│       └──────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

| Service | Image | Purpose | Port |
|---------|-------|---------|------|
| `db` | `mysql:8.0` | Database server | 3306 |
| `pipeline` | Built from Dockerfile | Fetches data, stores in DB | None |
| `dashboard` | Built from Dockerfile | Web UI | 8501 |

**Key Docker Compose features used:**

| Feature | What It Does | Why It Matters |
|---------|-------------|----------------|
| `depends_on: condition: service_healthy` | Pipeline waits for MySQL to be ready | Prevents "connection refused" errors |
| `healthcheck` | MySQL pings itself every 10 seconds | Compose knows when DB is truly ready |
| `volumes: db_data` | Persistent storage for MySQL | Data survives container restarts |
| `env_file: .env` | Loads environment variables | Credentials stay out of code |
| `DB_HOST: db` | Override host to Docker service name | Containers find each other by name |

**One-command launch:**
```bash
docker-compose up --build
# Builds images → Starts MySQL → Waits for health → Runs pipeline → Starts dashboard
```

### 7.3 CI/CD (GitHub Actions)

#### What is CI/CD?

- **CI (Continuous Integration):** Automatically test code on every push
- **CD (Continuous Deployment):** Automatically deploy after tests pass

#### Our CI Pipeline (`.github/workflows/ci.yml`)

```
Push to main → GitHub Actions triggers → Lint (flake8) → Test (pytest)
```

**Step-by-step:**

| Step | Tool | What It Does |
|------|------|-------------|
| 1. Checkout | `actions/checkout@v4` | Downloads the code |
| 2. Setup Python | `actions/setup-python@v5` | Installs Python 3.13 |
| 3. Install deps | `pip install` | Installs requirements.txt + flake8 |
| 4. Lint | `flake8` | Checks for syntax errors and style issues |
| 5. Test | `pytest` | Runs all unit tests |

**Flake8 lint rules:**
- **Blocking** (fail the build): `E9` (syntax errors), `F63` (assertion issues), `F7` (statement errors), `F82` (undefined names)
- **Warnings** (non-blocking): Style issues, max line length 120

**Trigger conditions:**
```yaml
on:
  push:
    branches: [main]        # Every push to main
  pull_request:
    branches: [main]        # Every PR targeting main
```

---

## 8. Testing Strategy

### Framework: pytest

All tests use **mocks** — no real API calls or database connections needed.

### Test Files

#### `tests/test_pipeline.py` (6 tests)

| Test Class | Test | What It Validates |
|-----------|------|-------------------|
| `TestFetchMarketData` | `test_success` | 200 response → correctly parsed dict |
| `TestFetchMarketData` | `test_api_failure_returns_none` | 500 status → returns `None` |
| `TestFetchMarketData` | `test_empty_payload_returns_none` | 200 with empty data → returns `None` |
| `TestStoreSnapshot` | `test_calls_stored_procedure` | Stored procedure called with correct args |
| `TestRunPipeline` | `test_pipeline_commits_on_success` | Transaction committed after success |
| `TestRunPipeline` | `test_pipeline_skips_failed_fetches` | Failed fetches don't call store |

#### `tests/test_export.py` (2 tests)

| Test Class | Test | What It Validates |
|-----------|------|-------------------|
| `TestExportToCsv` | `test_csv_file_created_with_correct_data` | CSV has correct headers and data |
| `TestExportToCsv` | `test_handles_db_error_gracefully` | DB error doesn't crash the program |

### How Mocking Works

```python
@patch("pipeline.requests.get")              # Replace real HTTP with mock
def test_success(self, mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,                      # Fake a 200 response
        json=lambda: {"data": {...}},         # Fake JSON data
    )
    result = fetch_market_data("bitcoin")
    assert result["price"] == 87432.15        # Verify parsing works
```

**Why mock?**
1. **Speed**: No network calls = tests run in milliseconds
2. **Reliability**: Tests don't fail because an API is down
3. **Cost**: No API rate limits consumed
4. **Isolation**: Tests only test YOUR code, not external services

### Running Tests

```bash
python -m pytest tests/ -v
```

---

## 9. Project File Map

```
financial-data-pipeline/
│
├── pipeline.py              # 🔧 BACKEND: Main orchestrator
│                            #    - fetch_market_data(): calls Blockchair API
│                            #    - store_snapshot(): inserts via stored procedure
│                            #    - run_pipeline(): loops all assets, commits
│
├── export_report.py         # 🔧 BACKEND: CSV export
│                            #    - export_to_csv(): SQL JOIN → CSV file
│
├── dashboard.py             # 🖥️ FRONTEND: Streamlit web dashboard
│                            #    - load_data(): SQL → Pandas DataFrame
│                            #    - KPI cards, line chart, data table
│
├── crypto_stats.py          # 🔧 BACKEND: Quick CLI stats viewer
│                            #    - fetch_market_data(): log BTC stats
│
├── logger.py                # 🔧 BACKEND: Centralized logging factory
│                            #    - get_logger(): returns configured logger
│
├── database/
│   └── setup.sql            # 🗄️ DATABASE: Stored procedure + seed data
│
├── tests/
│   ├── test_pipeline.py     # ✅ TESTING: 6 pipeline unit tests
│   └── test_export.py       # ✅ TESTING: 2 export unit tests
│
├── Dockerfile               # 🐳 DEVOPS: Container image definition
├── docker-compose.yml       # 🐳 DEVOPS: Multi-container orchestration
├── requirements.txt         # 📦 DEPS: Python package list
│
├── .github/workflows/
│   └── ci.yml               # 🔄 CI/CD: GitHub Actions pipeline
│
├── .env                     # 🔑 CONFIG: API keys & DB creds (git-ignored)
├── .gitignore               # Git ignore rules
├── .dockerignore            # Docker ignore rules
└── README.md                # 📖 Project documentation
```

---

## 10. Interview Questions & Answers

### General / Architecture

**Q: Can you explain what this project does?**
> It's an automated data pipeline that fetches live cryptocurrency prices from the Blockchair REST API, stores them in a normalized MySQL database using stored procedures and triggers, exports reports to CSV, and visualizes everything through an interactive Streamlit dashboard. The entire stack runs in Docker with CI/CD via GitHub Actions.

**Q: Why did you choose this architecture?**
> I followed the standard ETL (Extract-Transform-Load) pattern used in data engineering. The pipeline extracts data from an external API, transforms it (parsing JSON, calculating price changes via triggers), and loads it into a relational database. The dashboard provides the presentation layer. Docker ensures reproducibility, and CI/CD ensures code quality.

**Q: How would you scale this project?**
> Several ways: (1) Add more assets by inserting rows into the `assets` table and the `ASSETS` list. (2) Schedule the pipeline with cron or a job scheduler like Airflow for automated runs. (3) Add Redis caching for the dashboard to reduce DB load. (4) Use a message queue like RabbitMQ if we need real-time streaming instead of batch processing. (5) Move to a time-series database like TimescaleDB for better performance with millions of data points.

---

### Backend / Python

**Q: How does the pipeline handle errors?**
> Three levels: (1) If an API call fails (non-200 status or empty data), `fetch_market_data` returns `None` and that asset is skipped — it doesn't crash the pipeline. (2) Database errors are caught with `try/except` and logged. (3) The `finally` block ensures the database connection is always closed, preventing resource leaks.

**Q: What is `python-dotenv` and why do you use it?**
> `python-dotenv` loads environment variables from a `.env` file into `os.environ`. This keeps sensitive credentials (API keys, database passwords) out of the source code. The `.env` file is git-ignored so secrets are never committed to version control.

**Q: Why use `logging` instead of `print()`?**
> The `logging` module provides: (1) severity levels (DEBUG, INFO, WARNING, ERROR) so you can filter output, (2) timestamps and module names in every message, (3) output to multiple destinations (console + file) simultaneously, (4) a consistent format across all modules. `print()` has none of these features.

**Q: What design patterns did you use?**
> (1) **Factory Pattern** in `logger.py` — `get_logger()` creates configured objects consistently. (2) **Pipeline/Orchestrator Pattern** — `run_pipeline()` coordinates multiple steps in sequence. (3) **Repository Pattern** (loosely) — `store_snapshot()` abstracts database operations behind a function. (4) **Configuration Externalization** — credentials in `.env` following the 12-Factor App methodology.

---

### API

**Q: What is a REST API?**
> REST (Representational State Transfer) is an architectural style for web services. It uses standard HTTP methods (GET, POST, PUT, DELETE) to access resources identified by URLs. Data is typically exchanged as JSON. It's stateless — each request contains all the information needed to process it.

**Q: How do you handle API authentication?**
> The Blockchair API uses API key authentication. The key is stored in an environment variable (`BLOCKCHAIR_API_KEY`), loaded at startup, and passed as a query parameter in every request. This is a common pattern for public APIs.

**Q: What happens if the API is down?**
> The `requests.get()` call has a 30-second timeout. If the API returns a non-200 status code, the function returns `None`. If a network error occurs, it raises an exception that's caught by the `try/except` in `run_pipeline()`. Either way, the pipeline continues with the next asset.

**Q: What is the difference between query parameters and request body?**
> Query parameters are appended to the URL (e.g., `?key=abc123`) and are used for filtering or authentication in GET requests. The request body is used in POST/PUT requests to send larger data payloads. We use query parameters because we're making GET requests (reading data, not writing).

---

### Database / SQL

**Q: What is database normalization?**
> Normalization is the process of organizing data to minimize redundancy. Our database follows Third Normal Form (3NF): (1) 1NF — all values are atomic, no repeating groups. (2) 2NF — no partial dependencies on a composite key. (3) 3NF — no transitive dependencies. We achieve this by separating asset metadata (`assets` table) from time-series data (`market_snapshots` table).

**Q: What is a stored procedure and why use one?**
> A stored procedure is pre-compiled SQL code stored in the database. Our `sp_insert_snapshot` encapsulates the INSERT logic. Benefits: (1) Separation of concerns — SQL lives in the DB, not in Python. (2) Security — parameters are typed, reducing SQL injection risk. (3) Performance — the SQL is pre-compiled. (4) Reusability — any application can call the same procedure.

**Q: What is a database trigger?**
> A trigger is code that runs automatically when a database event occurs. Our `BEFORE INSERT` trigger on `market_snapshots` automatically calculates `price_change_pct` by comparing the new price against the previous snapshot for the same asset. This ensures the calculation always happens, regardless of which application inserts the data.

**Q: What is a foreign key?**
> A foreign key is a column that references the primary key of another table. Our `market_snapshots.asset_id` references `assets.asset_id`. This enforces referential integrity — you can't create a snapshot for an asset that doesn't exist, and you can't delete an asset that has snapshots.

**Q: Explain the SQL JOIN you use.**
> We use an INNER JOIN: `FROM market_snapshots s JOIN assets a ON s.asset_id = a.asset_id`. This combines rows from both tables where the `asset_id` matches. Without it, we'd only see numeric IDs instead of names like "Bitcoin". An INNER JOIN returns only matching rows — if an asset has no snapshots, it won't appear.

---

### Docker / DevOps

**Q: What is Docker and why use it?**
> Docker packages an application and its dependencies into a container — an isolated environment that runs consistently on any machine. Benefits: (1) "Works on my machine" problem is solved. (2) Easy to deploy — one command starts everything. (3) Isolation — each service runs independently. (4) Reproducibility — the exact same environment in development and production.

**Q: Explain your Docker Compose setup.**
> We have 3 services: (1) `db` — MySQL 8.0 with a health check, persistent volume, and auto-initialization via setup.sql. (2) `pipeline` — Python container that fetches data and stores it. (3) `dashboard` — Streamlit container exposed on port 8501. The pipeline and dashboard wait for MySQL's health check to pass before starting.

**Q: What is a Docker health check?**
> A health check is a command Docker runs periodically to verify a container is working. Our MySQL service runs `mysqladmin ping` every 10 seconds. Other services use `depends_on: condition: service_healthy` to wait until MySQL is truly ready — not just started, but actually accepting connections.

**Q: What is a Docker volume?**
> A volume is persistent storage that survives container restarts. Our `db_data` volume stores MySQL data files. Without it, all data would be lost when the container stops.

---

### Testing

**Q: Why do you use mocks in your tests?**
> Mocking replaces real external dependencies (API, database) with controlled fake objects. This gives us: (1) Speed — no network calls. (2) Reliability — tests don't fail due to external service outages. (3) Isolation — we test only our code logic, not third-party services. (4) Cost — no API rate limits or database setup needed.

**Q: What is the difference between unit tests and integration tests?**
> Unit tests test individual functions in isolation (our tests mock all dependencies). Integration tests test how components work together (e.g., actually connecting to a database). Our tests are primarily unit tests. A true integration test would use Docker Compose to spin up MySQL and test the full pipeline.

**Q: How does your CI/CD pipeline work?**
> On every push to `main` or pull request, GitHub Actions: (1) checks out the code, (2) installs Python 3.13 and dependencies, (3) runs flake8 linting to catch syntax errors, (4) runs pytest to verify all tests pass. If any step fails, the build fails and the team is notified.

---

### Behavioral / Problem-Solving

**Q: What was the most challenging part of this project?**
> Ensuring the pipeline is resilient to failures. The API could be down, the database could be unreachable, or the data could be malformed. I implemented multiple layers of error handling: graceful `None` returns for failed API calls, try/except blocks for database errors, and a `finally` clause to always clean up connections.

**Q: If you had more time, what would you add?**
> (1) **Alerting** — Send email/Slack notifications when prices change significantly. (2) **More assets** — Add support for 50+ cryptocurrencies. (3) **Historical backfill** — Import past data for trend analysis. (4) **User authentication** — Protect the dashboard with login. (5) **API rate limiting** — Implement exponential backoff for API calls. (6) **Data validation** — Add schema validation for API responses using Pydantic.

**Q: How do you ensure data quality?**
> Multiple safeguards: (1) API response validation — checking status codes and non-empty data before processing. (2) Database constraints — foreign keys prevent orphaned records, typed columns prevent invalid data. (3) Stored procedure — parameters are typed (DECIMAL, INT, BIGINT). (4) Trigger — price_change_pct is calculated server-side, ensuring consistency.
