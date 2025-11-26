import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ------------------------------
# Helpers: Session State & Data
# ------------------------------

def init_state():
    if "teams" not in st.session_state:
        st.session_state.teams = pd.DataFrame([
            {"team_id": "FS_RED", "team_name": "Fresh/Soph Red", "league_group": "F/S League"},
            {"team_id": "FS_BLUE", "team_name": "Fresh/Soph Blue", "league_group": "F/S League"},
            {"team_id": "JR_GREEN", "team_name": "Junior Green", "league_group": "Junior League"},
            {"team_id": "JR_GOLD", "team_name": "Junior Gold", "league_group": "Junior League"},
            {"team_id": "SWC_BLACK", "team_name": "SWC Black", "league_group": "SWC League"},
            {"team_id": "SWC_WHITE", "team_name": "SWC White", "league_group": "SWC League"},
        ])

    if "roster" not in st.session_state:
        st.session_state.roster = pd.DataFrame([
            {"camper_id": "C001", "first_name": "Alex", "last_name": "R", "team_id": "FS_RED", "bunk": "1", "age_group": "Freshman"},
            {"camper_id": "C002", "first_name": "Ben", "last_name": "S", "team_id": "FS_BLUE", "bunk": "2", "age_group": "Sophomore"},
            {"camper_id": "C003", "first_name": "Charlie", "last_name": "T", "team_id": "JR_GREEN", "bunk": "5", "age_group": "Junior"},
            {"camper_id": "C004", "first_name": "Dylan", "last_name": "U", "team_id": "JR_GOLD", "bunk": "6", "age_group": "Junior"},
            {"camper_id": "C005", "first_name": "Evan", "last_name": "V", "team_id": "SWC_BLACK", "bunk": "15", "age_group": "Senior"},
            {"camper_id": "C006", "first_name": "Finn", "last_name": "W", "team_id": "SWC_WHITE", "bunk": "16", "age_group": "Waiter"},
        ])

    if "games" not in st.session_state:
        st.session_state.games = pd.DataFrame(columns=[
            "game_id", "date", "league_group", "slot", "sport", "venue",
            "team_home_id", "team_away_id", "score_home", "score_away",
            "status", "notes"
        ])

    if "stats" not in st.session_state:
        st.session_state.stats = pd.DataFrame(columns=[
            "game_id", "camper_id", "stat_type", "stat_value"
        ])

    if "points_for_win" not in st.session_state:
        st.session_state.points_for_win = 2
    if "points_for_tie" not in st.session_state:
        st.session_state.points_for_tie = 1
    if "points_for_loss" not in st.session_state:
        st.session_state.points_for_loss = 0


def get_team_options(league_filter=None):
    teams = st.session_state.teams
    if league_filter:
        teams = teams[teams["league_group"] == league_filter]
    return {f'{row["team_name"]} ({row["league_group"]})': row["team_id"] for _, row in teams.iterrows()}


def generate_game_id(row_index: int, game_date: date, slot: str, league_group: str) -> str:
    return f"{game_date.strftime('%Y%m%d')}_{league_group.replace(' ', '')}_{slot}_{row_index}"


# ------------------------------
# Standings & Stats Calculation
# ------------------------------

