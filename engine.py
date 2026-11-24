"""Tic Tac Toe rules. Pure Python: no web or database code, so it is easy to test."""

WIN_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
EMPTY = "."


def new_board():
    return EMPTY * 9


def winning_line(board):
    for line in WIN_LINES:
        a, b, c = line
        if board[a] != EMPTY and board[a] == board[b] == board[c]:
            return line
    return None


def winner(board):
    line = winning_line(board)
    return board[line[0]] if line else None


def is_draw(board):
    return winner(board) is None and EMPTY not in board


def legal_moves(board):
    return [i for i, c in enumerate(board) if c == EMPTY]


def next_player(player):
    return "O" if player == "X" else "X"


def play(board, cell, player):
    """Return the new board, or raise ValueError with a message a player can read."""
    if winner(board) or is_draw(board):
        raise ValueError("The game is already over.")
    if not isinstance(cell, int) or isinstance(cell, bool) or not 0 <= cell <= 8:
        raise ValueError("Choose a cell from 0 to 8.")
    if board[cell] != EMPTY:
        raise ValueError("That cell is already taken.")
    return board[:cell] + player + board[cell + 1:]
