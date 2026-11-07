# ODP - Outils de déploiement de plateformes

Local app for reserving SSH containers. The browser is Vue. The API is FastAPI. Data is in PostgreSQL. Docker runs the pool on the same machine.

Flask and MySQL are no longer part of this tree. The last commit that still contains them is `0c7911d`.

## What you need

- Python 3.12 or newer
- Node.js 22
- Docker, with permission to use the Docker socket
- Ansible, only when a reservation installs packages

## Database

From the repository root:

```bash
docker compose up -d
python3 -m venv api/.venv
api/.venv/bin/pip install -r api/requirements.txt
cp api/.env.example api/.env
api/.venv/bin/python -m api.migrate
```

`api/.env` is local and is not committed. The example uses database `odp_platform`, user `odp`, password `odp`, on `localhost:5432`.

`python -m api.migrate` applies `database/postgres/001_init.sql`. It does not drop an existing database.

## Run

Use two processes. Both start from the repository root, except the frontend commands, which start in `frontend/`.

```bash
api/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173 . The dev server forwards `/api` and `/socket.io` to port 8000.

Sign in with `admin` / `admin`. That account is created the first time someone logs in. Register makes a normal user. An admin cannot reserve a machine.

## Container pool

`init_pool.py` builds `pool-node:latest` from `Docker/ssh`, starts `pool-node-1` through `pool-node-30` on host ports 3000–3029, and stores them as free rows in PostgreSQL.

```bash
api/.venv/bin/python init_pool.py
```

Run it from the repository root, with Docker already running and the database migrated. It removes an existing container of the same name before creating a new one.

Only the API process on port 8000 may release expired containers. Do not run a second expiry loop.

## Left in the tree

`vagrant/` and `Docker/` stay. `pool_manager.sh` and `database/migrate_data.py` still speak MySQL. They are not how this app starts or stores the pool.
