import streamlit as st
import pandas as pd
from datetime import date, datetime
from pathlib import Path

# -----------------------------------------
# Leagues
# -----------------------------------------

LEAGUES = [
    {"name": "Sophomore League", "slug": "soph"},
    {"name": "Junior League", "slug": "junior"},
    {"name": "Senior League", "slug": "senior"},
]

def get_league_by_name(name: str):
    for lg in LEAGUES:
        if lg["name"] == name:
            return lg
    return LEAGUES[-1]  # default to last (Senior)


# -----------------------------------------
# Stat Categories by Sport
# -----------------------------------------

SPORT_STAT_CATEGORIES = {
    "Basketball": [
        ("basket_points", "Points"),
        ("basket_assists", "Assists"),
        ("basket_rebounds", "Rebounds"),
    ],
    "Softball": [
        ("soft_hits", "Hits"),
        ("soft_doubles", "Doubles"),
        ("soft_home_runs", "Home Runs"),
    ],
    "Kickball": [
        ("kick_runs", "Runs"),
        ("kick_rbis", "RBIs"),
    ],
    "Hockey": [
        ("hockey_goals", "Goals"),
        ("hockey_assists", "Assists"),
    ],
    "Soccer": [
        ("soccer_goals", "Goals"),
        ("soccer_assists", "Assists"),
    ],
    "Euro": [
        ("euro_goals", "Goals"),
        ("euro_assists", "Assists"),
    ],
    "Speedball": [
        ("speed_points", "Points"),
        ("speed_assists", "Assists"),
    ],
    "Flag Football": [
        ("ff_touchdowns", "Touchdowns"),
        ("ff_catches", "Catches"),
        ("ff_interceptions", "Interceptions"),
    ],
    "Other": [
        ("points", "Points"),
        ("assists", "Assists"),
    ],
}

DEFAULT_SPORTS = list(SPORT_STAT_CATEGORIES.keys())
LEVELS = ["A", "B", "C", "D"]

# -----------------------------------------
# League point values by sport/level
# -----------------------------------------

GAME_POINT_VALUES = {
    "Basketball": {"A": 15, "B": 10, "C": 7, "D": 5},
    "Softball": {"A": 15, "B": 10, "C": 7, "D": 5},
    "Kickball": {"A": 10, "B": 7, "C": 5, "D": 3},
    "Hockey": {"A": 15, "B": 10, "C": 7, "D": 5},
    "Soccer": {"A": 15, "B": 10, "C": 7, "D": 5},
    "Euro": {"A": 12, "B": 9, "C": 6, "D": 4},
    "Speedball": {"A": 12, "B": 9, "C": 6, "D": 4},
    "Flag Football": {"A": 15, "B": 10, "C": 7, "D": 5},
    "Other": {"A": 10, "B": 7, "C": 5, "D": 3},
}
DEFAULT_GAME_POINTS = {"A": 10, "B": 7, "C": 5, "D": 3}


def get_game_points(sport: str, level: str) -> int:
    sport_map = GAME_POINT_VALUES.get(sport, {})
    return sport_map.get(level, DEFAULT_GAME_POINTS.get(level, 0))


# -----------------------------------------
# Paths – these will be set per league
# -----------------------------------------

ROSTER_FILE = Path("roster.csv")
TEAMS_FILE = Path("teams.csv")
GAMES_FILE = Path("games.csv")
STATS_FILE = Path("stats.csv")
HIGHLIGHTS_FILE = Path("highlights.csv")
VIDEOS_DIR = Path("highlight_videos")


def set_paths_for_league(slug: str):
    """
    Set global paths so that all data is stored per-league.
    soph_roster.csv, junior_games.csv, etc.
    """
    global ROSTER_FILE, TEAMS_FILE, GAMES_FILE, STATS_FILE, HIGHLIGHTS_FILE, VIDEOS_DIR
    ROSTER_FILE = Path(f"{slug}_roster.csv")
    TEAMS_FILE = Path(f"{slug}_teams.csv")
    GAMES_FILE = Path(f"{slug}_games.csv")
    STATS_FILE = Path(f"{slug}_stats.csv")
    HIGHLIGHTS_FILE = Path(f"{slug}_highlights.csv")
    VIDEOS_DIR = Path(f"{slug}_highlight_videos")