def compute_standings():
    games = st.session_state.games
    teams = st.session_state.teams

    # Initialize standings with all teams
    standings = teams.copy()
    standings["gp"] = 0
    standings["w"] = 0
    standings["l"] = 0
    standings["t"] = 0
    standings["pts"] = 0
    standings["gf"] = 0
    standings["ga"] = 0
    standings["diff"] = 0
    standings["streak"] = ""

    if games.empty:
        return standings

    # Only final games count
    final_games = games[games["status"] == "Final"].dropna(subset=["score_home", "score_away"])
    for _, g in final_games.iterrows():
        home_id = g["team_home_id"]
        away_id = g["team_away_id"]
        sh = int(g["score_home"])
        sa = int(g["score_away"])

        # Update goals for/against
        for team_id, gf, ga in [(home_id, sh, sa), (away_id, sa, sh)]:
            idx = standings["team_id"] == team_id
            standings.loc[idx, "gp"] += 1
            standings.loc[idx, "gf"] += gf
            standings.loc[idx, "ga"] += ga

        # Determine outcome
        if sh > sa:
            # home win
            standings.loc[standings["team_id"] == home_id, "w"] += 1
            standings.loc[standings["team_id"] == away_id, "l"] += 1
            standings.loc[standings["team_id"] == home_id, "pts"] += st.session_state.points_for_win
            standings.loc[standings["team_id"] == away_id, "pts"] += st.session_state.points_for_loss
        elif sh < sa:
            # away win
            standings.loc[standings["team_id"] == away_id, "w"] += 1
            standings.loc[standings["team_id"] == home_id, "l"] += 1
            standings.loc[standings["team_id"] == away_id, "pts"] += st.session_state.points_for_win
            standings.loc[standings["team_id"] == home_id, "pts"] += st.session_state.points_for_loss
        else:
            # tie
            standings.loc[standings["team_id"] == home_id, "t"] += 1
            standings.loc[standings["team_id"] == away_id, "t"] += 1
            standings.loc[standings["team_id"] == home_id, "pts"] += st.session_state.points_for_tie
            standings.loc[standings["team_id"] == away_id, "pts"] += st.session_state.points_for_tie

    standings["diff"] = standings["gf"] - standings["ga"]

    # Simple streak calculation (last result only)
    standings["streak"] = ""
    for team_id in standings["team_id"]:
        team_games = final_games[(final_games["team_home_id"] == team_id) | (final_games["team_away_id"] == team_id)]
        if team_games.empty:
            continue
        last_game = team_games.sort_values("date").iloc[-1]
        if last_game["score_home"] == last_game["score_away"]:
            result = "T1"
        else:
            home_team = last_game["team_home_id"] == team_id
            home_won = last_game["score_home"] > last_game["score_away"]
            away_won = last_game["score_away"] > last_game["score_home"]
            if (home_team and home_won) or ((not home_team) and away_won):
                result = "W1"
            else:
                result = "L1"
        standings.loc[standings["team_id"] == team_id, "streak"] = result

    # Sort within each league_group
    standings_sorted = standings.sort_values(
        by=["league_group", "pts", "diff", "gf", "team_name"],
        ascending=[True, False, False, False, True]
    ).reset_index(drop=True)

    return standings_sorted


def compute_leaderboards(stat_type_filter="points"):
    stats = st.session_state.stats
    roster = st.session_state.roster
    teams = st.session_state.teams

    if stats.empty:
        return pd.DataFrame()

    stats_filtered = stats[stats["stat_type"] == stat_type_filter]
    if stats_filtered.empty:
        return pd.DataFrame()

    agg = stats_filtered.groupby("camper_id")["stat_value"].sum().reset_index()
    agg = agg.rename(columns={"stat_value": "total"})

    merged = agg.merge(roster, on="camper_id", how="left")
    merged = merged.merge(teams[["team_id", "team_name", "league_group"]], on="team_id", how="left")

    # Games played for each camper
    gp = stats_filtered.groupby("camper_id")["game_id"].nunique().reset_index()
    gp = gp.rename(columns={"game_id": "games_played"})
    merged = merged.merge(gp, on="camper_id", how="left")

    merged = merged.sort_values(by="total", ascending=False).reset_index(drop=True)
    merged["rank"] = merged.index + 1
    cols = ["rank", "first_name", "last_name", "bunk", "team_name", "league_group", "total", "games_played"]
    return merged[cols]


# ------------------------------
# PDF Export
# ------------------------------

def generate_standings_pdf(standings_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    today_str = date.today().strftime("%B %d, %Y")

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Camp Bauercrest - League Standings")
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 90, f"Date: {today_str}")

    y = height - 120
    line_height = 14

    league_groups = standings_df["league_group"].unique()
    for lg in league_groups:
        lg_table = standings_df[standings_df["league_group"] == lg]
        if y < 120:
            c.showPage()
            y = height - 72

        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, y, lg)
        y -= line_height

        c.setFont("Helvetica-Bold", 10)
        headers = ["Team", "W", "L", "T", "Pts", "GF", "GA", "Diff", "Streak"]
        x_positions = [72, 250, 275, 300, 325, 360, 395, 430, 480]
        for x, h in zip(x_positions, headers):
            c.drawString(x, y, h)
        y -= line_height

        c.setFont("Helvetica", 10)
        for _, row in lg_table.iterrows():
            if y < 72:
                c.showPage()
                y = height - 72
                c.setFont("Helvetica-Bold", 14)
                c.drawString(72, y, lg + " (cont.)")
                y -= line_height
                c.setFont("Helvetica-Bold", 10)
                for x, h in zip(x_positions, headers):
                    c.drawString(x, y, h)
                y -= line_height
                c.setFont("Helvetica", 10)

            values = [
                row["team_name"],
                str(int(row["w"])),
                str(int(row["l"])),
                str(int(row["t"])),
                str(int(row["pts"])),
                str(int(row["gf"])),
                str(int(row["ga"])),
                str(int(row["diff"])),
                row.get("streak", ""),
            ]
            for x, v in zip(x_positions, values):
                c.drawString(x, y, v)
            y -= line_height

        y -= line_height  # extra space between leagues

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ------------------------------
# Pages
# ------------------------------

