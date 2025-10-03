# Tenants Post‑Migration Verifier — README

This README shows how to run the **entity → provision-state-machine** migration **verification script** using a clean Python **virtual environment** on **Windows (PowerShell)** and **Git Bash (on Windows)**.

The verifier checks, per **environment** and **cluster**:
- That each **tenant** in `entity` with `status = "provisioned"` exists in `provision-state-machine`.
- That the **number of users** per tenant in `entity` (any status) matches the count in `provision-state-machine`.
- Produces CSV reports: a **summary** and a list of **missing users**.

> **Files required:**
> - `verify_migration.py`
> - `.env` (contains mongodb configuration)
> - (optional) `load-env.ps1` helper to setup env variables by using PowerShell

---

## Prerequisites
- **Python 3.10+** (3.12 recommended). On Windows, install via Microsoft Store or:
  ```powershell
  winget install -e --id Python.Python.3.12
  ```
- **Mongo/Cosmos DB** connectivity and a valid **Mongo URI**.
- Network access from your machine to the database.


---

## Environment file (.env)

Create a `.env` file at the repo root to store your Mongo/Cosmos connection settings. Do not commit it; add `.env` to your `.gitignore.`

`.env` example

```
# Example: Azure Cosmos DB for Mongo
MONGO_URI="mongodb://<USER>:<PRIMARY_KEY>@<ACCOUNT_NAME>.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@your-app@"
# Database name
DB_NAME="deployment"
DEFAULT_ENVIRONMENT="dev"
DEFAULT_CLUSTER_INDEX="013"

```

Add `.gitignore`

```bash
.env
```

## Load the .env — PowerShell

`load-env.ps1`

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./load-env.ps1
```

## Load the .env — Git Bash

```
set -a
source .env
set +a
```


## Quick Start — Windows (PowerShell)

1) **Open PowerShell** and go to your repo folder
```powershell
cd C:\repos\tenants-post-validator
```

2) **Create a virtual environment** (venv)
```powershell
py -m venv .venv
```

3) **Activate the venv** (temporarily allow script execution for this session)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
You should see `(.venv)` at the start of your prompt.

4) **Install dependencies inside the venv**
```powershell
python -m pip install --upgrade pip
pip install pymongo
```

## 5a) Run the verifier (with explicit values)* (example: `environment=dev`, `cluster=013`)

```powershell
python .\verify_migration.py `
  --mongo-uri "mongodb://<USER>:<PASS>@<HOST>:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@your-app@" `
  --db-name "deployment" `
  --environment dev `
  --cluster-index 013 `
  --entity-collection entity `
  --psm-collection provision-state-machine `
  --csv-out .\migration_report_dev_013.csv `
  --missing-out .\missing_users_dev_013.csv
```

## 5b) Run the verifier (using .env variables)

```powershell
# Load .env (if not loaded yet)
./load-env.ps1

python ./verify_migration.py `
  --mongo-uri "$env:MONGO_URI" `
  --db-name "$env:DB_NAME" `
  --environment "$env:DEFAULT_ENVIRONMENT" `
  --cluster-index "$env:DEFAULT_CLUSTER_INDEX" `
  --entity-collection entity `
  --psm-collection provision-state-machine `
  --csv-out ./migration_report_${env:DEFAULT_ENVIRONMENT}_${env:DEFAULT_CLUSTER_INDEX}.csv `
  --missing-out ./missing_users_${env:DEFAULT_ENVIRONMENT}_${env:DEFAULT_CLUSTER_INDEX}.csv
```


### PowerShell one-liners
- Install deps with explicit venv Python:
  ```powershell
  .\.venv\Scripts\python.exe -m pip install --upgrade pip pymongo
  ```
- Run with explicit venv Python:
  ```powershell
  .\.venv\Scripts\python.exe .\verify_migration.py --help
  ```

## Quick Start — Git Bash (on Windows)


1) **Open Git Bash** and go to your repo
```bash
cd /c/repos/tenants-post-validator
```

2) **Create a virtual environment**
```bash
py -m venv .venv
# If `py` is not found, try:
# python -m venv .venv
```

3) **Activate the venv (bash)**
```bash
source .venv/Scripts/activate
```
You should see `(.venv)` in your prompt.

4) **Install dependencies**
```bash
python -m pip install --upgrade pip
pip install pymongo
```
## 5a) Run the verifier (with explicit values)
```bash
python verify_migration.py \
  --mongo-uri "mongodb://<USER>:<PASS>@<HOST>:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@your-app@" \
  --db-name deployment \
  --environment dev \
  --cluster-index 013 \
  --entity-collection entity \
  --psm-collection provision-state-machine \
  --csv-out ./migration_report_dev_013.csv \
  --missing-out ./missing_users_dev_013.csv
```

## 5b) Run the verifier (using .env variables)  

```bash
set -a && source .env && set +a
python verify_migration.py --mongo-uri "$MONGO_URI" --db-name "$DB_NAME" --environment "${DEFAULT_ENVIRONMENT:-dev}" --cluster-index "${DEFAULT_CLUSTER_INDEX:-013}" --entity-collection entity --psm-collection provision-state-machine --csv-out "./migration_report_${DEFAULT_ENVIRONMENT:-dev}_${DEFAULT_CLUSTER_INDEX:-013}.csv" --missing-out "./missing_users_${DEFAULT_ENVIRONMENT:-dev}_${DEFAULT_CLUSTER_INDEX:-013}.csv"
```




6) **Deactivate** when finished
```bash
deactivate
```

### Git Bash tips
- If `python` points to the global interpreter, prefer the venv directly:
  ```bash
  .venv/Scripts/python.exe -m pip install pymongo
  .venv/Scripts/python.exe verify_migration.py --help
  ```
- To keep secrets out of history, export the URI once per session:
  ```bash
  export MONGO_URI='mongodb://<USER>:<PASS>@<HOST>:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@your-app@'
  python verify_migration.py --mongo-uri "$MONGO_URI" --db-name ftds --environment dev --cluster-index 013 \
    --entity-collection entity --psm-collection provision-state-machine
  ```

---

## Re-running for multiple env/cluster combos
Run the command again changing:
- `--environment` (e.g., `dev`, `qa2`, `prod`)
- `--cluster-index` (e.g., `001`, `013`, etc.)

Example (PowerShell, QA2/001):
```powershell
python .\verify_migration.py `
  --mongo-uri "$env:MONGO_URI" `
  --db-name "deploy,ent" `
  --environment qa2 `
  --cluster-index 001 `
  --entity-collection entity `
  --psm-collection provision-state-machine
```

---

## Output artifacts
- **Summary CSV:** `migration_report_<ENV>_<CLUSTER>.csv`
- **Missing users CSV:** `missing_users_<ENV>_<CLUSTER>.csv`

These files help you confirm counts and identify any users to migrate/add.

---