# -----------------------------------------
# Helpers to create empty dataframes
# -----------------------------------------

def new_games_df():
    return pd.DataFrame(columns=[
        "game_id", "date", "sport", "level", "team1", "team2", "score1", "score2"
    ])


def new_stats_df():
    return pd.DataFrame(columns=[
        "game_id", "sport", "team_name", "player_id", "first_name",
        "last_name", "bunk", "stat_type", "value"
    ])


def new_highlights_df():
    return pd.DataFrame(columns=[
        "highlight_id", "date", "title", "description", "video_path",
        "sport", "level", "team1", "team2", "featured"
    ])


def load_csv(path: Path, columns):
    if path.exists():
        df = pd.read_csv(path)
        if "date" in df.columns:
            try:
                df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            except Exception:
                pass
        return df
    else:
        return pd.DataFrame(columns=columns)


def save_csv(path: Path, df: pd.DataFrame):
    df.to_csv(path, index=False)


# -----------------------------------------
# Session State Initialization (per league)
# -----------------------------------------

def init_state():
    # Make sure video folder exists
    VIDEOS_DIR.mkdir(exist_ok=True)

    # Roster
    if "roster" not in st.session_state:
        if ROSTER_FILE.exists():
            df = pd.read_csv(ROSTER_FILE)
            df.columns = (
                df.columns
                .astype(str)
                .str.replace("\ufeff", "", regex=False)
                .str.strip()
                .str.lower()
            )
            st.session_state.roster = df
        else:
            st.session_state.roster = None

    # Teams
    if "teams" not in st.session_state:
        if TEAMS_FILE.exists():
            st.session_state.teams = pd.read_csv(TEAMS_FILE)
        else:
            st.session_state.teams = None

    # Games
    if "games" not in st.session_state:
        st.session_state.games = load_csv(GAMES_FILE, new_games_df().columns)
        if "sport" not in st.session_state.games.columns:
            st.session_state.games["sport"] = "Other"
        if "level" not in st.session_state.games.columns:
            st.session_state.games["level"] = "A"

    # Stats
    if "stats" not in st.session_state:
        st.session_state.stats = load_csv(STATS_FILE, new_stats_df().columns)
        if "sport" not in st.session_state.stats.columns:
            st.session_state.stats["sport"] = "Other"

    # Highlights
    if "highlights" not in st.session_state:
        st.session_state.highlights = load_csv(HIGHLIGHTS_FILE, new_highlights_df().columns)
        if "featured" not in st.session_state.highlights.columns:
            st.session_state.highlights["featured"] = False
        if "video_path" not in st.session_state.highlights.columns:
            st.session_state.highlights["video_path"] = ""


# -----------------------------------------
# Core Calculations
# -----------------------------------------

def compute_standings():
    games = st.session_state.games
    teams = st.session_state.teams

    if teams is None or teams.empty:
        return pd.DataFrame()

    standings = pd.DataFrame({
        "team_name": teams["team_name"].unique()
    })
    standings["gp"] = 0
    standings["w"] = 0
    standings["l"] = 0
    standings["t"] = 0
    standings["pts"] = 0
    standings["points_for"] = 0
    standings["points_against"] = 0
    standings["diff"] = 0

    if games.empty:
        return standings

    for _, g in games.iterrows():
        team1 = g["team1"]
        team2 = g["team2"]
        s1 = int(g["score1"])
        s2 = int(g["score2"])
        sport = g.get("sport", "Other")
        level = g.get("level", "A")
        win_points = get_game_points(sport, level)

        for team_name, scored, allowed in [(team1, s1, s2), (team2, s2, s1)]:
            idx = standings["team_name"] == team_name
            standings.loc[idx, "gp"] += 1
            standings.loc[idx, "points_for"] += scored
            standings.loc[idx, "points_against"] += allowed

        if s1 > s2:
            standings.loc[standings["team_name"] == team1, "w"] += 1
            standings.loc[standings["team_name"] == team2, "l"] += 1
            standings.loc[standings["team_name"] == team1, "pts"] += win_points
        elif s2 > s1:
            standings.loc[standings["team_name"] == team2, "w"] += 1
            standings.loc[standings["team_name"] == team1, "l"] += 1
            standings.loc[standings["team_name"] == team2, "pts"] += win_points
        else:
            half = win_points // 2
            standings.loc[standings["team_name"] == team1, "t"] += 1
            standings.loc[standings["team_name"] == team2, "t"] += 1
            standings.loc[standings["team_name"] == team1, "pts"] += half
            standings.loc[standings["team_name"] == team2, "pts"] += half

    standings["diff"] = standings["points_for"] - standings["points_against"]

    standings = standings.sort_values(
        by=["pts", "diff", "points_for", "team_name"],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)

    return standings


