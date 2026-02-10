# app.py
# Streamlit Basketball Stat Clicker (Manual)
# Columns: PTS, REB, AST, 2PM, 2PA, 3PM, 3PA, STL, BLK, TOV
#
# Run locally:
#   pip install streamlit
#   streamlit run app.py
#
# Deploy free on Streamlit Community Cloud:
#   1) Create a GitHub repo with this app.py (and optional requirements.txt)
#   2) Go to share.streamlit.io, connect repo, deploy

import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Basketball Stat Clicker", layout="wide")

EXPORT_COLUMNS = ["PTS", "REB", "AST", "2PM", "2PA", "3PM", "3PA", "STL", "BLK", "TOV"]

# Buttons: (label, stat_key, delta, implies_attempt_key or None)
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

def ensure_state():
    if "roster" not in st.session_state:
        # roster is list of dicts: {"name": str, "number": str, "stats": {key:int}}
        st.session_state.roster = []
    if "selected" not in st.session_state:
        st.session_state.selected = None  # index
    if "action_stack" not in st.session_state:
        # list of (player_index, [(stat_key, delta), ...])
        st.session_state.action_stack = []

def blank_stats():
    return {k: 0 for k in EXPORT_COLUMNS if k != "PTS"}

def points(stats: dict) -> int:
    return 2 * stats.get("2PM", 0) + 3 * stats.get("3PM", 0)

def apply_change(player_idx: int, changes):
    """changes: list of (key, delta)"""
    p = st.session_state.roster[player_idx]
    for key, delta in changes:
        if key == "PTS":
            continue
        p["stats"][key] = max(0, p["stats"].get(key, 0) + delta)
    st.session_state.action_stack.append((player_idx, changes))

def click_button(stat_key: str, delta: int, implies_attempt: str | None):
    idx = st.session_state.selected
    if idx is None:
        st.warning("Select a player first.")
        return

    changes = [(stat_key, delta)]
    if implies_attempt:
        changes.append((implies_attempt, delta))
    apply_change(idx, changes)

def undo_last():
    if not st.session_state.action_stack:
        st.info("Nothing to undo.")
        return
    idx, changes = st.session_state.action_stack.pop()
    if idx < 0 or idx >= len(st.session_state.roster):
        return
    p = st.session_state.roster[idx]
    for key, delta in changes:
        p["stats"][key] = max(0, p["stats"].get(key, 0) - delta)

def build_df():
    rows = []
    for p in st.session_state.roster:
        s = p["stats"]
        row = {
            "PLAYER": p["name"],
            "NUMBER": p["number"],
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
        }
        rows.append(row)

    df = pd.DataFrame(rows, columns=["PLAYER", "NUMBER"] + EXPORT_COLUMNS)

    if len(df) > 0:
        totals = {col: 0 for col in ["PLAYER", "NUMBER"] + EXPORT_COLUMNS}
        totals["PLAYER"] = "TOTALS"
        totals["NUMBER"] = ""
        for col in EXPORT_COLUMNS:
            totals[col] = int(df[col].sum())
        df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

    return df

def roster_csv_template():
    # CSV template for roster import
    return "name,number\nPlayer 1,1\nPlayer 2,2\n"

ensure_state()

st.title("🏀 Basketball Stat Clicker (Streamlit)")

