def make_game(client, **options):
    return client.post("/api/games", json=options).get_json()


def test_register_login_logout(client):
    assert client.post("/api/register", json={"username": "bob", "password": "secret1"}).status_code == 201
    client.post("/api/logout", json={})
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/login", json={"username": "bob", "password": "secret1"}).status_code == 200
    assert client.get("/api/me").get_json() == {"username": "bob"}


def test_duplicate_username_and_bad_input(client, user):
    assert client.post("/api/register", json={"username": "alice", "password": "secret1"}).status_code == 409
    assert client.post("/api/register", json={"username": "x", "password": "secret1"}).status_code == 400
    assert client.post("/api/register", json={"username": "carol", "password": "123"}).status_code == 400


def test_wrong_password_rejected(client, user):
    client.post("/api/logout", json={})
    assert client.post("/api/login", json={"username": "alice", "password": "nope"}).status_code == 401


def test_password_is_hashed(client, user):
    from app import User
    with client.application.app_context():
        assert User.query.filter_by(username="alice").one().password_hash != "secret1"


def test_game_endpoints_need_login(client):
    assert client.post("/api/games", json={}).status_code == 401
    assert client.get("/api/history").status_code == 401


def test_two_player_game_to_a_win(client, user):
    game = make_game(client, mode="two")
    for cell in (0, 3, 1, 4, 2):
        result = client.post(f"/api/games/{game['id']}/move", json={"cell": cell}).get_json()
    assert result["status"] == "won" and result["winner"] == "X" and result["line"] == [0, 1, 2]
    assert client.post(f"/api/games/{game['id']}/move", json={"cell": 8}).status_code == 400


def test_occupied_and_invalid_moves(client, user):
    game = make_game(client, mode="two")
    url = f"/api/games/{game['id']}/move"
    client.post(url, json={"cell": 4})
    assert client.post(url, json={"cell": 4}).status_code == 400
    assert client.post(url, json={"cell": 12}).status_code == 400


def test_computer_replies_in_same_response(client, user):
    game = make_game(client, mode="ai", difficulty="hard")
    result = client.post(f"/api/games/{game['id']}/move", json={"cell": 0}).get_json()
    assert result["board"].count("X") == 1 and result["board"].count("O") == 1 and result["turn"] == "X"


def test_other_users_cannot_touch_a_game(client, user):
    game = make_game(client, mode="two")
    client.post("/api/logout", json={})
    client.post("/api/register", json={"username": "mallory", "password": "secret1"})
    assert client.get(f"/api/games/{game['id']}").status_code == 404
    assert client.post(f"/api/games/{game['id']}/move", json={"cell": 0}).status_code == 404


def test_non_json_post_rejected(client, user):
    assert client.post("/api/games", data="mode=ai").status_code == 415


def test_history_and_stats(client, user):
    game = make_game(client, mode="ai", difficulty="easy")
    for _ in range(5):
        free = [i for i, c in enumerate(game["board"]) if c == "."]
        game = client.post(f"/api/games/{game['id']}/move", json={"cell": free[0]}).get_json()
        if game["status"] != "playing":
            break
    history = client.get("/api/history").get_json()
    stats = client.get("/api/stats").get_json()
    assert len(history) == 1
    assert sum(stats.values()) == (0 if game["status"] == "playing" else 1)
