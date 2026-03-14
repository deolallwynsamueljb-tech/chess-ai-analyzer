import chess
import chess.pgn
import chess.engine

# start stockfish engine
engine = chess.engine.SimpleEngine.popen_uci("stockfish.exe")

# open PGN game
pgn = open("game.pgn")

game = chess.pgn.read_game(pgn)

board = game.board()

print("Analyzing chess game...\n")

move_number = 1

for move in game.mainline_moves():

    info_before = engine.analyse(board, chess.engine.Limit(depth=12))
    score_before = info_before["score"].white().score(mate_score=10000)

    board.push(move)

    info_after = engine.analyse(board, chess.engine.Limit(depth=12))
    score_after = info_after["score"].white().score(mate_score=10000)

    change = score_after - score_before

    print(f"Move {move_number}: {move} | Evaluation change: {change}")

    move_number += 1

engine.quit()