def compute_leaderboard(sport: str, stat_type: str):
    stats = st.session_state.stats
    if stats.empty:
        return pd.DataFrame()

    df = stats[(stats["sport"] == sport) & (stats["stat_type"] == stat_type)]
    if df.empty:
        return pd.DataFrame()

    agg = df.groupby(
        ["player_id", "first_name", "last_name", "bunk", "team_name"],
        as_index=False
    )["value"].sum()

    agg = agg.sort_values(by="value", ascending=False).reset_index(drop=True)
    agg["rank"] = agg.index + 1
    return agg[["rank", "first_name", "last_name", "bunk", "team_name", "value"]]


# -----------------------------------------
# Pages (all operate within current league)
# -----------------------------------------

def page_setup():
    st.header("Step 1: Upload League Roster CSV")

    st.write(
        """
        Upload a single CSV with **all kids** in this league (sophomores OR juniors OR seniors),
        including which of the 4 league teams each kid is on.
        """
    )

    st.markdown("**Required columns:** `player_id, first_name, last_name, team_name, bunk`")

    example = pd.DataFrame({
        "player_id": [1, 2, 3, 4],
        "first_name": ["Alex", "Ben", "Charlie", "Dylan"],
        "last_name": ["R", "S", "T", "U"],
        "team_name": ["Red", "Red", "Blue", "Blue"],
        "bunk": ["1", "1", "2", "2"],
    })
    st.caption("Example format:")
    st.dataframe(example, use_container_width=True)

    file = st.file_uploader("Upload league_roster.csv", type=["csv"])
    if file is not None:
        try:
            df = pd.read_csv(file)
            df.columns = (
                df.columns
                .astype(str)
                .str.replace("\ufeff", "", regex=False)
                .str.strip()
                .str.lower()
            )
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            return

        required_cols = {"player_id", "first_name", "last_name", "team_name", "bunk"}
        if not required_cols.issubset(df.columns):
            st.error(
                "CSV must contain columns: player_id, first_name, last_name, team_name, bunk. "
                f"Current columns are: {list(df.columns)}"
            )
            return

        st.session_state.roster = df
        teams_df = df[["team_name"]].drop_duplicates().reset_index(drop=True)
        st.session_state.teams = teams_df

        df.to_csv(ROSTER_FILE, index=False)
        teams_df.to_csv(TEAMS_FILE, index=False)

        st.success("Roster loaded and saved successfully!")

    if st.session_state.roster is not None:
        st.subheader("Current Roster")
        st.dataframe(st.session_state.roster, use_container_width=True)

        st.subheader("Teams")
        st.dataframe(st.session_state.teams, use_container_width=True)


