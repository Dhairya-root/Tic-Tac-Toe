# Tic Tac Toe (Python, Flask)

A Tic Tac Toe web game with a rules engine, a minimax computer opponent, accounts, saved game history and statistics.

## Run it

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                     # open http://127.0.0.1:5000
```

## Test it

```bash
pytest -q
```

## Project layout

| File | Purpose |
|---|---|
| engine.py | Board rules, win and draw detection (no web code) |
| ai.py | Easy (random) and hard (minimax with alpha-beta) opponent |
| app.py | Flask app: models, login, REST API |
| templates/index.html | The whole frontend: login, board, history |
| tests/ | Engine, AI and API tests |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/register, /api/login, /api/logout | Accounts (JSON body) |
| GET | /api/me | Current user |
| POST | /api/games | Start a game: `{"mode": "ai" or "two", "difficulty": "easy" or "hard"}` |
| GET | /api/games/<id> | Current board and status |
| POST | /api/games/<id>/move | `{"cell": 0-8}`; the computer replies in the same response |
| GET | /api/history, /api/stats | Past games, and your record against the computer |

In computer mode you are X and move first.

## Deploy

```bash
export SECRET_KEY="<long random value>"
export SESSION_COOKIE_SECURE=true          # when serving over HTTPS
export DATABASE_URL="postgresql://user:password@localhost/tictactoe"   # optional; SQLite is the default
gunicorn -w 3 -b 127.0.0.1:8000 "app:create_app()"
```

Put Nginx in front of Gunicorn for HTTPS. `/health` returns `{"status": "ok"}` for uptime checks. For PostgreSQL, also `pip install psycopg2-binary`.
