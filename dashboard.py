import streamlit as st
import chess
import chess.pgn
import chess.engine
import chess.svg
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import os
import zipfile
import stat
from streamlit.components.v1 import html

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="Chess AI Analyzer",
    layout="wide",
    page_icon="♟"
)

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Source+Sans+3:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Source Sans 3', sans-serif;
        background-color: #1a1a1a;
        color: #e8e0d0;
    }

    .main { background-color: #1a1a1a; }

    h1, h2, h3 {
        font-family: 'Merriweather', serif;
        color: #e8c97e;
    }

    .stButton > button {
        background-color: #2c2c2c;
        color: #e8c97e;
        border: 1px solid #e8c97e;
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.2s;
        width: 100%;
    }

    .stButton > button:hover {
        background-color: #e8c97e;
        color: #1a1a1a;
    }

    .metric-box {
        background: linear-gradient(135deg, #2c2c2c, #1a1a1a);
        border: 1px solid #e8c97e44;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
        text-align: center;
    }

    .metric-label {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #e8c97e;
        font-family: 'Merriweather', serif;
    }

    .opening-box {
        background: #2c2c2c;
        border-left: 3px solid #e8c97e;
        border-radius: 4px;
        padding: 10px 14px;
        margin-bottom: 16px;
        font-size: 14px;
        color: #e8e0d0;
    }

    .opening-label {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }

    .move-item {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: monospace;
        font-size: 13px;
        cursor: pointer;
    }

    .move-active {
        background-color: #e8c97e;
        color: #1a1a1a;
        font-weight: bold;
    }

    .blunder-card {
        background: #2c1a1a;
        border-left: 3px solid #e05252;
        border-radius: 4px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 13px;
    }

    .mistake-card {
        background: #2c2415;
        border-left: 3px solid #e08c52;
        border-radius: 4px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 13px;
    }

    .inaccuracy-card {
        background: #1e2215;
        border-left: 3px solid #b0c452;
        border-radius: 4px;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 13px;
    }

    .section-title {
        font-size: 13px;
        font-weight: 600;
        color: #e8c97e;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 16px 0 8px 0;
        border-bottom: 1px solid #333;
        padding-bottom: 4px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #333;
    }

    .stSlider > div > div > div {
        background-color: #e8c97e !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- ENGINE LOADER ----------------

def load_engine():
    engine_path = "./stockfish"

    if not os.path.exists(engine_path):
        for zname in ["stockfish.zip", "stockfish-ubuntu-x86-64.zip"]:
            if os.path.exists(zname):
                with zipfile.ZipFile(zname, "r") as z:
                    for member in z.namelist():
                        if "stockfish" in member.lower() and not member.endswith("/"):
                            z.extract(member, ".")
                            extracted = os.path.join(".", member)
                            if extracted != engine_path:
                                os.rename(extracted, engine_path)
                            break
                break

    if not os.path.exists(engine_path):
        st.error("❌ Stockfish binary not found. Commit 'stockfish.zip' (Linux binary) to your repo.")
        st.stop()

    current_mode = os.stat(engine_path).st_mode
    os.chmod(engine_path, current_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return chess.engine.SimpleEngine.popen_uci(engine_path)

# ---------------- OPENING DETECTION ----------------

OPENINGS = [
    ("Ruy López", ["e4","e5","Nf3","Nc6","Bb5"]),
    ("Sicilian Defense", ["e4","c5"]),
    ("French Defense", ["e4","e6","d4","d5"]),
    ("Caro-Kann", ["e4","c6","d4","d5"]),
    ("Italian Game", ["e4","e5","Nf3","Nc6","Bc4"]),
    ("Queen's Gambit", ["d4","d5","c4"]),
    ("King's Indian Defense", ["d4","Nf6","c4","g6"]),
    ("Nimzo-Indian", ["d4","Nf6","c4","e6","Nc3","Bb4"]),
    ("English Opening", ["c4"]),
    ("Pirc Defense", ["e4","d6","d4","Nf6"]),
    ("Dutch Defense", ["d4","f5"]),
    ("Slav Defense", ["d4","d5","c4","c6"]),
    ("Grünfeld Defense", ["d4","Nf6","c4","g6","Nc3","d5"]),
    ("London System", ["d4","d5","Nf3","Nf6","Bf4"]),
    ("King's Gambit", ["e4","e5","f4"]),
    ("Scotch Game", ["e4","e5","Nf3","Nc6","d4"]),
]

def detect_opening(moves, board):
    san_board = board.copy()
    san_list = []
    for move in moves[:12]:
        san_list.append(san_board.san(move))
        san_board.push(move)

    detected = "Unknown Opening"
    for name, pattern in sorted(OPENINGS, key=lambda x: -len(x[1])):
        if all(p in san_list[:len(pattern)+2] for p in pattern):
            detected = name
            break
    return detected

# ---------------- MOVE CLASSIFICATION ----------------

def classify_move(prev_eval, new_eval, is_white_move):
    if prev_eval is None:
        return ""
    # Flip perspective: if it's black's move, a drop for white = improvement for black
    if is_white_move:
        diff = new_eval - prev_eval  # positive = good for white
    else:
        diff = prev_eval - new_eval  # positive = good for black

    if diff < -300:
        return "??"
    elif diff < -150:
        return "?"
    elif diff < -80:
        return "?!"
    elif diff > 80:
        return "!!"
    elif diff > 30:
        return "!"
    else:
        return ""

# ---------------- ACCURACY ----------------

def compute_accuracy(evals):
    if len(evals) < 2:
        return 100.0
    score = 0
    for i in range(1, len(evals)):
        diff = abs(evals[i] - evals[i - 1])
        score += max(0, 100 - diff / 10)
    return round(score / max(1, len(evals) - 1), 1)

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
    move_num = 0

    for move in game.mainline_moves():
        is_white = (move_num % 2 == 0)
        analysis_board.push(move)

        info = engine.analyse(analysis_board, chess.engine.Limit(depth=depth))
        score = info["score"].white().score(mate_score=10000)
        best = info["pv"][0] if info.get("pv") else move

        moves.append(move)
        evaluations.append(score)
        classifications.append(classify_move(prev_eval, score, is_white))
        best_moves.append(best)

        prev_eval = score
        move_num += 1

    engine.quit()
    return game, moves, evaluations, classifications, best_moves

# ---------------- SIDEBAR ----------------

st.sidebar.markdown("## ♟ Game Input")
uploaded_file = st.sidebar.file_uploader("Upload PGN", type=["pgn"])
pgn_text = st.sidebar.text_area("Or paste PGN here", height=200)
depth = st.sidebar.slider("Engine Depth", 8, 20, 12)

# ---------------- LOAD GAME ----------------

game = None

if uploaded_file is not None:
    pgn_string = uploaded_file.read().decode()
    game, moves, evaluations, classifications, best_moves = analyze_game(pgn_string, depth)
elif pgn_text.strip():
    pgn_string = pgn_text
    game, moves, evaluations, classifications, best_moves = analyze_game(pgn_string, depth)

# ---------------- DEFAULT ----------------

if game is None:
    st.markdown("## ♟ Chess AI Analyzer")
    st.info("Upload or paste a PGN to begin analysis.")
    board_svg = chess.svg.board(board=chess.Board(), size=600,
        colors={"square light": "#f0d9b5", "square dark": "#b58863"})
    html(board_svg, height=630)
    st.stop()

# ---------------- SESSION STATE ----------------

if "move_index" not in st.session_state:
    st.session_state.move_index = 0

move_index = st.session_state.move_index

# ---------------- BOARD POSITION ----------------

board = game.board()
temp_board = board.copy()
for i in range(move_index + 1):
    temp_board.push(moves[i])

# ---------------- HEADER ----------------

headers = dict(game.headers)
white_player = headers.get("White", "White")
black_player = headers.get("Black", "Black")
white_elo = headers.get("WhiteElo", "?")
black_elo = headers.get("BlackElo", "?")
result = headers.get("Result", "*")

opening_name = detect_opening(moves, board)
accuracy = compute_accuracy(evaluations)

st.markdown(f"## ♟ {white_player} ({white_elo}) vs {black_player} ({black_elo})  —  {result}")

# ---------------- OPENING + ACCURACY ROW ----------------

h1, h2, h3 = st.columns([3, 1, 1])
with h1:
    st.markdown(f"""
    <div class="opening-box">
        <div class="opening-label">Opening</div>
        {opening_name}
    </div>
    """, unsafe_allow_html=True)
with h2:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Accuracy</div>
        <div class="metric-value">{accuracy}%</div>
    </div>
    """, unsafe_allow_html=True)
with h3:
    score_now = evaluations[move_index]
    score_display = f"+{score_now/100:.1f}" if score_now > 0 else f"{score_now/100:.1f}"
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Eval</div>
        <div class="metric-value">{score_display}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- LAYOUT ----------------

eval_col, board_col, moves_col = st.columns([0.5, 5, 2])

# ---------------- EVAL BAR ----------------

with eval_col:
    score = evaluations[move_index]
    cap = 400
    score = max(min(score, cap), -cap)
    white_percent = (score + cap) / (2 * cap)
    black_percent = 1 - white_percent

    st.markdown(
        f"""
        <div style="height:600px;width:24px;border-radius:6px;overflow:hidden;border:1px solid #444;margin-top:4px;">
            <div style="background:#1a1a1a;height:{black_percent*100:.1f}%;transition:height 0.3s;"></div>
            <div style="background:#f0d9b5;height:{white_percent*100:.1f}%;transition:height 0.3s;"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------- BOARD ----------------

with board_col:
    arrow = None
    if move_index < len(best_moves):
        best = best_moves[move_index]
        arrow = [chess.svg.Arrow(best.from_square, best.to_square, color="#27ae60")]

    # Chess.com color scheme
    board_svg = chess.svg.board(
        board=temp_board,
        size=600,
        arrows=arrow or [],
        colors={
            "square light": "#f0d9b5",
            "square dark":  "#b58863",
            "margin":       "#2c2c2c",
            "coord":        "#e8c97e",
        }
    )
    html(board_svg, height=630)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("⏮ Start"):
            st.session_state.move_index = 0
            st.rerun()
    with c2:
        if st.button("◀ Prev"):
            if st.session_state.move_index > 0:
                st.session_state.move_index -= 1
                st.rerun()
    with c3:
        if st.button("Next ▶"):
            if st.session_state.move_index < len(moves) - 1:
                st.session_state.move_index += 1
                st.rerun()
    with c4:
        if st.button("End ⏭"):
            st.session_state.move_index = len(moves) - 1
            st.rerun()

# ---------------- MOVE LIST ----------------

with moves_col:
    st.markdown('<div class="section-title">Moves</div>', unsafe_allow_html=True)

    san_board = board.copy()
    move_html = ""

    for i, move in enumerate(moves):
        move_san = san_board.san(move)
        cls_symbol = classifications[i]
        label = f"{move_san}{cls_symbol}"

        if i % 2 == 0:
            move_html += f"<span style='color:#888;font-size:12px;margin-right:2px;'>{i//2+1}.</span>"

        active = "move-active" if i == move_index else ""
        move_html += f"<span class='move-item {active}'>{label}</span> "

        if i % 2 == 1:
            move_html += "<br>"

        san_board.push(move)

    st.markdown(f"<div style='line-height:2;font-family:monospace;font-size:13px;'>{move_html}</div>",
                unsafe_allow_html=True)

    # ---------------- BLUNDER SUMMARY ----------------

    st.markdown('<div class="section-title" style="margin-top:20px;">Game Summary</div>',
                unsafe_allow_html=True)

    san_board2 = board.copy()
    blunders, mistakes, inaccuracies = [], [], []

    for i, move in enumerate(moves):
        move_san = san_board2.san(move)
        player = white_player if i % 2 == 0 else black_player
        cls = classifications[i]
        label = f"{'White' if i%2==0 else 'Black'} move {i//2+1}. {move_san}"

        if cls == "??":
            blunders.append(label)
        elif cls == "?":
            mistakes.append(label)
        elif cls == "?!":
            inaccuracies.append(label)

        san_board2.push(move)

    summary_html = ""

    if blunders:
        summary_html += f"<div style='color:#e05252;font-size:12px;margin:4px 0;font-weight:600;'>🔴 Blunders ({len(blunders)})</div>"
        for b in blunders:
            summary_html += f"<div class='blunder-card'>{b}</div>"

    if mistakes:
        summary_html += f"<div style='color:#e08c52;font-size:12px;margin:8px 0 4px;font-weight:600;'>🟠 Mistakes ({len(mistakes)})</div>"
        for m in mistakes:
            summary_html += f"<div class='mistake-card'>{m}</div>"

    if inaccuracies:
        summary_html += f"<div style='color:#b0c452;font-size:12px;margin:8px 0 4px;font-weight:600;'>🟡 Inaccuracies ({len(inaccuracies)})</div>"
        for n in inaccuracies:
            summary_html += f"<div class='inaccuracy-card'>{n}</div>"

    if not blunders and not mistakes and not inaccuracies:
        summary_html += "<div style='color:#4caf50;font-size:13px;'>✅ Clean game — no blunders or mistakes!</div>"

    st.markdown(summary_html, unsafe_allow_html=True)

# ---------------- EVAL GRAPH ----------------

st.markdown('<div class="section-title" style="margin-top:20px;">Engine Evaluation</div>',
            unsafe_allow_html=True)

fig, ax = plt.subplots(figsize=(12, 3))
fig.patch.set_facecolor("#1a1a1a")
ax.set_facecolor("#2c2c2c")

x = list(range(len(evaluations)))
y = [max(min(e, 1000), -1000) for e in evaluations]

ax.fill_between(x, y, 0, where=[v > 0 for v in y], color="#f0d9b5", alpha=0.6)
ax.fill_between(x, y, 0, where=[v <= 0 for v in y], color="#1a1a1a", alpha=0.8)
ax.plot(x, y, color="#e8c97e", linewidth=1.5)
ax.axhline(0, color="#888", linewidth=0.8)
ax.axvline(move_index, color="#e8c97e", linewidth=1, linestyle="--", alpha=0.7)

ax.set_xlabel("Move Number", color="#888", fontsize=10)
ax.set_ylabel("Centipawns", color="#888", fontsize=10)
ax.tick_params(colors="#888")
for spine in ax.spines.values():
    spine.set_edgecolor("#444")

st.pyplot(fig)