def page_dashboard():
    st.header("League Manager Dashboard")
    st.write("Quick view of today's games and current standings.")

    today = date.today()
    games = st.session_state.games
    todays_games = games[games["date"] == pd.to_datetime(today)]
    if todays_games.empty:
        st.info("No games scheduled for today yet.")
    else:
        st.subheader("Today's Games")
        st.dataframe(todays_games)

    st.subheader("Current Standings")
    standings = compute_standings()
    st.dataframe(standings)


def page_schedule_games():
    st.header("Schedule Games (A/B/C/D)")

    leagues = st.session_state.teams["league_group"].unique().tolist()
    league_group = st.selectbox("League Group", leagues)
    game_date = st.date_input("Date", value=date.today())
    slots = ["A", "B", "C", "D"]
    sports = ["Softball", "Basketball", "Soccer", "Flag Football", "Other"]

    team_options = get_team_options(league_filter=league_group)
    team_names = list(team_options.keys())

    st.write("Enter matchups for each slot:")

    new_games = []
    for slot in slots:
        with st.expander(f"Slot {slot}", expanded=(slot == "A")):
            enable = st.checkbox(f"Use Slot {slot}", value=(slot in ["A", "B"]))
            if not enable:
                continue
            sport = st.selectbox(f"Sport (Slot {slot})", sports, key=f"sport_{slot}")
            venue = st.text_input(f"Venue (Slot {slot})", value=f"{slot} Field", key=f"venue_{slot}")
            home_team = st.selectbox(f"Home Team (Slot {slot})", team_names, key=f"home_{slot}")
            away_team = st.selectbox(f"Away Team (Slot {slot})", team_names, key=f"away_{slot}")
            notes = st.text_input(f"Notes (Slot {slot})", "", key=f"notes_{slot}")

            if home_team == away_team:
                st.warning(f"Home and Away teams are the same for Slot {slot}. Please fix before saving.")
            else:
                new_games.append({
                    "slot": slot,
                    "sport": sport,
                    "venue": venue,
                    "home_team_key": home_team,
                    "away_team_key": away_team,
                    "notes": notes,
                })

    if st.button("Save Games for This Day"):
        existing = st.session_state.games
        for idx, g in enumerate(new_games):
            game_id = generate_game_id(idx, game_date, g["slot"], league_group)
            row = {
                "game_id": game_id,
                "date": pd.to_datetime(game_date),
                "league_group": league_group,
                "slot": g["slot"],
                "sport": g["sport"],
                "venue": g["venue"],
                "team_home_id": team_options[g["home_team_key"]],
                "team_away_id": team_options[g["away_team_key"]],
                "score_home": None,
                "score_away": None,
                "status": "Scheduled",
                "notes": g["notes"],
            }
            existing = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)

        st.session_state.games = existing
        st.success("Games saved for this day!")
        st.experimental_rerun()

    st.subheader("Games for Selected League & Date")
    filt = (st.session_state.games["league_group"] == league_group) & \
           (st.session_state.games["date"] == pd.to_datetime(game_date))
    st.dataframe(st.session_state.games[filt])


