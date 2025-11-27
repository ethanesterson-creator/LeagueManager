import streamlit as st
import pandas as pd
from datetime import date

# -----------------------------------------
# Stat Categories by Sport
# -----------------------------------------

# You can edit this dictionary to add/remove stats.
# Keys = Sport names used when you create a game.
# Values = list of (stat_code, nice_label).
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
    "Hockey": [
        ("hockey_goals", "Goals"),
        ("hockey_assists", "Assists"),
    ],
    "Soccer": [
        ("soccer_goals", "Goals"),
        ("soccer_assists", "Assists"),
    ],
    "Flag Football": [
        ("ff_touchdowns", "Touchdowns"),
        ("ff_catches", "Catches"),
        ("ff_interceptions", "Interceptions"),
    ],
    # Fallback / generic stats if you want simple stuff
    "Other": [
        ("points", "Points"),
        ("assists", "Assists"),
    ],
}

DEFAULT_SPORTS = list(SPORT_STAT_CATEGORIES.keys())


# -----------------------------------------
# Helpers to create empty dataframes
# -----------------------------------------

def new_games_df():
    return pd.DataFrame(columns=[
        "game_id", "date", "sport", "team1", "team2", "score1", "score2"
    ])


def new_stats_df():
    return pd.DataFrame(columns=[
        "game_id", "sport", "team_name", "player_id", "first_name",
        "last_name", "bunk", "stat_type", "value"
    ])


# -----------------------------------------
# Session State Initialization
# -----------------------------------------

def init_state():
    if "roster" not in st.session_state:
        st.session_state.roster = None  # roster DataFrame
    if "teams" not in st.session_state:
        st.session_state.teams = None   # DataFrame of unique teams

    if "games" not in st.session_state:
        st.session_state.games = new_games_df()
    else:
        # Backwards compatibility: make sure all columns exist
        if "sport" not in st.session_state.games.columns:
            st.session_state.games["sport"] = "Other"

    if "stats" not in st.session_state:
        st.session_state.stats = new_stats_df()
    else:
        if "sport" not in st.session_state.stats.columns:
            st.session_state.stats["sport"] = "Other"

    if "points_for_win" not in st.session_state:
        st.session_state.points_for_win = 2
    if "points_for_tie" not in st.session_state:
        st.session_state.points_for_tie = 1
    if "points_for_loss" not in st.session_state:
        st.session_state.points_for_loss = 0


# -----------------------------------------
# Core Calculations
# -----------------------------------------

def compute_standings():
    """
    Compute standings table from st.session_state.games
    Using:
    - 2 pts for win (default)
    - 1 pt for tie
    - 0 pts for loss
    """
    games = st.session_state.games
    teams = st.session_state.teams

    if teams is None or teams.empty:
        return pd.DataFrame()

    # Build initial standings for all teams
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

        # games played, points for / against
        for team_name, scored, allowed in [(team1, s1, s2), (team2, s2, s1)]:
            idx = standings["team_name"] == team_name
            standings.loc[idx, "gp"] += 1
            standings.loc[idx, "points_for"] += scored
            standings.loc[idx, "points_against"] += allowed

        # result
        if s1 > s2:
            # team1 win
            standings.loc[standings["team_name"] == team1, "w"] += 1
            standings.loc[standings["team_name"] == team2, "l"] += 1
            standings.loc[standings["team_name"] == team1, "pts"] += st.session_state.points_for_win
            standings.loc[standings["team_name"] == team2, "pts"] += st.session_state.points_for_loss
        elif s2 > s1:
            # team2 win
            standings.loc[standings["team_name"] == team2, "w"] += 1
            standings.loc[standings["team_name"] == team1, "l"] += 1
            standings.loc[standings["team_name"] == team2, "pts"] += st.session_state.points_for_win
            standings.loc[standings["team_name"] == team1, "pts"] += st.session_state.points_for_loss
        else:
            # tie
            standings.loc[standings["team_name"] == team1, "t"] += 1
            standings.loc[standings["team_name"] == team2, "t"] += 1
            standings.loc[standings["team_name"] == team1, "pts"] += st.session_state.points_for_tie
            standings.loc[standings["team_name"] == team2, "pts"] += st.session_state.points_for_tie

    standings["diff"] = standings["points_for"] - standings["points_against"]

    standings = standings.sort_values(
        by=["pts", "diff", "points_for", "team_name"],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)

    return standings


