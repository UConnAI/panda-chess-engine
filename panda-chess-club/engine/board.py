"""Chess rules, transparent features, and the same two-ply search for both bots."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import chess

FEATURE_NAMES = ['Pawn balance', 'Knight balance', 'Bishop balance', 'Rook balance',
                 'Queen balance', 'Bishop pair', 'Pawn advance', 'Center control',
                 'Attacked squares', 'King pawn shield', 'Doubled pawns',
                 'Isolated pawns', 'Castling rights', 'Side to move', 'Check pressure',
                 'Central pawns']
VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
CENTER = [chess.D4, chess.E4, chess.D5, chess.E5]

def material(board):
    return float(sum(v * (len(board.pieces(p, chess.WHITE)) - len(board.pieces(p, chess.BLACK))) for p, v in VALUES.items()))

def features(board):
    """16 observable quantities; mostly White minus Black. No engine labels here."""
    out = [float(len(board.pieces(p, chess.WHITE)) - len(board.pieces(p, chess.BLACK))) for p in VALUES]
    sides = []
    for color in [chess.WHITE, chess.BLACK]:
        pawns = list(board.pieces(chess.PAWN, color))
        files = [sum(chess.square_file(s) == f for s in pawns) for f in range(8)]
        advance = sum((chess.square_rank(s) if color else 7 - chess.square_rank(s)) - 1 for s in pawns)
        attacks = 0
        for square in chess.scan_forward(board.occupied_co[color]): attacks |= board.attacks_mask(square)
        king = board.king(color)
        shield = 0
        if king is not None:
            rank = chess.square_rank(king) + (1 if color else -1)
            for file in range(max(0, chess.square_file(king)-1), min(8, chess.square_file(king)+2)):
                if 0 <= rank <= 7 and board.piece_at(chess.square(file, rank)) == chess.Piece(chess.PAWN, color): shield += 1
        isolated = sum(files[f] for f in range(8) if (f == 0 or files[f-1] == 0) and (f == 7 or files[f+1] == 0))
        sides.append([float(len(board.pieces(chess.BISHOP, color)) >= 2), advance,
                      sum(board.is_attacked_by(color, sq) for sq in CENTER), attacks.bit_count(), shield,
                      sum(max(0, n-1) for n in files), isolated,
                      int(board.has_kingside_castling_rights(color)) + int(board.has_queenside_castling_rights(color))])
    out.extend(a-b for a, b in zip(*sides))
    out.extend([1.0 if board.turn else -1.0,
                (-1.0 if board.turn else 1.0) if board.is_check() else 0.0,
                float(sum(board.piece_at(s) == chess.Piece(chess.PAWN, chess.WHITE) for s in CENTER)
                      - sum(board.piece_at(s) == chess.Piece(chess.PAWN, chess.BLACK) for s in CENTER))])
    return out

def terminal_score(board, ply=0):
    outcome = board.outcome(claim_draw=True)
    if outcome is None: return None
    if outcome.winner is None: return 0.0
    return (10000.0-ply) * (1 if outcome.winner else -1)

def choose_move(board, evaluator, depth=2):
    """Deterministic minimax with alpha-beta. Depth 2 includes the opponent's reply."""
    nodes = 0
    def search(remaining, alpha, beta, ply):
        nonlocal nodes
        nodes += 1
        terminal = terminal_score(board, ply)
        if terminal is not None: return terminal
        if remaining == 0: return max(-10.0, min(10.0, evaluator(board)))
        maximize = board.turn == chess.WHITE
        best = float('-inf') if maximize else float('inf')
        for move in sorted(board.legal_moves, key=lambda m: (not board.is_capture(m), m.uci())):
            board.push(move)
            value = search(remaining-1, alpha, beta, ply+1)
            board.pop()
            best = max(best, value) if maximize else min(best, value)
            if maximize: alpha = max(alpha, best)
            else: beta = min(beta, best)
            if beta <= alpha: break
        return best
    if board.is_game_over(claim_draw=True): return None, None, nodes
    best_move, best_value = None, float('-inf') if board.turn else float('inf')
    maximize = board.turn
    alpha, beta = float('-inf'), float('inf')
    for move in sorted(board.legal_moves, key=lambda m: (not board.is_capture(m), m.uci())):
        board.push(move)
        value = search(depth-1, alpha, beta, 1)
        board.pop()
        if best_move is None or (value > best_value if maximize else value < best_value):
            best_move, best_value = move, value
        if maximize: alpha = max(alpha, best_value)
        else: beta = min(beta, best_value)
    return best_move, best_value, nodes

def replay(moves):
    if not isinstance(moves, list) or len(moves) > 600: raise ValueError('Invalid move history.')
    board = chess.Board()
    for text in moves:
        if not isinstance(text, str): raise ValueError('Each move must be a UCI string.')
        if board.is_game_over(claim_draw=True): raise ValueError('This game has already ended.')
        move = chess.Move.from_uci(text)
        if move not in board.legal_moves: raise ValueError('That move is not legal in this position.')
        board.push(move)
    return board

def board_state(board):
    outcome = board.outcome(claim_draw=True)
    return {'fen': board.fen(), 'turn': 'White' if board.turn else 'Black',
            'pieces': {chess.square_name(s): p.symbol() for s, p in board.piece_map().items()},
            'legal_moves': [] if outcome else [m.uci() for m in board.legal_moves],
            'check': board.is_check(), 'result': outcome.result() if outcome else None,
            'termination': outcome.termination.name.replace('_', ' ').lower() if outcome else None}
