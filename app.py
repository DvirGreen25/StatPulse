import streamlit as st
import pandas as pd
import os
import time

# --- Page Config ---
st.set_page_config(
    page_title="StatPulse Ultimate",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Styling (Stathead Imitation) ---
st.markdown("""
<style>
    /* Clean Tables */
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    /* Metrics Styling */
    .stMetric {background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px;}
    
    /* Headers */
    h1, h2, h3 {font-family: 'Roboto', sans-serif; color: #1d428a;}
    
    /* Active Streak Badge */
    .active-badge {background-color: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;}
    
    /* Hide Default Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION: Active Teams Map ---
ACTIVE_TEAMS = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons', 'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
}

# --- HELPER FUNCTIONS ---
def get_headshot(player_id):
    return f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{int(player_id)}.png"

def get_team_logo(team_abbr):
    # Mapping Abbr to ID is tricky without a DB, using a fallback or generic NBA logo if ID missing
    # For now, we use a generic method or just display the name nicely. 
    # To get real logos we need Team IDs. Let's try to grab ID from the dataframe if possible.
    return f"https://cdn.nba.com/logos/nba/{team_abbr}/primary/L/logo.svg" # This URL structure usually requires ID, but let's try strict Abbr or fallback

# --- DATA ENGINE ---
@st.cache_data(ttl=3600)
def load_data_ultimate():
    required_cols = [
        'SEASON_ID', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'TEAM_ID',
        'GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 
        'STL', 'BLK', 'TOV', 'FGA', 'FGM', 'FG3M', 'FG3A', 'FTA', 'FTM', 'MIN', 'PLUS_MINUS', 'PF'
    ]

    def safe_read(file_path):
        try:
            return pd.read_csv(file_path, usecols=lambda c: c in required_cols)
        except:
            return pd.DataFrame()

    history = safe_read('nba_history.csv.zip')
    live = safe_read('nba_current.csv')

    if not history.empty and not live.empty:
        # Check for duplicates based on Game Date and Player
        df = pd.concat([history, live], ignore_index=True)
    elif not history.empty:
        df = history
    elif not live.empty:
        df = live
    else:
        return None

    df = df.drop_duplicates(subset=['PLAYER_ID', 'GAME_DATE'])

    # Data Cleaning & Types
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    if 'GAME_DATE' in df.columns:
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df['Date_Str'] = df['GAME_DATE'].dt.strftime('%Y-%m-%d')
    
    numeric_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FGA', 'FGM', 'FG3A', 'FG3M', 'FTA', 'FTM', 'MIN', 'PLUS_MINUS', 'TOV', 'PF']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Calculate Percentages
    df['FG%'] = (df['FGM'] / df['FGA']).fillna(0) * 100
    df['3P%'] = (df['FG3M'] / df['FG3A']).fillna(0) * 100
    df['FT%'] = (df['FTM'] / df['FTA']).fillna(0) * 100

    return df

# --- SIDEBAR & REFRESH ---
with st.sidebar:
    st.title("⚙️ Settings")
    if st.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.info("Click above if 2025/26 data is missing.")

# Load Data
df = load_data_ultimate()

if df is None:
    st.error("Data not found. Please check GitHub Actions.")
    st.stop()

# --- MAIN NAVIGATION ---
st.title("🏀 StatPulse Ultimate")
tab_game, tab_player, tab_h2h, tab_streak, tab_record = st.tabs([
    "🔎 Game Finder", "👤 Player Profile", "⚔️ Head-to-Head", "🔥 Streak Finder Pro", "🏆 Record Index"
])

# ==========================================
# 1. GAME FINDER (EXPANDED)
# ==========================================
with tab_game:
    st.subheader("Find Specific Games")
    
    # Filters
    c1, c2, c3 = st.columns(3)
    with c1:
        all_seasons = sorted(df['SEASON_ID'].astype(str).unique(), reverse=True)
        sel_seasons = st.multiselect("Season", all_seasons, default=all_seasons[:1])
    with c2:
        # Active teams only for filter
        sel_team_abbr = st.multiselect("Team", options=sorted(ACTIVE_TEAMS.keys()), format_func=lambda x: ACTIVE_TEAMS[x])
    with c3:
        opps = sorted(df['MATCHUP'].astype(str).unique())
        sel_opp = st.multiselect("Opponent / Matchup", opps[:50])

    # Basic Stats
    c1, c2, c3 = st.columns(3)
    with c1: min_pts = st.number_input("Min Points", 0, 100, 30)
    with c2: min_ast = st.number_input("Min Assists", 0, 50, 0)
    with c3: min_reb = st.number_input("Min Rebounds", 0, 50, 0)

    # Advanced Stats Expander
    with st.expander("➕ Advanced Filters (Blocks, Steals, 3PM, Minutes...)"):
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1: min_stl = st.number_input("Min Steals", 0, 20, 0)
        with ac2: min_blk = st.number_input("Min Blocks", 0, 20, 0)
        with ac3: min_3pm = st.number_input("Min 3PM", 0, 20, 0)
        with ac4: min_min = st.number_input("Min Minutes", 0, 60, 0)
        
        ac5, ac6 = st.columns(2)
        with ac5: min_tov = st.number_input("Max Turnovers", 0, 20, 20) # Max logic usually
        with ac6: min_pm = st.number_input("Min Plus/Minus", -50, 50, -50)

    # Logic
    gf_df = df.copy()
    if sel_seasons: gf_df = gf_df[gf_df['SEASON_ID'].isin(sel_seasons)]
    if sel_team_abbr: gf_df = gf_df[gf_df['TEAM_ABBREVIATION'].isin(sel_team_abbr)]
    
    res = gf_df[
        (gf_df['PTS'] >= min_pts) & (gf_df['AST'] >= min_ast) & (gf_df['REB'] >= min_reb) &
        (gf_df['STL'] >= min_stl) & (gf_df['BLK'] >= min_blk) & (gf_df['FG3M'] >= min_3pm) &
        (gf_df['MIN'] >= min_min) & (gf_df['PLUS_MINUS'] >= min_pm)
    ]
    
    st.markdown(f"**Found {len(res)} games.**")
    
    cols_show = ['Date_Str', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'FG%', 'PLUS_MINUS']
    
    st.dataframe(
        res[cols_show].sort_values('PTS', ascending=False).head(500),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date_Str": "Date",
            "TEAM_ABBREVIATION": "Team",
            "FG%": st.column_config.NumberColumn("FG%", format="%.1f%%"),
            "PLUS_MINUS": st.column_config.NumberColumn("+/-", format="%+d")
        }
    )

# ==========================================
# 2. PLAYER PROFILE (BREF STYLE)
# ==========================================
with tab_player:
    all_players = sorted(df['PLAYER_NAME'].dropna().unique())
    # Smart Default
    def_idx = all_players.index("Shai Gilgeous-Alexander") if "Shai Gilgeous-Alexander" in all_players else 0
    p_sel = st.selectbox("Select Player", all_players, index=def_idx)

    p_data = df[df['PLAYER_NAME'] == p_sel].sort_values('GAME_DATE', ascending=False)
    
    if not p_data.empty:
        # Header
        head_c1, head_c2 = st.columns([1, 5])
        with head_c1:
            st.image(get_headshot(p_data.iloc[0]['PLAYER_ID']))
        with head_c2:
            team_now = p_data.iloc[0]['TEAM_ABBREVIATION']
            team_full = ACTIVE_TEAMS.get(team_now, team_now)
            st.markdown(f"## {p_sel}")
            st.markdown(f"**{team_full}**")
            
            # Summary Metrics
            s_gp = len(p_data)
            s_ppg = p_data['PTS'].mean()
            s_rpg = p_data['REB'].mean()
            s_apg = p_data['AST'].mean()
            s_per = p_data['FG%'].mean() # Rough approx
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Games", s_gp)
            m2.metric("PPG", f"{s_ppg:.1f}")
            m3.metric("RPG", f"{s_rpg:.1f}")
            m4.metric("APG", f"{s_apg:.1f}")

        st.divider()
        
        # Sub-Navigation (The "Blue" Menu)
        view_mode = st.radio("View:", ["Overview / Season Stats", "Game Logs", "Splits"], horizontal=True)
        
        if view_mode == "Overview / Season Stats":
            st.markdown("#### Season Averages")
            season_avg = p_data.groupby('SEASON_ID').mean(numeric_only=True).sort_index(ascending=False)
            season_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FGM', 'FGA', 'FG%', 'FG3M', 'FG3A', '3P%', 'FTM', 'FTA', 'FT%', 'MIN', 'PLUS_MINUS']
            st.dataframe(season_avg[season_cols].style.format("{:.1f}"), use_container_width=True)

        elif view_mode == "Game Logs":
            st.markdown("#### Complete Game Log")
            log_cols = ['Date_Str', 'TEAM_ABBREVIATION', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'FG3M', 'FG%', 'PLUS_MINUS']
            st.dataframe(
                p_data[log_cols], 
                use_container_width=True, 
                hide_index=True,
                column_config={"Date_Str": "Date", "PLUS_MINUS": st.column_config.NumberColumn("+/-", format="%+d")}
            )
            
        elif view_mode == "Splits":
            st.markdown("#### Career Splits")
            p_data['WIN'] = p_data['WL'].apply(lambda x: "Win" if x == 'W' else "Loss")
            p_data['LOC'] = p_data['MATCHUP'].apply(lambda x: "Home" if " vs. " in str(x) else "Away")
            
            c_split1, c_split2 = st.columns(2)
            with c_split1:
                st.write("**By Result (Win/Loss)**")
                st.dataframe(p_data.groupby('WIN')[['PTS', 'REB', 'AST', 'FG%', 'PLUS_MINUS']].mean().style.format("{:.1f}"), use_container_width=True)
            with c_split2:
                st.write("**By Location (Home/Away)**")
                st.dataframe(p_data.groupby('LOC')[['PTS', 'REB', 'AST', 'FG%', 'PLUS_MINUS']].mean().style.format("{:.1f}"), use_container_width=True)

# ==========================================
# 3. HEAD TO HEAD (STATHEAD STYLE)
# ==========================================
with tab_h2h:
    st.subheader("Player Comparison Tool")
    
    # Selectors
    c_sel1, c_vs, c_sel2 = st.columns([1, 0.2, 1])
    with c_sel1:
        p1_name = st.selectbox("Player 1", all_players, index=0)
    with c_sel2:
        p2_name = st.selectbox("Player 2", all_players, index=1)
        
    # Data Fetch
    p1_df = df[df['PLAYER_NAME'] == p1_name]
    p2_df = df[df['PLAYER_NAME'] == p2_name]
    
    # Images Centered
    c_img1, c_vs_img, c_img2 = st.columns([1, 0.5, 1])
    with c_img1: 
        st.image(get_headshot(p1_df.iloc[0]['PLAYER_ID']), width=200)
    with c_img2: 
        st.image(get_headshot(p2_df.iloc[0]['PLAYER_ID']), width=200)

    st.divider()
    
    # Comparison Logic
    stats_map = {
        'Points': 'PTS', 'Rebounds': 'REB', 'Assists': 'AST', 'Steals': 'STL', 'Blocks': 'BLK',
        'Turnovers': 'TOV', 'FG%': 'FG%', '3P%': '3P%', 'FT%': 'FT%', 'Minutes': 'MIN', 'Plus/Minus': 'PLUS_MINUS'
    }
    
    comp_data = []
    for label, col in stats_map.items():
        v1 = p1_df[col].mean()
        v2 = p2_df[col].mean()
        diff = v1 - v2
        
        comp_data.append({
            "Category": label,
            p1_name: f"{v1:.1f}",
            p2_name: f"{v2:.1f}",
            "Diff": diff # Keep numeric for styling
        })
        
    comp_df = pd.DataFrame(comp_data)
    
    # Custom Coloring Function
    def color_diff(val):
        color = '#d4edda' if val > 0 else '#f8d7da' if val < 0 else 'white' # Green if + (P1 wins), Red if - (P2 wins)
        return f'background-color: {color}; color: black'

    # Display Styled DataFrame
    st.dataframe(
        comp_df.style.applymap(color_diff, subset=['Diff']).format({'Diff': '{:+.1f}'}),
        use_container_width=True,
        hide_index=True,
        height=500
    )

# ==========================================
# 4. STREAK FINDER PRO (MULTI-CONDITION)
# ==========================================
with tab_streak:
    st.subheader("🔥 Advanced Streak Finder")
    st.caption("Find consecutive games matching MULTIPLE criteria (e.g., Triple Doubles)")
    
    # Dynamic Criteria Inputs
    c1, c2, c3 = st.columns(3)
    with c1: 
        s_stat1 = st.selectbox("Stat 1", ['PTS', 'AST', 'REB', 'STL', 'BLK', 'FG3M'], index=0)
        s_val1 = st.number_input("Val 1 >=", 0, 100, 30)
    with c2:
        use_2 = st.checkbox("Add Stat 2?")
        s_stat2 = st.selectbox("Stat 2", ['AST', 'PTS', 'REB', 'STL', 'BLK'], index=0)
        s_val2 = st.number_input("Val 2 >=", 0, 100, 10)
    with c3:
        use_3 = st.checkbox("Add Stat 3?")
        s_stat3 = st.selectbox("Stat 3", ['REB', 'PTS', 'AST', 'STL', 'BLK'], index=0)
        s_val3 = st.number_input("Val 3 >=", 0, 100, 10)
        
    c_len, c_active = st.columns(2)
    with c_len: min_len = st.number_input("Min Streak Length", 2, 100, 3)
    with c_active: 
        only_active = st.checkbox("Active Streaks Only (Alive)", value=False)
        
    if st.button("🔎 Search Streaks"):
        # Build Boolean Mask
        mask = (df[s_stat1] >= s_val1)
        if use_2: mask = mask & (df[s_stat2] >= s_val2)
        if use_3: mask = mask & (df[s_stat3] >= s_val3)
        
        sdf = df.copy().sort_values(['PLAYER_NAME', 'GAME_DATE'])
        sdf['match'] = mask
        
        # Streak Grouping Magic
        sdf['grp'] = (sdf['match'] != sdf['match'].shift()).cumsum()
        sdf = sdf[sdf['match']] # Keep only matching games
        
        # Aggregate
        res = sdf.groupby(['PLAYER_NAME', 'grp']).agg(
            Length=('GAME_DATE', 'count'),
            Start=('Date_Str', 'first'),
            End=('Date_Str', 'last'),
            Avg_Stat1=(s_stat1, 'mean'),
            Last_Game_In_DB=('GAME_DATE', 'max') # To check active
        ).reset_index()
        
        # Get actual last game for every player to check "Active"
        player_last_game = df.groupby('PLAYER_NAME')['GAME_DATE'].max().to_dict()
        
        final_res = []
        for idx, row in res.iterrows():
            if row['Length'] >= min_len:
                is_active = row['Last_Game_In_DB'] == player_last_game[row['PLAYER_NAME']]
                
                if only_active and not is_active:
                    continue
                    
                final_res.append({
                    "Player": row['PLAYER_NAME'],
                    "Length": row['Length'],
                    "Start": row['Start'],
                    "End": row['End'],
                    "Avg": row['Avg_Stat1'],
                    "Status": "🟢 Active" if is_active else "🔴 Ended"
                })
        
        st.dataframe(pd.DataFrame(final_res).sort_values('Length', ascending=False), use_container_width=True, hide_index=True)

# ==========================================
# 5. RECORD INDEX (SELECTOR STYLE)
# ==========================================
with tab_record:
    st.subheader("🏆 NBA Record Index")
    
    rec_type = st.radio("Record Type:", ["Single Game", "Season Total", "Per Game (Season)"], horizontal=True)
    
    # Create Leaderboards (Pre-calc top 1)
    # This simulates the "Index" view where you see the record holder before clicking
    records = {
        'Points': 'PTS', 'Assists': 'AST', 'Rebounds': 'REB', 'Steals': 'STL', 'Blocks': 'BLK', 
        '3-Pointers': 'FG3M', 'Turnovers': 'TOV'
    }
    
    # UI: Select Box with "Current Leader" info
    options = []
    for name, col in records.items():
        if rec_type == "Single Game":
            top = df.nlargest(1, col).iloc[0]
            val = int(top[col])
            holder = top['PLAYER_NAME']
            options.append(f"{name} (Record: {val} by {holder})")
        elif rec_type == "Season Total":
            # Group by Player+Season
            seas = df.groupby(['PLAYER_NAME', 'SEASON_ID'])[col].sum().reset_index()
            top = seas.nlargest(1, col).iloc[0]
            options.append(f"{name} (Record: {int(top[col])} by {top['PLAYER_NAME']} in {top['SEASON_ID']})")
        else: # Per Game
            # Filter seasons with minimal games to avoid noise
            seas_cnt = df.groupby(['PLAYER_NAME', 'SEASON_ID']).filter(lambda x: len(x) > 40)
            if seas_cnt.empty: seas_cnt = df # Fallback
            seas = seas_cnt.groupby(['PLAYER_NAME', 'SEASON_ID'])[col].mean().reset_index()
            top = seas.nlargest(1, col).iloc[0]
            options.append(f"{name} (Record: {top[col]:.1f} by {top['PLAYER_NAME']})")

    sel_rec = st.selectbox("Choose Category to View Full List:", options)
    
    # Parse selection to get column back
    cat_name = sel_rec.split(" (")[0]
    target_col = records[cat_name]
    
    st.divider()
    st.markdown(f"### Top 100 Leaders: {cat_name}")
    
    if rec_type == "Single Game":
        st.dataframe(df.nlargest(100, target_col)[['Date_Str', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'MATCHUP', target_col]], hide_index=True, use_container_width=True)
    elif rec_type == "Season Total":
        seas_tot = df.groupby(['PLAYER_NAME', 'SEASON_ID', 'TEAM_ABBREVIATION'])[target_col].sum().reset_index()
        st.dataframe(seas_tot.nlargest(100, target_col), hide_index=True, use_container_width=True)
    else:
        seas_avg = df.groupby(['PLAYER_NAME', 'SEASON_ID', 'TEAM_ABBREVIATION']).filter(lambda x: len(x) > 20)
        seas_avg = seas_avg.groupby(['PLAYER_NAME', 'SEASON_ID', 'TEAM_ABBREVIATION'])[target_col].mean().reset_index()
        st.dataframe(seas_avg.nlargest(100, target_col).style.format({target_col: "{:.1f}"}), hide_index=True, use_container_width=True)