def page_enter_scores_and_stats():
    st.header("Step 2: Enter Game Scores & Player Stats")

    if st.session_state.roster is None or st.session_state.teams is None:
        st.warning("You need to upload a roster first on the 'Setup' page.")
        return

    teams_list = st.session_state.teams["team_name"].tolist()
    sports_list = DEFAULT_SPORTS

    # Add new game
    st.subheader("Add New Game")

    col_date, col_sport, col_level = st.columns(3)
    with col_date:
        game_date = st.date_input("Game Date", value=date.today())
    with col_sport:
        sport = st.selectbox("Sport", sports_list, index=0)
    with col_level:
        level = st.selectbox("Level (A/B/C/D)", LEVELS, index=0)

    col_team1, col_team2 = st.columns(2)
    with col_team1:
        team1 = st.selectbox("Team 1", teams_list, key="team1_select")
    with col_team2:
        team2 = st.selectbox("Team 2", teams_list, key="team2_select")

    if team1 == team2:
        st.error("Team 1 and Team 2 must be different.")
    else:
        col_score1, col_score2 = st.columns(2)
        with col_score1:
            score1 = st.number_input(f"{team1} Score", min_value=0, step=1, value=0)
        with col_score2:
            score2 = st.number_input(f"{team2} Score", min_value=0, step=1, value=0)

        if st.button("Save Game"):
            game_id = f"G{len(st.session_state.games) + 1}"
            new_game = pd.DataFrame([{
                "game_id": game_id,
                "date": pd.to_datetime(game_date).date(),
                "sport": sport,
                "level": level,
                "team1": team1,
                "team2": team2,
                "score1": score1,
                "score2": score2,
            }])
            st.session_state.games = pd.concat(
                [st.session_state.games, new_game], ignore_index=True
            )
            save_csv(GAMES_FILE, st.session_state.games)

            pts = get_game_points(sport, level)
            st.success(
                f"Saved game {game_id}: {sport} ({level}) – {team1} {score1}-{score2} {team2} "
                f"(win worth {pts} league pts)."
            )

    st.markdown("---")

    # Enter / edit stats
    st.subheader("Enter / Edit Stats for an Existing Game")

    games = st.session_state.games
    if games.empty:
        st.info("No games yet. Add a game above first.")
        return

    games_sorted = games.sort_values("date")
    game_options = {}
    for _, g in games_sorted.iterrows():
        d = g["date"]
        label = f"{g['game_id']} – {d} – {g['sport']} ({g['level']}) – {g['team1']} vs {g['team2']}"
        game_options[label] = g["game_id"]

    selected_label = st.selectbox("Choose a game to enter stats for", list(game_options.keys()))
    selected_game_id = game_options[selected_label]
    game_row = games[games["game_id"] == selected_game_id].iloc[0]

    game_sport = game_row["sport"]
    team1 = game_row["team1"]
    team2 = game_row["team2"]

    st.caption(f"Game: {selected_game_id} • {game_sport} • {team1} vs {team2}")

    categories = SPORT_STAT_CATEGORIES.get(game_sport, SPORT_STAT_CATEGORIES["Other"])

    roster = st.session_state.roster
    home_roster = roster[roster["team_name"] == team1]
    away_roster = roster[roster["team_name"] == team2]

    stats_df = st.session_state.stats
    existing_stats_game = stats_df[stats_df["game_id"] == selected_game_id]

    existing_lookup = {}
    for _, row in existing_stats_game.iterrows():
        key = (row["player_id"], row["stat_type"])
        existing_lookup[key] = row["value"]

    st.caption("Enter stat totals for THIS game only. The app will handle season totals.")

    # Stats for team1
    st.markdown("### Stats for " + team1)
    with st.expander(f"{team1} Players", expanded=True):
        for _, p in home_roster.iterrows():
            player_key_base = f"{selected_game_id}_{team1}_{p['player_id']}"
            st.markdown(f"**{p['first_name']} {p['last_name']} (Bunk {p['bunk']})**")
            cols = st.columns(len(categories))
            for (stat_code, stat_label), col in zip(categories, cols):
                default_val = existing_lookup.get((p["player_id"], stat_code), 0)
                with col:
                    st.number_input(
                        stat_label,
                        min_value=0,
                        step=1,
                        value=int(default_val),
                        key=f"{player_key_base}_{stat_code}",
                    )

    # Stats for team2
    st.markdown("### Stats for " + team2)
    with st.expander(f"{team2} Players", expanded=True):
        for _, p in away_roster.iterrows():
            player_key_base = f"{selected_game_id}_{team2}_{p['player_id']}"
            st.markdown(f"**{p['first_name']} {p['last_name']} (Bunk {p['bunk']})**")
            cols = st.columns(len(categories))
            for (stat_code, stat_label), col in zip(categories, cols):
                default_val = existing_lookup.get((p["player_id"], stat_code), 0)
                with col:
                    st.number_input(
                        stat_label,
                        min_value=0,
                        step=1,
                        value=int(default_val),
                        key=f"{player_key_base}_{stat_code}",
                    )

    if st.button("Save Stats for This Game"):
        st.session_state.stats = st.session_state.stats[
            st.session_state.stats["game_id"] != selected_game_id
        ]

        new_stats_rows = []

        def collect_stats_for_team(team_name, team_roster):
            for _, p in team_roster.iterrows():
                player_key_base = f"{selected_game_id}_{team_name}_{p['player_id']}"
                for (stat_code, _) in categories:
                    widget_key = f"{player_key_base}_{stat_code}"
                    val = st.session_state.get(widget_key, 0)
                    if val and int(val) > 0:
                        new_stats_rows.append({
                            "game_id": selected_game_id,
                            "sport": game_sport,
                            "team_name": team_name,
                            "player_id": p["player_id"],
                            "first_name": p["first_name"],
                            "last_name": p["last_name"],
                            "bunk": p["bunk"],
                            "stat_type": stat_code,
                            "value": int(val),
                        })

        collect_stats_for_team(team1, home_roster)
        collect_stats_for_team(team2, away_roster)

        if new_stats_rows:
            new_stats_df = pd.DataFrame(new_stats_rows)
            st.session_state.stats = pd.concat(
                [st.session_state.stats, new_stats_df], ignore_index=True
            )
            save_csv(STATS_FILE, st.session_state.stats)

        st.success(f"Saved stats for game {selected_game_id}.")

    st.subheader("Games Entered So Far")
    if st.session_state.games.empty:
        st.info("No games yet.")
    else:
        st.dataframe(st.session_state.games, use_container_width=True)


