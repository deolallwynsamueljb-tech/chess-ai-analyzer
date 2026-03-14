import streamlit as st
import chess
import chess.pgn
import chess.engine
import chess.svg
import matplotlib.pyplot as plt
import io
from streamlit.components.v1 import html
import os
import shutil
 

import streamlit as st
import chess
import chess.pgn
import chess.engine
import chess.svg
import matplotlib.pyplot as plt
import io
from streamlit.components.v1 import html
import os
import shutil

# ---------------- ENGINE LOADER ----------------

def load_engine():

    # Try automatic detection
    path = shutil.which("stockfish")

    if path:
        return chess.engine.SimpleEngine.popen_uci(path)

    # Common Linux locations (Streamlit Cloud)
    possible_paths = [
        "/usr/games/stockfish",
        "/usr/bin/stockfish",
        "/home/adminuser/venv/bin/stockfish"
    ]

    for p in possible_paths:
        if os.path.exists(p):
            return chess.engine.SimpleEngine.popen_uci(p)

    raise RuntimeError("Stockfish engine not found")

# ---------------- PAGE ----------------

st.set_page_config(layout="wide")
st.title("♟ Chess AI Analyzer")

# ---------------- SIDEBAR ----------------

st.sidebar.header("Game Input")

uploaded_file = st.sidebar.file_uploader("Upload PGN", type=["pgn"])

pgn_text = st.sidebar.text_area(
    "Or paste PGN here",
    height=200
)

depth = st.sidebar.slider("Engine Depth", 8, 20, 12)

# ---------------- ENGINE ----------------

 

# ---------------- MOVE CLASSIFICATION ----------------

def classify_move(prev_eval, new_eval):

    if prev_eval is None:
        return ""

    diff = abs(new_eval - prev_eval)

    if diff > 300:
        return "??"
    elif diff > 150:
        return "?"
    elif diff > 80:
        return "?!"
    elif diff > 30:
        return "!"
    else:
        return "!!"

# ---------------- ACCURACY ----------------

def compute_accuracy(evals):

    score = 0

    for i in range(1,len(evals)):
        diff = abs(evals[i] - evals[i-1])
        score += max(0,100 - diff/10)

    return round(score/max(1,len(evals)),1)

# ---------------- ANALYSIS ----------------

@st.cache_data
def analyze_game(pgn_string, depth):

    game = chess.pgn.read_game(io.StringIO(pgn_string))
    board = game.board()

    engine = load_engine()

    moves = []
    evaluations = []
    classifications = []
    best_moves = []

    prev_eval = None

    analysis_board = board.copy()

    for move in game.mainline_moves():

        analysis_board.push(move)

        info = engine.analyse(
            analysis_board,
            chess.engine.Limit(depth=depth)
        )

        score = info["score"].white().score(mate_score=10000)

        best = info["pv"][0]

        moves.append(move)
        evaluations.append(score)

        cls = classify_move(prev_eval,score)
        classifications.append(cls)

        best_moves.append(best)

        prev_eval = score

    engine.quit()

    return game,moves,evaluations,classifications,best_moves

# ---------------- LOAD GAME ----------------

game = None

if uploaded_file is not None:
    pgn_string = uploaded_file.read().decode()
    game,moves,evaluations,classifications,best_moves = analyze_game(pgn_string,depth)

elif pgn_text.strip() != "":
    pgn_string = pgn_text
    game,moves,evaluations,classifications,best_moves = analyze_game(pgn_string,depth)

# ---------------- DEFAULT BOARD ----------------

if game is None:

    board = chess.Board()

    st.info("Upload or paste a PGN to analyze.")

    board_svg = chess.svg.board(board=board,size=720)

    html(board_svg,height=750)

    st.stop()

# ---------------- ACCURACY DISPLAY ----------------

accuracy = compute_accuracy(evaluations)

st.metric("Game Accuracy",f"{accuracy}%")

# ---------------- SESSION STATE ----------------

if "move_index" not in st.session_state:
    st.session_state.move_index = 0

move_index = st.session_state.move_index

# ---------------- BOARD POSITION ----------------

board = game.board()
temp_board = board.copy()

for i in range(move_index+1):
    temp_board.push(moves[i])

# ---------------- LAYOUT ----------------

eval_col,board_col,moves_col = st.columns([0.6,6,2])

# ---------------- EVAL BAR ----------------

with eval_col:

    score = evaluations[move_index]

    cap = 400
    score = max(min(score,cap),-cap)

    white_percent = (score + cap) / (2*cap)
    black_percent = 1-white_percent

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

    arrow=None

    if move_index < len(best_moves):

        best = best_moves[move_index]

        arrow=[chess.svg.Arrow(best.from_square,best.to_square,color="#00FF00")]

    board_svg = chess.svg.board(
        board=temp_board,
        size=720,
        arrows=arrow
    )

    html(board_svg,height=750)

    c1,c2,c3,c4 = st.columns(4)

    with c1:
        if st.button("⏮ Start"):
            st.session_state.move_index = 0

    with c2:
        if st.button("◀ Prev"):
            if st.session_state.move_index>0:
                st.session_state.move_index-=1

    with c3:
        if st.button("Next ▶"):
            if st.session_state.move_index<len(moves)-1:
                st.session_state.move_index+=1

    with c4:
        if st.button("End ⏭"):
            st.session_state.move_index=len(moves)-1

# ---------------- MOVE LIST ----------------

with moves_col:

    st.subheader("Moves")

    san_board = board.copy()

    move_text=""

    for i,move in enumerate(moves):

        if i%2==0:
            move_text+=f"{i//2+1}. "

        move_san=san_board.san(move)

        move_san+=f" {classifications[i]}"

        move_text+=move_san+" "

        san_board.push(move)

        if i%2==1:
            move_text+="\n"

    st.text(move_text)

# ---------------- GRAPH ----------------

st.subheader("Engine Evaluation")

fig,ax = plt.subplots(figsize=(12,4))

ax.plot(evaluations,linewidth=2)
ax.axhline(0)

ax.set_xlabel("Move Number")
ax.set_ylabel("Centipawn Evaluation")

ax.grid(True)

st.pyplot(fig)