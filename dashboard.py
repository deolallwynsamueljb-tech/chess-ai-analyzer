import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
import chess
import chess.pgn
import chess.engine
import chess.svg
import matplotlib.pyplot as plt
import io
from streamlit.components.v1 import html

# ---------------- PAGE ----------------

st.set_page_config(layout="wide")
st.title("♟ Chess Analyzer")

# ---------------- SIDEBAR ----------------

st.sidebar.header("Game Input")

uploaded_file = st.sidebar.file_uploader("Upload PGN", type=["pgn"])

pgn_text = st.sidebar.text_area(
    "Or paste PGN here",
    height=200
)

depth = st.sidebar.slider("Engine Depth", 8, 20, 12)

# ---------------- LOAD GAME ----------------

game = None

if uploaded_file is not None:
    game = chess.pgn.read_game(uploaded_file)

elif pgn_text.strip() != "":
    game = chess.pgn.read_game(io.StringIO(pgn_text))

# ---------------- DEFAULT BOARD ----------------

if game is None:

    board = chess.Board()

    st.info("No PGN loaded. Showing starting position.")

    board_svg = chess.svg.board(
        board=board,
        size=720,
        coordinates=True,
        colors={
            "square light": "#E6E6E6",
            "square dark": "#9E9E9E",
            "border": "#2c2c2c",
            "coord": "#ffffff"
        }
    )

    html(board_svg, height=750)

    st.stop()

# ---------------- ANALYSIS ----------------

board = game.board()

moves = []
evaluations = []

analysis_board = board.copy()

try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish.exe")
except:
    st.error("Stockfish engine not found")
    st.stop()

for move in game.mainline_moves():

    analysis_board.push(move)

    info = engine.analyse(
        analysis_board,
        chess.engine.Limit(depth=depth)
    )

    score = info["score"].white().score(mate_score=10000)

    moves.append(move)
    evaluations.append(score)

engine.quit()

# ---------------- SESSION STATE ----------------

if "move_index" not in st.session_state:
    st.session_state.move_index = 0

move_index = st.session_state.move_index

# ---------------- MOVE BOARD ----------------

temp_board = board.copy()

for i in range(move_index + 1):
    temp_board.push(moves[i])

# ---------------- LAYOUT ----------------

eval_col, board_col, moves_col = st.columns([0.6,6,2])

# ---------------- EVALUATION BAR ----------------

with eval_col:

    score = evaluations[move_index]

    cap = 400
    score = max(min(score, cap), -cap)

    white_percent = (score + cap) / (2 * cap)
    black_percent = 1 - white_percent

    st.markdown(
    f"""
    <div style="
        height:720px;
        width:28px;
        border-radius:6px;
        overflow:hidden;
        border:1px solid #444;
    ">
        <div style="background:black;height:{black_percent*100}%"></div>
        <div style="background:white;height:{white_percent*100}%"></div>
    </div>
    """,
    unsafe_allow_html=True
    )

# ---------------- BOARD ----------------

with board_col:

    board_svg = chess.svg.board(
        board=temp_board,
        size=720,
        coordinates=True,
        colors={
            "square light": "#E6E6E6",
            "square dark": "#9E9E9E",
            "border": "#2c2c2c",
            "coord": "#ffffff"
        }
    )

    html(board_svg, height=750)

    # navigation buttons
    c1,c2,c3,c4 = st.columns(4)

    with c1:
        if st.button("⏮ Start"):
            st.session_state.move_index = 0

    with c2:
        if st.button("◀ Prev"):
            if st.session_state.move_index > 0:
                st.session_state.move_index -= 1

    with c3:
        if st.button("Next ▶"):
            if st.session_state.move_index < len(moves)-1:
                st.session_state.move_index += 1

    with c4:
        if st.button("End ⏭"):
            st.session_state.move_index = len(moves)-1

# ---------------- MOVE LIST ----------------

with moves_col:

    st.subheader("Moves")

    san_board = board.copy()

    move_text = ""

    for i, move in enumerate(moves):

        if i % 2 == 0:
            move_text += f"{i//2+1}. "

        move_text += san_board.san(move) + " "

        san_board.push(move)

        if i % 2 == 1:
            move_text += "\n"

    st.text(move_text)

# ---------------- GRAPH ----------------

st.subheader("Engine Evaluation")

fig, ax = plt.subplots(figsize=(12,4))

ax.plot(evaluations, linewidth=2)

ax.axhline(0)

ax.set_xlabel("Move Number")
ax.set_ylabel("Centipawn Evaluation")

ax.grid(True)

st.pyplot(fig)