def page_standings():
    st.header("Standings")

    if st.session_state.roster is None or st.session_state.teams is None:
        st.warning("You need to upload a roster first on the 'Setup' page.")
        return

    standings = compute_standings()
    if standings.empty:
        st.info("No games yet. Enter some results first.")
        return

    display = standings.copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    display = display.rename(columns={
        "team_name": "Team",
        "gp": "GP",
        "w": "W",
        "l": "L",
        "t": "T",
        "pts": "Pts",
        "points_for": "PF",
        "points_against": "PA",
        "diff": "Diff",
    })

    st.dataframe(display, use_container_width=True)


def page_leaderboards():
    st.header("Leaderboards")

    if st.session_state.roster is None or st.session_state.teams is None:
        st.warning("You need to upload a roster first on the 'Setup' page.")
        return

    stats = st.session_state.stats
    if stats.empty:
        st.info("No stats yet. Enter some game stats first.")
        return

    sports_with_stats = sorted(stats["sport"].unique().tolist())
    selected_sport = st.selectbox("Sport", sports_with_stats)

    categories = SPORT_STAT_CATEGORIES.get(selected_sport, SPORT_STAT_CATEGORIES["Other"])
    label_to_code = {label: code for code, label in categories}
    stat_label = st.selectbox("Stat Category", list(label_to_code.keys()))
    stat_code = label_to_code[stat_label]

    lb = compute_leaderboard(selected_sport, stat_code)
    if lb.empty:
        st.info(f"No stats recorded yet for {selected_sport} – {stat_label}.")
        return

    display = lb.rename(columns={
        "first_name": "First",
        "last_name": "Last",
        "bunk": "Bunk",
        "team_name": "Team",
        "value": stat_label,
    })

    top_row = display.iloc[0]
    st.success(
        f"🏆 Current leader in {selected_sport} – {stat_label}: "
        f"{top_row['First']} {top_row['Last']} ({top_row['Team']}), {stat_label}: {top_row[stat_label]}"
    )

    st.subheader(f"Top {len(display)} – {selected_sport} – {stat_label}")
    st.dataframe(display, use_container_width=True)