def page_enter_results():
    st.header("Enter Results & Stats")

    if st.session_state.games.empty:
        st.info("No games scheduled yet.")
        return

    leagues = st.session_state.teams["league_group"].unique().tolist()
    league_group = st.selectbox("League Group", leagues)
    game_date = st.date_input("Date", value=date.today(), key="results_date")

    mask = (st.session_state.games["league_group"] == league_group) & \
           (st.session_state.games["date"] == pd.to_datetime(game_date))
    games = st.session_state.games[mask].copy()

    if games.empty:
        st.info("No games for this league and date.")
        return

    teams = st.session_state.teams.set_index("team_id")

    for idx, g in games.iterrows():
        st.subheader(f"{g['sport']} - Slot {g['slot']} @ {g['venue']}")
        home_name = teams.loc[g["team_home_id"], "team_name"]
        away_name = teams.loc[g["team_away_id"], "team_name"]

        col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
        with col1:
            st.markdown(f"**{home_name} vs {away_name}**")
        with col2:
            sh = st.number_input("Home Score", min_value=0, value=int(g["score_home"]) if pd.notna(g["score_home"]) else 0,
                                 key=f"sh_{g['game_id']}")
        with col3:
            sa = st.number_input("Away Score", min_value=0, value=int(g["score_away"]) if pd.notna(g["score_away"]) else 0,
                                 key=f"sa_{g['game_id']}")
        with col4:
            status = st.selectbox("Status", ["Scheduled", "In Progress", "Final", "Cancelled"],
                                  index=["Scheduled", "In Progress", "Final", "Cancelled"].index(g["status"]),
                                  key=f"status_{g['game_id']}")

        # Stats entry
        with st.expander("Enter Stats (optional)", expanded=False):
            roster = st.session_state.roster
            home_roster = roster[roster["team_id"] == g["team_home_id"]]
            away_roster = roster[roster["team_id"] == g["team_away_id"]]

            st.caption("Use this for goals/points/etc. Only one stat type for now: 'points'")

            stat_type = "points"

            colh1, colh2 = st.columns(2)
            with colh1:
                st.markdown(f"**{home_name} Scorers**")
                for _, p in home_roster.iterrows():
                    val = st.number_input(
                        f"{p['first_name']} {p['last_name']} ({p['bunk']})",
                        min_value=0,
                        value=0,
                        key=f"stat_{g['game_id']}_{p['camper_id']}"
                    )
                    if val > 0:
                        # Store / update stat row
                        existing_mask = (st.session_state.stats["game_id"] == g["game_id"]) & \
                                        (st.session_state.stats["camper_id"] == p["camper_id"]) & \
                                        (st.session_state.stats["stat_type"] == stat_type)
                        st.session_state.stats = st.session_state.stats[~existing_mask]
                        st.session_state.stats = pd.concat([
                            st.session_state.stats,
                            pd.DataFrame([{
                                "game_id": g["game_id"],
                                "camper_id": p["camper_id"],
                                "stat_type": stat_type,
                                "stat_value": val,
                            }])
                        ], ignore_index=True)

            with colh2:
                st.markdown(f"**{away_name} Scorers**")
                for _, p in away_roster.iterrows():
                    val = st.number_input(
                        f"{p['first_name']} {p['last_name']} ({p['bunk']}) ",
                        min_value=0,
                        value=0,
                        key=f"stat_{g['game_id']}_{p['camper_id']}"
                    )
                    if val > 0:
                        existing_mask = (st.session_state.stats["game_id"] == g["game_id"]) & \
                                        (st.session_state.stats["camper_id"] == p["camper_id"]) & \
                                        (st.session_state.stats["stat_type"] == stat_type)
                        st.session_state.stats = st.session_state.stats[~existing_mask]
                        st.session_state.stats = pd.concat([
                            st.session_state.stats,
                            pd.DataFrame([{
                                "game_id": g["game_id"],
                                "camper_id": p["camper_id"],
                                "stat_type": stat_type,
                                "stat_value": val,
                            }])
                        ], ignore_index=True)

        # Save button for this game
        if st.button(f"Save Result ({g['game_id']})"):
            # Update the master games DF
            idx_master = st.session_state.games["game_id"] == g["game_id"]
            st.session_state.games.loc[idx_master, "score_home"] = sh
            st.session_state.games.loc[idx_master, "score_away"] = sa
            st.session_state.games.loc[idx_master, "status"] = status
            st.success(f"Saved result for game {g['game_id']}.")

    st.info("All saved results automatically update standings and leaderboards.")


def page_standings():
    st.header("Standings")

    standings = compute_standings()
    if standings.empty:
        st.info("No standings yet. Schedule games and enter Final scores.")
        return

    leagues = standings["league_group"].unique().tolist()
    league_group = st.selectbox("League Group", leagues)

    lg_table = standings[standings["league_group"] == league_group].copy()
    lg_table.insert(0, "Rank", range(1, len(lg_table) + 1))
    display_cols = ["Rank", "team_name", "w", "l", "t", "pts", "gf", "ga", "diff", "streak"]
    display = lg_table[display_cols]
    display = display.rename(columns={
        "team_name": "Team",
        "w": "W",
        "l": "L",
        "t": "T",
        "pts": "Pts",
        "gf": "GF",
        "ga": "GA",
        "diff": "Diff",
        "streak": "Streak",
    })
    st.dataframe(display, use_container_width=True)

    with st.expander("Points Settings"):
        st.session_state.points_for_win = st.number_input("Points for Win", min_value=0, max_value=10, value=st.session_state.points_for_win)
        st.session_state.points_for_tie = st.number_input("Points for Tie", min_value=0, max_value=10, value=st.session_state.points_for_tie)
        st.session_state.points_for_loss = st.number_input("Points for Loss", min_value=0, max_value=10, value=st.session_state.points_for_loss)
        st.caption("Changing these will affect newly computed standings (re-run this page).")