# Sidebar: roster management
with st.sidebar:
    st.header("Roster")

    with st.expander("Add player", expanded=True):
        name = st.text_input("Player name", key="add_name")
        number = st.text_input("Jersey # (optional)", key="add_number")
        if st.button("Add to roster", use_container_width=True):
            if not name.strip():
                st.error("Please enter a player name.")
            else:
                st.session_state.roster.append(
                    {"name": name.strip(), "number": number.strip(), "stats": blank_stats()}
                )
                st.session_state.add_name = ""
                st.session_state.add_number = ""
                if st.session_state.selected is None:
                    st.session_state.selected = 0

    with st.expander("Import roster CSV", expanded=False):
        st.caption("CSV headers: name, number (number optional)")
        st.download_button(
            "Download roster CSV template",
            data=roster_csv_template().encode("utf-8"),
            file_name="roster_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
        upload = st.file_uploader("Upload roster CSV", type=["csv"])
        if upload is not None:
            try:
                df_in = pd.read_csv(upload)
                cols = [c.lower().strip() for c in df_in.columns]
                if "name" not in cols:
                    st.error("CSV must include a 'name' column.")
                else:
                    name_col = df_in.columns[cols.index("name")]
                    number_col = None
                    for cand in ["number", "jersey", "jersey_number"]:
                        if cand in cols:
                            number_col = df_in.columns[cols.index(cand)]
                            break

                    new_roster = []
                    for _, r in df_in.iterrows():
                        nm = str(r.get(name_col, "")).strip()
                        if not nm:
                            continue
                        num = str(r.get(number_col, "")).strip() if number_col else ""
                        new_roster.append({"name": nm, "number": num, "stats": blank_stats()})

                    st.session_state.roster = new_roster
                    st.session_state.selected = 0 if new_roster else None
                    st.session_state.action_stack = []
                    st.success(f"Imported {len(new_roster)} players.")
            except Exception as e:
                st.error(f"Could not import CSV: {e}")

    with st.expander("Roster actions", expanded=False):
        if st.button("Reset all stats (keep roster)", use_container_width=True):
            for p in st.session_state.roster:
                p["stats"] = blank_stats()
            st.session_state.action_stack = []
            st.success("Stats reset.")

        if st.button("Clear roster", use_container_width=True):
            st.session_state.roster = []
            st.session_state.selected = None
            st.session_state.action_stack = []
            st.success("Roster cleared.")

# Main layout: selection + buttons + table
colA, colB = st.columns([1, 2], gap="large")

with colA:
    st.subheader("Select player")

    if not st.session_state.roster:
        st.info("Add players in the sidebar to start.")
    else:
        options = []
        for i, p in enumerate(st.session_state.roster):
            label = f"#{p['number']} {p['name']}".strip() if p["number"] else p["name"]
            options.append((i, label))

        # keep selection stable
        current_idx = st.session_state.selected if st.session_state.selected is not None else 0
        idx_list = [x[0] for x in options]
        if current_idx not in idx_list:
            current_idx = idx_list[0]

        selected_label = st.selectbox(
            "Player",
            options=[x[1] for x in options],
            index=idx_list.index(current_idx),
        )
        st.session_state.selected = options[[x[1] for x in options].index(selected_label)][0]

        # Remove selected player
        if st.button("Remove selected player", use_container_width=True):
            rm_idx = st.session_state.selected
            if rm_idx is not None:
                st.session_state.roster.pop(rm_idx)
                st.session_state.action_stack = []
                if len(st.session_state.roster) == 0:
                    st.session_state.selected = None
                else:
                    st.session_state.selected = min(rm_idx, len(st.session_state.roster) - 1)
                st.success("Player removed.")

    st.divider()
    st.subheader("Undo / Export")

    if st.button("Undo last action", use_container_width=True):
        undo_last()

    df = build_df()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download stats CSV",
        data=csv_bytes,
        file_name="game_stats.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=(len(st.session_state.roster) == 0),
    )

with colB:
    st.subheader("Stat buttons")

    if st.session_state.selected is None:
        st.info("Select a player to enable stat buttons.")
    else:
        p = st.session_state.roster[st.session_state.selected]
        st.caption(f"Logging for: **{('#'+p['number']+' ' if p['number'] else '')}{p['name']}**")

        # 3 columns of buttons
        bcols = st.columns(3)
        for i, (label, key, delta, implies) in enumerate(BUTTONS):
            with bcols[i % 3]:
                if st.button(label, use_container_width=True):
                    click_button(key, delta, implies)

    st.divider()
    st.subheader("Box score")

    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.session_state.selected is not None and st.session_state.roster:
        p = st.session_state.roster[st.session_state.selected]
        s = p["stats"]
        st.markdown("#### Selected player quick view")
        st.write({
            "PTS": points(s),
            "REB": s.get("REB", 0),
            "AST": s.get("AST", 0),
            "2PM/2PA": f"{s.get('2PM',0)}/{s.get('2PA',0)}",
            "3PM/3PA": f"{s.get('3PM',0)}/{s.get('3PA',0)}",
            "STL": s.get("STL", 0),
            "BLK": s.get("BLK", 0),
            "TOV": s.get("TOV", 0),
        })