def page_highlights():
    st.header("Highlights & Videos")

    if st.session_state.roster is None or st.session_state.teams is None:
        st.info("You can still add highlights even if no roster is loaded, but teams list will be empty.")
        teams_list = []
    else:
        teams_list = st.session_state.teams["team_name"].tolist()

    st.write("Upload highlight videos from that day for the mess hall monitor.")

    col_form, col_list = st.columns([2, 3])

    # Add highlight form
    with col_form:
        st.subheader("Add New Highlight")
        with st.form("add_highlight_form", clear_on_submit=True):
            h_date = st.date_input("Date", value=date.today())
            title = st.text_input("Title (e.g., 'A Basketball: Red vs Blue')")
            video_file = st.file_uploader(
                "Upload highlight video",
                type=["mp4", "mov", "avi", "mkv"],
            )
            description = st.text_area("Description (optional)", height=80)

            sport = st.selectbox("Sport", DEFAULT_SPORTS + ["Other"])
            level = st.selectbox("Level", LEVELS + ["N/A"], index=0)

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                team1 = st.selectbox("Team 1 (optional)", [""] + teams_list)
            with col_t2:
                team2 = st.selectbox("Team 2 (optional)", [""] + teams_list)

            featured = st.checkbox("Feature this on today's display board", value=True)

            submitted = st.form_submit_button("Save Highlight")

            if submitted:
                if not title.strip():
                    st.error("Please enter a title.")
                elif video_file is None:
                    st.error("Please upload a video file.")
                else:
                    hl_df = st.session_state.highlights
                    next_id = 1 if hl_df.empty else int(hl_df["highlight_id"].max()) + 1

                    VIDEOS_DIR.mkdir(exist_ok=True)
                    safe_name = f"highlight_{next_id}_{video_file.name}"
                    video_path = VIDEOS_DIR / safe_name
                    with open(video_path, "wb") as f:
                        f.write(video_file.getbuffer())

                    new_row = {
                        "highlight_id": next_id,
                        "date": h_date,
                        "title": title.strip(),
                        "description": description.strip(),
                        "video_path": str(video_path),
                        "sport": sport,
                        "level": level,
                        "team1": team1 or "",
                        "team2": team2 or "",
                        "featured": bool(featured),
                    }

                    st.session_state.highlights = pd.concat(
                        [hl_df, pd.DataFrame([new_row])], ignore_index=True
                    )
                    save_csv(HIGHLIGHTS_FILE, st.session_state.highlights)
                    st.success("Highlight saved!")

    # Highlight list & preview
    with col_list:
        st.subheader("Existing Highlights")

        hl_df = st.session_state.highlights
        if hl_df.empty:
            st.info("No highlights yet.")
        else:
            display = hl_df.copy()
            st.dataframe(
                display[["highlight_id", "date", "title", "sport", "level", "featured"]],
                use_container_width=True,
            )

            st.markdown("---")
            st.subheader("Preview a Highlight")
            ids = display["highlight_id"].tolist()
            id_to_title = {int(r["highlight_id"]): r["title"] for _, r in display.iterrows()}
            if ids:
                selected_id = st.selectbox(
                    "Choose a highlight to preview",
                    ids,
                    format_func=lambda x: f"{x} – {id_to_title.get(x, '')}"
                )
                row = display[display["highlight_id"] == selected_id].iloc[0]
                st.markdown(f"**{row['title']}**")
                if isinstance(row["date"], (datetime, date)):
                    st.caption(str(row["date"]))
                elif isinstance(row["date"], str):
                    st.caption(row["date"])
                if row.get("description"):
                    st.write(row["description"])
                vp = row.get("video_path", "")
                if vp and Path(vp).exists():
                    st.video(vp)
                else:
                    st.warning("Video file not found. It may have been moved or deleted.")


