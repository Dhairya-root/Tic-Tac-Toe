"""Computer opponent: random moves on easy, minimax with alpha-beta pruning on hard."""
import random

from engine import legal_moves, next_player, play, winner


def _score(board, me, turn, alpha, beta, depth):
    won = winner(board)
    if won:
        return 10 - depth if won == me else depth - 10  # prefer quick wins, slow losses
    moves = legal_moves(board)
    if not moves:
        return 0
    if turn == me:
        best = -99
        for m in moves:
            best = max(best, _score(play(board, m, turn), me, next_player(turn), alpha, beta, depth + 1))
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best
    best = 99
    for m in moves:
        best = min(best, _score(play(board, m, turn), me, next_player(turn), alpha, beta, depth + 1))
        beta = min(beta, best)
        if alpha >= beta:
            break
    return best


def choose_move(board, me, difficulty="hard"):
    moves = legal_moves(board)
    if difficulty == "easy":
        return random.choice(moves)
    scored = [(_score(play(board, m, me), me, next_player(me), -99, 99, 1), m) for m in moves]
    top = max(s for s, _ in scored)
    return random.choice([m for s, m in scored if s == top])
