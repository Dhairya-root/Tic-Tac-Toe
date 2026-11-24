"""Flask backend: accounts, games, moves, history and stats."""
import os
import re
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

import ai
import engine

db = SQLAlchemy()


def _now():
    return datetime.now(timezone.utc)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_now)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    mode = db.Column(db.String(10), nullable=False)          # "ai" or "two"
    difficulty = db.Column(db.String(10))                    # "easy" or "hard" (ai mode only)
    board = db.Column(db.String(9), nullable=False, default=engine.new_board)
    turn = db.Column(db.String(1), nullable=False, default="X")
    status = db.Column(db.String(10), nullable=False, default="playing")  # playing, won, draw
    winner = db.Column(db.String(1))
    created_at = db.Column(db.DateTime, default=_now)


class Move(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("game.id"), nullable=False, index=True)
    move_number = db.Column(db.Integer, nullable=False)
    player = db.Column(db.String(1), nullable=False)
    cell = db.Column(db.Integer, nullable=False)


def fail(message, code):
    return jsonify(error=message), code


def state(game):
    return {"id": game.id, "mode": game.mode, "difficulty": game.difficulty, "board": list(game.board),
            "turn": game.turn, "status": game.status, "winner": game.winner,
            "line": engine.winning_line(game.board)}


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///tictactoe.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "true",
    )
    app.config.update(config or {})
    db.init_app(app)
    with app.app_context():
        db.create_all()

    def login_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return fail("Log in to continue.", 401)
            return view(*args, **kwargs)
        return wrapper

    def owned_game(game_id):
        game = db.session.get(Game, game_id)
        return game if game and game.user_id == session["user_id"] else None

    @app.before_request
    def require_json():
        # Browsers cannot send JSON cross-site without a preflight, which blocks forged requests.
        if request.method == "POST" and request.path.startswith("/api/") and not request.is_json:
            return fail("Send the request as JSON.", 415)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/register")
    def register():
        data = request.get_json(silent=True) or {}
        username, password = str(data.get("username", "")).strip(), str(data.get("password", ""))
        if not re.fullmatch(r"\w{3,20}", username):
            return fail("Username must be 3 to 20 letters, numbers or underscores.", 400)
        if len(password) < 6:
            return fail("Password must be at least 6 characters.", 400)
        if User.query.filter_by(username=username).first():
            return fail("That username is taken.", 409)
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        return jsonify(username=user.username), 201

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True) or {}
        user = User.query.filter_by(username=str(data.get("username", "")).strip()).first()
        if not user or not check_password_hash(user.password_hash, str(data.get("password", ""))):
            return fail("Wrong username or password.", 401)
        session.clear()
        session["user_id"] = user.id
        return jsonify(username=user.username)

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/me")
    @login_required
    def me():
        return jsonify(username=db.session.get(User, session["user_id"]).username)

    @app.post("/api/games")
    @login_required
    def new_game():
        data = request.get_json(silent=True) or {}
        mode = data.get("mode", "ai")
        difficulty = data.get("difficulty", "hard")
        if mode not in ("ai", "two") or difficulty not in ("easy", "hard"):
            return fail("Choose a valid mode and difficulty.", 400)
        game = Game(user_id=session["user_id"], mode=mode, difficulty=difficulty if mode == "ai" else None)
        db.session.add(game)
        db.session.commit()
        return jsonify(state(game)), 201

    @app.get("/api/games/<int:game_id>")
    @login_required
    def get_game(game_id):
        game = owned_game(game_id)
        return jsonify(state(game)) if game else fail("Game not found.", 404)

    def apply_move(game, cell):
        game.board = engine.play(game.board, cell, game.turn)
        number = Move.query.filter_by(game_id=game.id).count() + 1
        db.session.add(Move(game_id=game.id, move_number=number, player=game.turn, cell=cell))
        won = engine.winner(game.board)
        if won:
            game.status, game.winner = "won", won
        elif engine.is_draw(game.board):
            game.status = "draw"
        else:
            game.turn = engine.next_player(game.turn)

    @app.post("/api/games/<int:game_id>/move")
    @login_required
    def move(game_id):
        game = owned_game(game_id)
        if not game:
            return fail("Game not found.", 404)
        cell = (request.get_json(silent=True) or {}).get("cell")
        try:
            apply_move(game, cell)
            if game.mode == "ai" and game.status == "playing":  # the player is X, the computer is O
                apply_move(game, ai.choose_move(game.board, "O", game.difficulty))
        except ValueError as error:
            db.session.rollback()
            return fail(str(error), 400)
        db.session.commit()
        return jsonify(state(game))

    @app.get("/api/history")
    @login_required
    def history():
        games = Game.query.filter_by(user_id=session["user_id"]).order_by(Game.id.desc()).limit(20).all()
        return jsonify([{"id": g.id, "mode": g.mode, "difficulty": g.difficulty, "status": g.status,
                         "winner": g.winner, "created_at": g.created_at.isoformat()} for g in games])

    @app.get("/api/stats")
    @login_required
    def stats():
        """Record against the computer: the player is always X."""
        games = Game.query.filter_by(user_id=session["user_id"], mode="ai").filter(Game.status != "playing").all()
        return jsonify(wins=sum(g.winner == "X" for g in games), losses=sum(g.winner == "O" for g in games),
                       draws=sum(g.status == "draw" for g in games))

    return app


if __name__ == "__main__":
    import threading
    import webbrowser

    debug = os.environ.get("FLASK_DEBUG") == "1"
    if not debug:  # debug mode restarts Flask, which would open two tabs
        threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    create_app().run(debug=debug)