def page_display_board(current_league_name: str):
    st.header(f"Mess Hall Display – {current_league_name}")

    standings = compute_standings()
    stats = st.session_state.stats
    hl_df = st.session_state.highlights

    mode = st.radio(
        "Display mode",
        [
            "Standings & One Stat Leaderboard",
            "Highlights Reel (Today/Featured)",
            "All Stat Leaders (All Sports)",
        ],
    )

    # Mode 1: Standings + one stat
    if mode == "Standings & One Stat Leaderboard":
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Team Standings")
            if standings.empty:
                st.info("No games yet.")
            else:
                display = standings.copy()
                display.insert(0, "Rank", range(1, len(display) + 1))
                display = display.rename(columns={
                    "team_name": "Team",
                    "gp": "GP",
                    "w": "W",
                    "l": "L",
                    "t": "T",
                    "pts": "Pts",
                    "points_for": "PF",
                    "points_against": "PA",
                    "diff": "Diff",
                })
                st.dataframe(display, use_container_width=True)

        with col2:
            st.subheader("Stat Leaders")
            if stats.empty:
                st.info("No stats yet.")
            else:
                sports_with_stats = sorted(stats["sport"].unique().tolist())
                selected_sport = st.selectbox("Sport", sports_with_stats, key="display_sport")
                categories = SPORT_STAT_CATEGORIES.get(selected_sport, SPORT_STAT_CATEGORIES["Other"])
                label_to_code = {label: code for code, label in categories}
                stat_label = st.selectbox("Stat", list(label_to_code.keys()), key="display_stat")
                stat_code = label_to_code[stat_label]

                lb = compute_leaderboard(selected_sport, stat_code)
                if lb.empty:
                    st.info(f"No stats yet for {selected_sport} – {stat_label}.")
                else:
                    top_n = lb.head(10)
                    display_lb = top_n.rename(columns={
                        "first_name": "First",
                        "last_name": "Last",
                        "bunk": "Bunk",
                        "team_name": "Team",
                        "value": stat_label,
                    })
                    st.dataframe(display_lb, use_container_width=True)

        st.markdown("---")
        st.caption("Tip: Put your browser in full-screen mode for the mess hall TV.")

    # Mode 2: Highlights reel
    elif mode == "Highlights Reel (Today/Featured)":
        st.subheader("Highlights Reel")

        if hl_df.empty:
            st.info("No highlights yet.")
        else:
            today_str = date.today().isoformat()

            def is_today(val):
                if isinstance(val, str):
                    return val.startswith(today_str)
                if isinstance(val, (datetime, date)):
                    return val == date.today()
                return False

            today_highlights = hl_df[hl_df["date"].apply(is_today) | hl_df["featured"].astype(bool)]
            if today_highlights.empty:
                st.info("No highlights marked for today yet.")
            else:
                st.caption("Scroll or fullscreen – videos are stacked, ready to play back-to-back.")
                for _, row in today_highlights.sort_values("date").iterrows():
                    st.markdown(f"**{row['title']}** ({row['sport']} {row['level']})")
                    if row.get("description"):
                        st.write(row["description"])
                    vp = row.get("video_path", "")
                    if vp and Path(vp).exists():
                        st.video(vp)
                    else:
                        st.warning("Video file not found.")
                    st.markdown("---")

    # Mode 3: All stat leaders all sports
    elif mode == "All Stat Leaders (All Sports)":
        st.subheader("Stat Leaders – All Sports")

        if stats.empty:
            st.info("No stats yet.")
            return

        sports_with_stats = sorted(stats["sport"].unique().tolist())

        for sport in sports_with_stats:
            st.markdown(f"### {sport}")
            categories = SPORT_STAT_CATEGORIES.get(sport, SPORT_STAT_CATEGORIES["Other"])
            main_code, main_label = categories[0]

            lb = compute_leaderboard(sport, main_code)
            if lb.empty:
                st.info(f"No stats yet for {sport}.")
                continue

            top_n = lb.head(10)
            display_lb = top_n.rename(columns={
                "first_name": "First",
                "last_name": "Last",
                "bunk": "Bunk",
                "team_name": "Team",
                "value": main_label,
            })
            st.dataframe(display_lb, use_container_width=True)