def compute_leaderboard(sport: str, stat_type: str):
    """
    Aggregates stats by player for a given sport and stat_type
    (e.g. sport="Basketball", stat_type="basket_points").
    """
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
# Pages
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
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            return

        required_cols = {"player_id", "first_name", "last_name", "team_name", "bunk"}
        if not required_cols.issubset(df.columns):
            st.error(f"CSV must contain columns: {', '.join(required_cols)}")
            return

        if df["team_name"].nunique() != 4:
            st.warning(
                f"CSV currently has {df['team_name'].nunique()} unique team_name values. "
                "You probably want exactly 4 league teams."
            )

        st.session_state.roster = df
        st.session_state.teams = df[["team_name"]].drop_duplicates().reset_index(drop=True)
        st.success("Roster loaded successfully!")

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

    # -------------------------
    # Section A: Add a new game
    # -------------------------
    st.subheader("Add New Game")

    col_date, col_sport = st.columns(2)
    with col_date:
        game_date = st.date_input("Game Date", value=date.today())
    with col_sport:
        sport = st.selectbox("Sport", sports_list, index=0)

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
                "date": pd.to_datetime(game_date),
                "sport": sport,
                "team1": team1,
                "team2": team2,
                "score1": score1,
                "score2": score2,
            }])
            st.session_state.games = pd.concat(
                [st.session_state.games, new_game], ignore_index=True
            )
            st.success(f"Saved game {game_id}: {sport} – {team1} {score1}-{score2} {team2}")

    st.markdown("---")

    # ------------------------------------------
    # Section B: Enter / Edit stats for a game
    # ------------------------------------------
    st.subheader("Enter / Edit Stats for an Existing Game")

    games = st.session_state.games
    if games.empty:
        st.info("No games yet. Add a game above first.")
        return

    # Sort games by date
    games_sorted = games.sort_values("date")
    game_options = {}
    for _, g in games_sorted.iterrows():
        d = g["date"].date() if isinstance(g["date"], pd.Timestamp) else g["date"]
        label = f"{g['game_id']} – {d} – {g['sport']} – {g['team1']} vs {g['team2']}"
        game_options[label] = g["game_id"]

    selected_label = st.selectbox("Choose a game to enter stats for", list(game_options.keys()))
    selected_game_id = game_options[selected_label]
    game_row = games[games["game_id"] == selected_game_id].iloc[0]

    game_sport = game_row["sport"]
    team1 = game_row["team1"]
    team2 = game_row["team2"]

    st.caption(f"Game: {selected_game_id} • {game_sport} • {team1} vs {team2}")

    # Get stat categories for this sport
    categories = SPORT_STAT_CATEGORIES.get(game_sport, SPORT_STAT_CATEGORIES["Other"])

    roster = st.session_state.roster
    home_roster = roster[roster["team_name"] == team1]
    away_roster = roster[roster["team_name"] == team2]

    # Load existing stats for this game to pre-fill values
    stats_df = st.session_state.stats
    existing_stats_game = stats_df[stats_df["game_id"] == selected_game_id]

    # Build lookup: (player_id, stat_type) -> value
    existing_lookup = {}
    for _, row in existing_stats_game.iterrows():
        key = (row["player_id"], row["stat_type"])
        existing_lookup[key] = row["value"]

    st.caption("Enter stat totals for THIS game only. The app will handle season totals.")

    # Player stat inputs
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
        # Remove any existing stats rows for this game
        st.session_state.stats = st.session_state.stats[
            st.session_state.stats["game_id"] != selected_game_id
        ]

        new_stats_rows = []

        # Helper to collect values from the widgets
        def collect_stats_for_team(team_name, team_roster):
            for _, p in team_roster.iterrows():
                player_key_base = f"{selected_game_id}_{team_name}_{p['player_id']}"
                for (stat_code, stat_label) in categories:
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

        st.success(f"Saved stats for game {selected_game_id}.")

    st.subheader("Games Entered So Far")
    if st.session_state.games.empty:
        st.info("No games yet.")
    else:
        display_games = st.session_state.games.copy()
        if not display_games.empty and isinstance(display_games["date"].iloc[0], pd.Timestamp):
            display_games["date"] = display_games["date"].dt.date
        st.dataframe(display_games, use_container_width=True)


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

    with st.expander("Points Settings"):
        st.session_state.points_for_win = st.number_input(
            "Points for Win", min_value=0, max_value=10,
            value=st.session_state.points_for_win,
        )
        st.session_state.points_for_tie = st.number_input(
            "Points for Tie", min_value=0, max_value=10,
            value=st.session_state.points_for_tie,
        )
        st.session_state.points_for_loss = st.number_input(
            "Points for Loss", min_value=0, max_value=10,
            value=st.session_state.points_for_loss,
        )
        st.caption("Changing this will update standings next time they are calculated.")


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

    # Figure out which stat codes are relevant for this sport
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

    st.subheader(f"Top {len(display)} – {selected_sport} – {stat_label}")
    st.dataframe(display, use_container_width=True)


