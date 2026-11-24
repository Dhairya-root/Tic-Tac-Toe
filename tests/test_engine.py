import pytest

from ai import choose_move
from engine import WIN_LINES, is_draw, legal_moves, new_board, next_player, play, winner


@pytest.mark.parametrize("line", WIN_LINES)
@pytest.mark.parametrize("player", ["X", "O"])
def test_every_winning_line(line, player):
    board = new_board()
    for cell in line:
        board = board[:cell] + player + board[cell + 1:]
    assert winner(board) == player


def test_draw():
    board = "XOXXOOOXX"
    assert winner(board) is None and is_draw(board)


@pytest.mark.parametrize("cell", [-1, 9, "a", None, True, 1.5])
def test_invalid_cell_rejected(cell):
    with pytest.raises(ValueError):
        play(new_board(), cell, "X")


def test_occupied_cell_and_finished_game_rejected():
    board = play(new_board(), 4, "X")
    with pytest.raises(ValueError):
        play(board, 4, "O")
    with pytest.raises(ValueError):
        play("XXXOO....", 5, "O")


def test_easy_ai_plays_a_legal_move():
    board = "XO......."
    assert choose_move(board, "O", "easy") in legal_moves(board)


def test_hard_ai_never_loses():
    """Try every possible human move at every turn; the computer (O) must never lose."""
    def explore(board, turn):
        if winner(board) or is_draw(board):
            assert winner(board) != "X"
            return
        if turn == "X":
            for cell in legal_moves(board):
                explore(play(board, cell, "X"), next_player(turn))
        else:
            explore(play(board, choose_move(board, "O", "hard"), "O"), next_player(turn))

    explore(new_board(), "X")


def test_hard_ai_takes_a_winning_move():
    assert choose_move("OO.XX....", "O", "hard") == 2