def page_admin():
    st.header("Admin / Clear Data (This League Only)")

    roster_rows = 0 if st.session_state.roster is None else len(st.session_state.roster)
    team_rows = 0 if st.session_state.teams is None else len(st.session_state.teams)
    game_rows = len(st.session_state.games)
    stat_rows = len(st.session_state.stats)
    hl_rows = len(st.session_state.highlights)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Roster rows", roster_rows)
        st.metric("Teams", team_rows)
    with col2:
        st.metric("Games", game_rows)
        st.metric("Stat entries", stat_rows)
    with col3:
        st.metric("Highlights", hl_rows)

    st.markdown("---")

    # Delete selected games
    st.subheader("Delete Selected Games (and Their Stats)")

    games = st.session_state.games
    if games.empty:
        st.info("No games stored.")
    else:
        games_sorted = games.sort_values("date")
        labels = []
        ids = []
        for _, g in games_sorted.iterrows():
            d = g["date"]
            label = f"{g['game_id']} – {d} – {g['sport']} ({g['level']}) – {g['team1']} vs {g['team2']}"
            labels.append(label)
            ids.append(g["game_id"])

        selected_labels = st.multiselect("Select games to delete", labels)
        label_to_id = dict(zip(labels, ids))
        selected_ids = [label_to_id[l] for l in selected_labels]

        if selected_ids and st.button("Delete Selected Games"):
            st.session_state.games = st.session_state.games[
                ~st.session_state.games["game_id"].isin(selected_ids)
            ]
            st.session_state.stats = st.session_state.stats[
                ~st.session_state.stats["game_id"].isin(selected_ids)
            ]
            save_csv(GAMES_FILE, st.session_state.games)
            save_csv(STATS_FILE, st.session_state.stats)
            st.success(f"Deleted {len(selected_ids)} game(s) and their stats.")

    st.markdown("---")

    # Delete ALL games & stats
    st.subheader("Delete ALL Games & Stats (keep roster & highlights)")
    st.warning("This will remove every game and every stat entry for this league, but keep your roster, teams, and highlights.")
    confirm_all_games = st.checkbox("I understand, delete ALL games & stats")
    if confirm_all_games and st.button("Delete ALL Games & Stats"):
        st.session_state.games = new_games_df()
        st.session_state.stats = new_stats_df()
        save_csv(GAMES_FILE, st.session_state.games)
        save_csv(STATS_FILE, st.session_state.stats)
        st.success("All games and stats have been deleted.")

    st.markdown("---")

    # Delete ALL highlights
    st.subheader("Delete ALL Highlights (this league)")
    confirm_hl = st.checkbox("I understand, delete ALL highlights")
    if confirm_hl and st.button("Delete ALL Highlights"):
        st.session_state.highlights = new_highlights_df()
        save_csv(HIGHLIGHTS_FILE, st.session_state.highlights)
        st.success("All highlights deleted.")

    st.markdown("---")

    # Full reset for this league
    st.subheader("Delete EVERYTHING for This League (Roster, Teams, Games, Stats, Highlights)")
    st.error(
        "This will completely reset THIS league only. "
        "You will need to upload a new roster and re-enter all games, stats, and highlights."
    )
    confirm_everything = st.checkbox("I REALLY understand, delete EVERYTHING for this league")
    if confirm_everything and st.button("Full Reset: Clear All Data for This League"):
        st.session_state.roster = None
        st.session_state.teams = None
        st.session_state.games = new_games_df()
        st.session_state.stats = new_stats_df()
        st.session_state.highlights = new_highlights_df()

        # Delete league-specific files
        for path in [ROSTER_FILE, TEAMS_FILE, GAMES_FILE, STATS_FILE, HIGHLIGHTS_FILE]:
            if path.exists():
                path.unlink()

        # Clear videos for this league
        if VIDEOS_DIR.exists():
            for p in VIDEOS_DIR.iterdir():
                if p.is_file():
                    p.unlink()

        st.success("All data cleared for this league. Go to Setup to upload a fresh roster.")


# -----------------------------------------
# Main
# -----------------------------------------

def main():
    st.set_page_config(page_title="Crest League Manager", layout="wide")

    # League selector in sidebar (default to Senior League)
    st.sidebar.title("Crest League Manager")
    league_names = [lg["name"] for lg in LEAGUES]
    default_index = next(i for i, lg in enumerate(LEAGUES) if lg["slug"] == "senior")
    selected_league_name = st.sidebar.selectbox("League", league_names, index=default_index)
    league = get_league_by_name(selected_league_name)

    # Set file paths for this league
    set_paths_for_league(league["slug"])

    # Bauercrest logo in sidebar if present
    logo_path = Path("logo-header-2.png")
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_column_width=True)

    st.sidebar.caption(f"Managing data for: **{selected_league_name}**")

    # Initialize state for this league
    init_state()

    page = st.sidebar.radio(
        "Go to",
        [
            "Setup",
            "Enter Scores & Stats",
            "Standings",
            "Leaderboards",
            "Highlights",
            "Display Board",
            "Admin / Clear Data",
        ],
    )

    if page == "Setup":
        page_setup()
    elif page == "Enter Scores & Stats":
        page_enter_scores_and_stats()
    elif page == "Standings":
        page_standings()
    elif page == "Leaderboards":
        page_leaderboards()
    elif page == "Highlights":
        page_highlights()
    elif page == "Display Board":
        page_display_board(selected_league_name)
    elif page == "Admin / Clear Data":
        page_admin()


if __name__ == "__main__":
    main()