def page_admin():
    st.header("Admin / Clear Data")

    st.write("Use this page to clear out test rosters, games, and stats.")

    # Quick status
    roster_rows = 0 if st.session_state.roster is None else len(st.session_state.roster)
    team_rows = 0 if st.session_state.teams is None else len(st.session_state.teams)
    game_rows = len(st.session_state.games)
    stat_rows = len(st.session_state.stats)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Roster rows", roster_rows)
        st.metric("Teams", team_rows)
    with col2:
        st.metric("Games", game_rows)
        st.metric("Stat entries", stat_rows)

    st.markdown("---")

    # -------------------------
    # Delete selected games
    # -------------------------
    st.subheader("Delete Selected Games (and Their Stats)")

    games = st.session_state.games
    if games.empty:
        st.info("No games stored.")
    else:
        games_sorted = games.sort_values("date")
        labels = []
        ids = []
        for _, g in games_sorted.iterrows():
            d = g["date"].date() if isinstance(g["date"], pd.Timestamp) else g["date"]
            label = f"{g['game_id']} – {d} – {g['sport']} – {g['team1']} vs {g['team2']}"
            labels.append(label)
            ids.append(g["game_id"])

        selected_labels = st.multiselect("Select games to delete", labels)
        label_to_id = dict(zip(labels, ids))
        selected_ids = [label_to_id[l] for l in selected_labels]

        if selected_ids and st.button("Delete Selected Games"):
            # Remove selected games
            st.session_state.games = st.session_state.games[
                ~st.session_state.games["game_id"].isin(selected_ids)
            ]
            # Remove their stats
            st.session_state.stats = st.session_state.stats[
                ~st.session_state.stats["game_id"].isin(selected_ids)
            ]
            st.success(f"Deleted {len(selected_ids)} game(s) and their stats.")

    st.markdown("---")

    # -------------------------
    # Delete ALL games & stats
    # -------------------------
    st.subheader("Delete ALL Games & Stats (keep roster)")

    st.warning("This will remove every game and every stat entry, but keep your roster and teams.")
    confirm_all_games = st.checkbox("I understand, delete ALL games & stats")
    if confirm_all_games and st.button("Delete ALL Games & Stats"):
        st.session_state.games = new_games_df()
        st.session_state.stats = new_stats_df()
        st.success("All games and stats have been deleted.")

    st.markdown("---")

    # -------------------------
    # Delete EVERYTHING
    # -------------------------
    st.subheader("Delete EVERYTHING (Roster, Teams, Games, Stats)")

    st.error(
        "This will completely reset the app. You will need to upload a new roster "
        "and re-enter all games and stats."
    )
    confirm_everything = st.checkbox("I REALLY understand, delete EVERYTHING")
    if confirm_everything and st.button("Full Reset: Clear All Data"):
        st.session_state.roster = None
        st.session_state.teams = None
        st.session_state.games = new_games_df()
        st.session_state.stats = new_stats_df()
        st.success("All data cleared. Go to Setup to upload a fresh roster.")


# -----------------------------------------
# Main
# -----------------------------------------

def main():
    st.set_page_config(page_title="Crest League Manager (Stats by Sport)", layout="wide")
    init_state()

    st.sidebar.image("logo-header-2.png", use_column_width=True)
    st.sidebar.title("Crest League Manager")
    st.sidebar.caption("Standings & multi-sport stats")

    page = st.sidebar.radio(
        "Go to",
        ["Setup", "Enter Scores & Stats", "Standings", "Leaderboards", "Admin / Clear Data"],
    )

    if page == "Setup":
        page_setup()
    elif page == "Enter Scores & Stats":
        page_enter_scores_and_stats()
    elif page == "Standings":
        page_standings()
    elif page == "Leaderboards":
        page_leaderboards()
    elif page == "Admin / Clear Data":
        page_admin()


if __name__ == "__main__":
    main()
