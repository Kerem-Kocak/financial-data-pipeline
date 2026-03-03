# Automated Financial Data Pipeline 📊

A robust, automated data pipeline that extracts live cryptocurrency market data via the Blockchair REST API and systematically stores it in a normalized MySQL database for time-series analysis. 

## 🏗 Architecture & Technologies
* **Python 3:** Handles API requests, JSON parsing, and database connections.
* **REST API:** Integrates with the Blockchair API to fetch real-time blockchain statistics, market dominance, and pricing.
* **MySQL:** A fully normalized relational database (compliant with 1NF, 2NF, and 3NF) ensuring data integrity and eliminating redundancy.
* **SQL Triggers:** Implements server-side database logic to automatically calculate and store percentage price changes upon new data insertion.
* **Stored Procedures:** Encapsulates INSERT logic in `sp_insert_snapshot`, keeping SQL out of application code and providing a clean DB API layer.
* **Centralized Logging:** All modules use a shared `logger.py` that writes to both the console and `logs/pipeline.log` for a full audit trail.
* **Streamlit Dashboard:** Interactive web UI with KPI cards, price-history charts, and filtering.
* **Docker & Docker Compose:** One-command setup for the full stack (Python + MySQL + Dashboard).
* **CI/CD:** GitHub Actions workflow runs `flake8` (lint) and `pytest` (tests) on every push.

## 🗄️ Database Schema
The database is structured into two primary tables to maintain strict normalization:
1. `assets`: Stores static information about the financial assets (Symbol, Name).
2. `market_snapshots`: Stores the time-series data (Price, Market Cap, Blocks, Dominance) with a Foreign Key linked to the `assets` table.

**Advanced Features:**
* A `BEFORE INSERT` Trigger calculates the `price_change_pct` dynamically by comparing incoming API data against the most recent historical entry.
* A Stored Procedure (`sp_insert_snapshot`) encapsulates the insertion logic for clean separation of concerns.

## 📡 Multi-Asset Tracking
The pipeline tracks multiple cryptocurrencies in a single run. Currently configured assets:

| asset_id | Symbol | Name     |
|----------|--------|----------|
| 1        | BTC    | Bitcoin  |
| 2        | ETH    | Ethereum |

To add a new asset: insert a row into the `assets` table and append an entry to the `ASSETS` list in `pipeline.py`.

## 🚀 Setup & Installation

### 1. Clone the Repository
\`\`\`bash
git clone https://github.com/Kerem-Kocak/financial-data-pipeline.git
cd financial-data-pipeline
\`\`\`

### 2. Install Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 3. Environment Variables
Create a `.env` file in the root directory and add your credentials:
\`\`\`env
BLOCKCHAIR_API_KEY=your_api_key
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=financial_pipeline
\`\`\`

### 4. Database Initialization
Run the provided SQL scripts to create the normalized tables, the trigger, and the stored procedure:
\`\`\`bash
mysql -u root -p financial_pipeline < database/setup.sql
\`\`\`

### 5. Run the Pipeline
\`\`\`bash
python pipeline.py
\`\`\`
*Note: This script can be scheduled via Cron (Linux/Mac) or Task Scheduler (Windows) to run at automated intervals.*

### 6. Launch the Dashboard
\`\`\`bash
streamlit run dashboard.py
\`\`\`

### Alternative: Docker (full stack in one command)
\`\`\`bash
docker-compose up --build
\`\`\`
This starts MySQL, runs the pipeline, and opens the dashboard at `http://localhost:8501`.

## ✅ Testing
\`\`\`bash
python -m pytest tests/ -v
\`\`\`
All tests use mocked API and database calls — no live credentials needed.

## 📂 Project Structure
\`\`\`
├── pipeline.py            # Main orchestrator (fetch → store → export)
├── export_report.py       # SQL JOIN query → CSV export
├── dashboard.py           # Streamlit interactive dashboard
├── crypto_stats.py        # Standalone quick-stats viewer
├── logger.py              # Centralized logging configuration
├── Dockerfile             # Container image definition
├── docker-compose.yml     # Full-stack orchestration
├── requirements.txt       # Python dependencies
├── database/
│   └── setup.sql          # Stored procedure + asset seed data
├── tests/
│   ├── test_pipeline.py   # Pipeline unit tests
│   └── test_export.py     # Export module unit tests
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions CI pipeline
├── logs/
│   └── pipeline.log       # Full debug-level audit trail
├── .env                   # API keys & DB credentials (git-ignored)
├── .gitignore
└── README.md
\`\`\`