def page_leaderboards():
    st.header("Leaderboards")

    stats = st.session_state.stats
    if stats.empty:
        st.info("No stats recorded yet.")
        return

    stat_type = st.selectbox("Stat Type", ["points"])
    lb = compute_leaderboards(stat_type_filter=stat_type)
    if lb.empty:
        st.info("No stats of this type yet.")
        return

    leagues = lb["league_group"].unique().tolist()
    league_group = st.selectbox("League Group", leagues)

    lg_lb = lb[lb["league_group"] == league_group]

    st.subheader(f"Top {len(lg_lb)} - {league_group} - {stat_type.title()}")
    display = lg_lb.rename(columns={
        "first_name": "First",
        "last_name": "Last",
        "bunk": "Bunk",
        "team_name": "Team",
        "league_group": "League",
        "total": stat_type.title(),
        "games_played": "Games",
    })
    st.dataframe(display, use_container_width=True)


def page_export_pdf():
    st.header("Export Standings PDF")

    standings = compute_standings()
    if standings.empty:
        st.info("No standings available to export.")
        return

    pdf_bytes = generate_standings_pdf(standings)
    today_str = date.today().strftime("%Y-%m-%d")
    filename = f"bauercrest_league_standings_{today_str}.pdf"

    st.download_button(
        label="Download Standings PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
    )

    st.success("PDF generated. You can download and print it for the mess hall.")


def page_data_admin():
    st.header("Data Admin (Teams & Roster)")

    st.subheader("Teams")
    st.write("Edit teams directly in the table. Changes are saved when you click 'Save Teams'.")

    teams_edit = st.data_editor(st.session_state.teams, num_rows="dynamic", use_container_width=True)
    if st.button("Save Teams"):
        st.session_state.teams = teams_edit
        st.success("Teams updated.")

    st.subheader("Roster")
    st.write("Edit roster directly. Each camper must be linked to a valid team_id.")

    roster_edit = st.data_editor(st.session_state.roster, num_rows="dynamic", use_container_width=True)
    if st.button("Save Roster"):
        st.session_state.roster = roster_edit
        st.success("Roster updated.")

    st.subheader("Import / Export CSVs")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Import Teams CSV**")
        file_teams = st.file_uploader("Upload teams.csv", type=["csv"], key="upload_teams")
        if file_teams is not None:
            st.session_state.teams = pd.read_csv(file_teams)
            st.success("Teams imported from CSV.")

        st.markdown("**Import Roster CSV**")
        file_roster = st.file_uploader("Upload roster.csv", type=["csv"], key="upload_roster")
        if file_roster is not None:
            st.session_state.roster = pd.read_csv(file_roster)
            st.success("Roster imported from CSV.")

    with col2:
        st.markdown("**Download Current Teams CSV**")
        teams_csv = st.session_state.teams.to_csv(index=False).encode("utf-8")
        st.download_button("Download teams.csv", data=teams_csv, file_name="teams.csv", mime="text/csv")

        st.markdown("**Download Current Roster CSV**")
        roster_csv = st.session_state.roster.to_csv(index=False).encode("utf-8")
        st.download_button("Download roster.csv", data=roster_csv, file_name="roster.csv", mime="text/csv")


# ------------------------------
# Main
# ------------------------------

def main():
    st.set_page_config(page_title="Bauercrest League Manager", layout="wide")
    init_state()

    st.sidebar.title("League Manager")
    st.sidebar.caption("Camp Bauercrest • League Standings & Stats")
    page = st.sidebar.radio(
        "Go to",
        [
            "Dashboard",
            "Schedule Games",
            "Enter Results & Stats",
            "Standings",
            "Leaderboards",
            "Export PDF",
            "Data Admin",
        ],
    )

    if page == "Dashboard":
        page_dashboard()
    elif page == "Schedule Games":
        page_schedule_games()
    elif page == "Enter Results & Stats":
        page_enter_results()
    elif page == "Standings":
        page_standings()
    elif page == "Leaderboards":
        page_leaderboards()
    elif page == "Export PDF":
        page_export_pdf()
    elif page == "Data Admin":
        page_data_admin()


if __name__ == "__main__":
    main()
