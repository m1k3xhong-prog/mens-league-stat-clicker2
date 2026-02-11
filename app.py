# streamlit_app.py
# Basketball Stat Clicker — All Players Visible (Auto-load roster.csv)
# Python 3.8+ compatible

import os
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Basketball Stat Clicker", layout="wide")

# Box score columns requested
EXPORT_COLUMNS = ["PTS", "REB", "AST", "2PM", "2PA", "3PM", "3PA", "STL", "BLK", "TOV"]

# Buttons per player:
# label, stat_key, delta, implies_attempt_key (make implies attempt)
BUTTONS = [
    ("2PM",     "2PM", 1, "2PA"),
    ("2P Miss", "2PA", 1, None),
    ("3PM",     "3PM", 1, "3PA"),
    ("3P Miss", "3PA", 1, None),
    ("REB",     "REB", 1, None),
    ("AST",     "AST", 1, None),
    ("STL",     "STL", 1, None),
    ("BLK",     "BLK", 1, None),
    ("TOV",     "TOV", 1, None),
]


# -----------------------
# State + helpers
# -----------------------
def ensure_state() -> None:
    if "roster" not in st.session_state:
        # roster = list of {"name": str, "stats": dict[str,int]}
        st.session_state.roster = []
    if "action_stack" not in st.session_state:
        # action_stack = list of (player_index, [(stat_key, delta), ...])
        st.session_state.action_stack = []


def blank_stats() -> Dict[str, int]:
    # everything except PTS is stored; PTS is computed
    return {k: 0 for k in EXPORT_COLUMNS if k != "PTS"}


def points(stats: Dict[str, int]) -> int:
    return 2 * stats.get("2PM", 0) + 3 * stats.get("3PM", 0)


def apply_change(player_idx: int, changes: List[Tuple[str, int]]) -> None:
    p = st.session_state.roster[player_idx]
    for key, delta in changes:
        p["stats"][key] = max(0, int(p["stats"].get(key, 0)) + int(delta))
    st.session_state.action_stack.append((player_idx, changes))


def undo_last() -> None:
    if not st.session_state.action_stack:
        st.toast("Nothing to undo.", icon="ℹ️")
        return

    idx, changes = st.session_state.action_stack.pop()
    if idx < 0 or idx >= len(st.session_state.roster):
        return

    p = st.session_state.roster[idx]
    for key, delta in changes:
        p["stats"][key] = max(0, int(p["stats"].get(key, 0)) - int(delta))


def build_df() -> pd.DataFrame:
    rows = []
    for p in st.session_state.roster:
        s = p["stats"]
        rows.append({
            "PLAYER": p["name"],
            "PTS": points(s),
            "REB": s.get("REB", 0),
            "AST": s.get("AST", 0),
            "2PM": s.get("2PM", 0),
            "2PA": s.get("2PA", 0),
            "3PM": s.get("3PM", 0),
            "3PA": s.get("3PA", 0),
            "STL": s.get("STL", 0),
            "BLK": s.get("BLK", 0),
            "TOV": s.get("TOV", 0),
        })

    df = pd.DataFrame(rows, columns=["PLAYER"] + EXPORT_COLUMNS)

    if len(df) > 0:
        totals = {"PLAYER": "TOTALS"}
        for col in EXPORT_COLUMNS:
            totals[col] = int(df[col].sum())
        df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

    return df


def import_roster_from_df(df_in: pd.DataFrame) -> None:
    cols = [c.lower().strip() for c in df_in.columns]
    if "name" not in cols:
        st.error("CSV must include a 'name' column (header should be exactly: name).")
        return

    name_col = df_in.columns[cols.index("name")]
    roster = []
    for _, r in df_in.iterrows():
        nm = str(r.get(name_col, "")).strip()
        if nm:
            roster.append({"name": nm, "stats": blank_stats()})

    st.session_state.roster = roster
    st.session_state.action_stack = []
    st.success(f"Imported {len(roster)} players.")
    st.rerun()


# -----------------------
# App start
# -----------------------
ensure_state()

