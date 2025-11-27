import streamlit as st
import pandas as pd
from datetime import date

# -----------------------------------------
# Session State Initialization
# -----------------------------------------

def init_state():
    if "roster" not in st.session_state:
        st.session_state.roster = None  # roster DataFrame
    if "teams" not in st.session_state:
        st.session_state.teams = None   # DataFrame of unique teams
    if "games" not in st.session_state:
        st.session_state.games = pd.DataFrame(columns=[
            "game_id", "date", "team1", "team2", "score1", "score2"
        ])
    if "stats" not in st.session_state:
        st.session_state.stats = pd.DataFrame(columns=[
            "game_id", "team_name", "player_id", "first_name",
            "last_name", "bunk", "stat_type", "value"
        ])
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


def compute_leaderboard(stat_type: str):
    """
    Aggregates stats by player for given stat_type ("points" or "assists").
    """
    stats = st.session_state.stats
    if stats.empty:
        return pd.DataFrame()

    df = stats[stats["stat_type"] == stat_type]
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

    st.subheader("New Game")

    col_date, col_team1, col_team2 = st.columns(3)
    with col_date:
        game_date = st.date_input("Game Date", value=date.today())
    with col_team1:
        team1 = st.selectbox("Team 1", teams_list, key="team1_select")
    with col_team2:
        team2 = st.selectbox("Team 2", teams_list, key="team2_select")

    if team1 == team2:
        st.error("Team 1 and Team 2 must be different.")
        return

    col_score1, col_score2 = st.columns(2)
    with col_score1:
        score1 = st.number_input(f"{team1} Score", min_value=0, step=1, value=0)
    with col_score2:
        score2 = st.number_input(f"{team2} Score", min_value=0, step=1, value=0)

    # Temporary key to tie widget values to this matchup
    temp_key = f"{game_date}_{team1}_{team2}".replace(" ", "_")

    st.markdown("### Player Stats (optional)")

    roster = st.session_state.roster

    home_roster = roster[roster["team_name"] == team1]
    away_roster = roster[roster["team_name"] == team2]

    st.caption("For each player, enter **Points** and **Assists** for this game (if any).")

    with st.expander(f"{team1} Player Stats", expanded=True):
        for _, p in home_roster.iterrows():
            row_key = f"{temp_key}_home_{p['player_id']}"
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"{p['first_name']} {p['last_name']} (Bunk {p['bunk']})")
            with col2:
                st.number_input(
                    "Points",
                    min_value=0,
                    step=1,
                    key=f"points_{row_key}"
                )
            with col3:
                st.number_input(
                    "Assists",
                    min_value=0,
                    step=1,
                    key=f"assists_{row_key}"
                )

    with st.expander(f"{team2} Player Stats", expanded=True):
        for _, p in away_roster.iterrows():
            row_key = f"{temp_key}_away_{p['player_id']}"
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"{p['first_name']} {p['last_name']} (Bunk {p['bunk']})")
            with col2:
                st.number_input(
                    "Points",
                    min_value=0,
                    step=1,
                    key=f"points_{row_key}"
                )
            with col3:
                st.number_input(
                    "Assists",
                    min_value=0,
                    step=1,
                    key=f"assists_{row_key}"
                )

    if st.button("Save Game & Stats"):
        # Create new game row
        game_id = f"G{len(st.session_state.games) + 1}"
        new_game = pd.DataFrame([{
            "game_id": game_id,
            "date": pd.to_datetime(game_date),
            "team1": team1,
            "team2": team2,
            "score1": score1,
            "score2": score2,
        }])

        st.session_state.games = pd.concat(
            [st.session_state.games, new_game], ignore_index=True
        )

        # Collect stats from widgets
        new_stats_rows = []

        # Team 1 stats
        for _, p in home_roster.iterrows():
            row_key = f"{temp_key}_home_{p['player_id']}"
            pts = st.session_state.get(f"points_{row_key}", 0)
            ast = st.session_state.get(f"assists_{row_key}", 0)

            if pts > 0:
                new_stats_rows.append({
                    "game_id": game_id,
                    "team_name": team1,
                    "player_id": p["player_id"],
                    "first_name": p["first_name"],
                    "last_name": p["last_name"],
                    "bunk": p["bunk"],
                    "stat_type": "points",
                    "value": int(pts),
                })
            if ast > 0:
                new_stats_rows.append({
                    "game_id": game_id,
                    "team_name": team1,
                    "player_id": p["player_id"],
                    "first_name": p["first_name"],
                    "last_name": p["last_name"],
                    "bunk": p["bunk"],
                    "stat_type": "assists",
                    "value": int(ast),
                })

        # Team 2 stats
        for _, p in away_roster.iterrows():
            row_key = f"{temp_key}_away_{p['player_id']}"
            pts = st.session_state.get(f"points_{row_key}", 0)
            ast = st.session_state.get(f"assists_{row_key}", 0)

            if pts > 0:
                new_stats_rows.append({
                    "game_id": game_id,
                    "team_name": team2,
                    "player_id": p["player_id"],
                    "first_name": p["first_name"],
                    "last_name": p["last_name"],
                    "bunk": p["bunk"],
                    "stat_type": "points",
                    "value": int(pts),
                })
            if ast > 0:
                new_stats_rows.append({
                    "game_id": game_id,
                    "team_name": team2,
                    "player_id": p["player_id"],
                    "first_name": p["first_name"],
                    "last_name": p["last_name"],
                    "bunk": p["bunk"],
                    "stat_type": "assists",
                    "value": int(ast),
                })

        if new_stats_rows:
            new_stats_df = pd.DataFrame(new_stats_rows)
            st.session_state.stats = pd.concat(
                [st.session_state.stats, new_stats_df], ignore_index=True
            )

        st.success(f"Saved game {game_id} and stats.")

    st.subheader("Games Entered So Far")
    if st.session_state.games.empty:
        st.info("No games yet.")
    else:
        display_games = st.session_state.games.copy()
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

    stat_type = st.selectbox("Stat Type", ["points", "assists"])

    lb = compute_leaderboard(stat_type)
    if lb.empty:
        st.info(f"No {stat_type} recorded yet.")
        return

    display = lb.rename(columns={
        "first_name": "First",
        "last_name": "Last",
        "bunk": "Bunk",
        "team_name": "Team",
        "value": stat_type.title(),
    })

    st.subheader(f"Top {len(display)} – {stat_type.title()}")
    st.dataframe(display, use_container_width=True)


# -----------------------------------------
# Main
# -----------------------------------------

def main():
    st.set_page_config(page_title="Crest League Manager (Simple)", layout="wide")
    init_state()

    st.sidebar.title("Crest League Manager")
    st.sidebar.caption("Simple standings & stats for league play")

    page = st.sidebar.radio(
        "Go to",
        ["Setup", "Enter Scores & Stats", "Standings", "Leaderboards"],
    )

    if page == "Setup":
        page_setup()
    elif page == "Enter Scores & Stats":
        page_enter_scores_and_stats()
    elif page == "Standings":
        page_standings()
    elif page == "Leaderboards":
        page_leaderboards()


if __name__ == "__main__":
    main()