# ✅ Auto-load roster.csv ONCE if it exists in the repo
if "roster_loaded" not in st.session_state:
    st.session_state.roster_loaded = True
    if (not st.session_state.roster) and os.path.exists("roster.csv"):
        try:
            df_auto = pd.read_csv("roster.csv")
            cols = [c.lower().strip() for c in df_auto.columns]
            if "name" in cols:
                name_col = df_auto.columns[cols.index("name")]
                auto_roster = []
                for _, r in df_auto.iterrows():
                    nm = str(r.get(name_col, "")).strip()
                    if nm:
                        auto_roster.append({"name": nm, "stats": blank_stats()})
                st.session_state.roster = auto_roster
        except Exception:
            # don't crash the app if roster.csv is malformed
            pass

st.title("🏀 Basketball Stat Clicker (Streamlit) — All Players")

# -----------------------
# Sidebar controls
# -----------------------
with st.sidebar:
    st.header("Roster")

    with st.expander("Add player", expanded=True):
        new_name = st.text_input("Player name", key="add_name")
        if st.button("Add to roster", use_container_width=True):
            nm = (new_name or "").strip()
            if not nm:
                st.error("Please enter a player name.")
            else:
                st.session_state.roster.append({"name": nm, "stats": blank_stats()})
                st.session_state.add_name = ""
                st.rerun()

    with st.expander("Import roster CSV", expanded=False):
        st.caption("CSV header must be: name")
        up = st.file_uploader("Upload roster CSV", type=["csv"])
        if up is not None:
            try:
                df_in = pd.read_csv(up)
                import_roster_from_df(df_in)
            except Exception as e:
                st.error(f"Could not import CSV: {e}")

    with st.expander("Roster actions", expanded=False):
        if st.button("Reset all stats", use_container_width=True, disabled=(len(st.session_state.roster) == 0)):
            for p in st.session_state.roster:
                p["stats"] = blank_stats()
            st.session_state.action_stack = []
            st.rerun()

        if st.button("Clear roster", use_container_width=True, disabled=(len(st.session_state.roster) == 0)):
            st.session_state.roster = []
            st.session_state.action_stack = []
            st.rerun()

# -----------------------
# Top controls
# -----------------------
c1, c2 = st.columns([1, 2], gap="large")

with c1:
    if st.button("Undo last action", use_container_width=True, disabled=(len(st.session_state.roster) == 0)):
        undo_last()
        st.rerun()

with c2:
    csv_bytes = build_df().to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download stats CSV",
        data=csv_bytes,
        file_name="game_stats.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=(len(st.session_state.roster) == 0),
    )

st.divider()

# -----------------------
# Player panels
# -----------------------
if not st.session_state.roster:
    st.info("Add players in the sidebar or include roster.csv in the repo to auto-load.")
else:
    st.subheader("Players")

    per_row = 2  # change to 3 if you want more compact on desktop
    cols = st.columns(per_row, gap="large")

    for i, p in enumerate(st.session_state.roster):
        with cols[i % per_row]:
            st.markdown(f"### {p['name']}")
            s = p["stats"]
            st.caption(f"PTS: **{points(s)}**  •  REB: **{s.get('REB',0)}**  •  AST: **{s.get('AST',0)}**")

            # Button grid: 3 columns of stat buttons per player
            bcols = st.columns(3)
            for bi, (label, key, delta, implies) in enumerate(BUTTONS):
                with bcols[bi % 3]:
                    btn_key = f"btn_{i}_{key}_{label}"
                    if st.button(label, key=btn_key, use_container_width=True):
                        changes = [(key, delta)]
                        if implies:
                            changes.append((implies, delta))
                        apply_change(i, changes)
                        st.rerun()

            if st.button("Remove player", key=f"rm_{i}", use_container_width=True):
                st.session_state.roster.pop(i)
                st.session_state.action_stack = []
                st.rerun()

    st.divider()
    st.subheader("Box score")
    st.dataframe(build_df(), use_container_width=True, hide_index=True)
