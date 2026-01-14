import streamlit as st
import pandas as pd
import os

# --- Page Config ---
st.set_page_config(
    page_title="StatPulse Pro",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS Hacks for Cleaner Look ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;} /* Hide Sidebar Completely */
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 10px;}
    div[data-testid="stExpander"] div[role="button"] p {font-size: 1.1rem; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def get_headshot_url(player_id):
    return f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{int(player_id)}.png"

# --- Data Loading ---
@st.cache_data
def load_data():
    file_path = 'nba_data_live.csv'
    if not os.path.exists(file_path):
        return None
    
    df = pd.read_csv(file_path)
    
    if 'GAME_DATE' in df.columns:
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    
    # Ensure numeric columns
    cols_to_numeric = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'MIN', 'GAME_SCORE', 'TS_PCT', 'PLAYER_ID', 'FGA', 'FTA', 'TOV', 'PF']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Create cleaner date string column for display
    df['Date_Str'] = df['GAME_DATE'].dt.strftime('%Y-%m-%d')
    
    return df

df = load_data()

# --- HEADER ---
c_logo, c_title = st.columns([1, 15])
with c_logo:
    st.write("🏀")
with c_title:
    st.title("StatPulse Pro: The Database")

if df is None:
    st.error("Data missing! Please wait for the nightly update.")
    st.stop()

# --- MAIN TABS ---
tabs = st.tabs(["🔎 Game Finder", "👤 Player Reference", "⚔️ Versus Comparison", "🔥 Streak Lab", "🏆 Record Book"])

# ==========================================
# TAB 1: GAME FINDER
# ==========================================
with tabs[0]:
    # --- Top Bar Filters ---
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            all_seasons = sorted(df['SEASON_ID'].unique(), reverse=True) if 'SEASON_ID' in df.columns else []
            sel_seasons = st.multiselect("Select Season(s)", all_seasons, default=all_seasons[:1], key="gf_season")
        with c2:
            teams = sorted(df['TEAM_ABBREVIATION'].unique())
            sel_team = st.multiselect("Filter Team", teams, key="gf_team")
        with c3:
            opps = sorted(df['OPPONENT'].unique()) if 'OPPONENT' in df.columns else []
            sel_opp = st.multiselect("Filter Opponent", opps, key="gf_opp")

    # Filter Data
    gf_df = df.copy()
    if sel_seasons: gf_df = gf_df[gf_df['SEASON_ID'].isin(sel_seasons)]
    if sel_team: gf_df = gf_df[gf_df['TEAM_ABBREVIATION'].isin(sel_team)]
    if sel_opp: gf_df = gf_df[gf_df['OPPONENT'].isin(sel_opp)]

    st.markdown("---")
    
    # --- Stat Inputs ---
    c_s1, c_s2, c_s3, c_s4 = st.columns(4)
    with c_s1: min_pts = st.number_input("Min Points", 0, 100, 30)
    with c_s2: min_ast = st.number_input("Min Assists", 0, 50, 0)
    with c_s3: min_reb = st.number_input("Min Rebounds", 0, 50, 0)
    with c_s4: min_gmsc = st.number_input("Min GameScore", 0.0, 100.0, 0.0)

    # Apply Logic
    res = gf_df[
        (gf_df['PTS'] >= min_pts) & 
        (gf_df['AST'] >= min_ast) & 
        (gf_df['REB'] >= min_reb) & 
        (gf_df['GAME_SCORE'] >= min_gmsc)
    ]
    
    st.success(f"Found {len(res)} games.")
    
    # Display Table (Clean Dates)
    cols_show = ['Date_Str', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'OPPONENT', 'WL', 'PTS', 'REB', 'AST', 'GAME_SCORE', 'TS_PCT']
    st.dataframe(
        res[cols_show].sort_values('PTS', ascending=False).head(100),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date_Str": st.column_config.TextColumn("Date"),
            "TS_PCT": st.column_config.NumberColumn("TS%", format="%.1f%%"),
            "GAME_SCORE": st.column_config.NumberColumn("GmSc", format="%.1f")
        }
    )

# ==========================================
# TAB 2: PLAYER REFERENCE (BBREF STYLE)
# ==========================================
with tabs[1]:
    # Top Bar
    all_players = sorted(df['PLAYER_NAME'].unique())
    col_sel, col_season = st.columns([2, 2])
    with col_sel:
        p_sel = st.selectbox("Search Player", all_players, index=0)
    with col_season:
        p_seasons_avail = sorted(df[df['PLAYER_NAME'] == p_sel]['SEASON_ID'].unique(), reverse=True)
        p_season = st.multiselect("Filter Season (Optional)", p_seasons_avail, default=p_seasons_avail)

    # Filter
    p_data = df[df['PLAYER_NAME'] == p_sel].copy()
    if p_season:
        p_data = p_data[p_data['SEASON_ID'].isin(p_season)]
    
    p_data = p_data.sort_values('GAME_DATE', ascending=False)
    
    if not p_data.empty:
        # --- BIO HEADER ---
        c_img, c_bio, c_car = st.columns([1, 2, 3])
        with c_img:
            st.image(get_headshot_url(p_data.iloc[0]['PLAYER_ID']))
        with c_bio:
            st.markdown(f"## {p_sel}")
            st.markdown(f"**Team:** {p_data.iloc[0]['TEAM_ABBREVIATION']}")
            st.markdown(f"**Position:** G/F (Est.)") 
        with c_car:
            # Career Totals (in DB)
            games = len(p_data)
            pts = p_data['PTS'].sum()
            wins = len(p_data[p_data['WL']=='W'])
            win_pct = (wins/games)*100 if games > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Games", games)
            m2.metric("Total PTS", int(pts))
            m3.metric("Win %", f"{win_pct:.1f}%")

        st.divider()

        # --- STATS TABLES ---
        t1, t2 = st.tabs(["Regular Stats", "Advanced Splits"])
        
        with t1:
            st.markdown("### 📊 Per Game Stats (By Season)")
            # Exclude non-numeric columns explicitly for mean calculation
            numeric_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'MIN', 'TS_PCT', 'GAME_SCORE']
            season_avg = p_data.groupby('SEASON_ID')[numeric_cols].mean()
            st.dataframe(season_avg.style.format("{:.1f}"), use_container_width=True)
            
            st.markdown("### 🗓️ Recent Game Log")
            st.dataframe(
                p_data[['Date_Str', 'OPPONENT', 'WL', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TS_PCT']].head(10),
                use_container_width=True, hide_index=True
            )

        with t2:
            # Create a numeric Win column (1 for W, 0 for L) specifically for averaging
            p_data['WIN_VAL'] = p_data['WL'].apply(lambda x: 1 if x == 'W' else 0)

            st.markdown("### 🏠 Home vs Away Splits")
            # Now we use WIN_VAL instead of WL for the average
            split_loc = p_data.groupby('LOCATION')[['PTS', 'REB', 'AST', 'TS_PCT', 'WIN_VAL']].mean()
            # Rename WIN_VAL to Win% and multiply by 100 for display
            split_loc['Win%'] = split_loc['WIN_VAL'] * 100
            split_loc = split_loc.drop(columns=['WIN_VAL'])
            
            st.dataframe(split_loc.style.format("{:.1f}"), use_container_width=True)

            st.markdown("### ✅ Win vs Loss Splits")
            # For this split, we group BY 'WL', so we don't need to average it (it's the index)
            split_wl = p_data.groupby('WL')[['PTS', 'REB', 'AST', 'TS_PCT']].mean()
            st.dataframe(split_wl.style.format("{:.1f}"), use_container_width=True)

# ==========================================
# TAB 3: VERSUS COMPARISON (Expanded)
# ==========================================
with tabs[2]:
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1: 
        p1 = st.selectbox("Player A", all_players, index=0, key="vs_1")
    with c2:
        # Choose seasons for comparison
        vs_seasons = st.multiselect("Seasons", all_seasons, default=all_seasons[:1], key="vs_seas")
    with c3: 
        p2 = st.selectbox("Player B", all_players, index=1, key="vs_2")

    # Filter
    d1 = df[(df['PLAYER_NAME'] == p1) & (df['SEASON_ID'].isin(vs_seasons))]
    d2 = df[(df['PLAYER_NAME'] == p2) & (df['SEASON_ID'].isin(vs_seasons))]
    
    if not d1.empty and not d2.empty:
        # Images
        ic1, ic2 = st.columns(2)
        with ic1: st.image(get_headshot_url(d1.iloc[0]['PLAYER_ID']), width=150)
        with ic2: st.image(get_headshot_url(d2.iloc[0]['PLAYER_ID']), width=150)
        
        st.divider()

        # Detailed Comparison Table
        def get_stats(d):
            return {
                'GP': len(d),
                'PTS': d['PTS'].mean(),
                'REB': d['REB'].mean(),
                'AST': d['AST'].mean(),
                'STL': d['STL'].mean(),
                'BLK': d['BLK'].mean(),
                'TOV': d['TOV'].mean(),
                'TS%': d['TS_PCT'].mean(),
                'GmSc': d['GAME_SCORE'].mean(),
                'Win%': (len(d[d['WL']=='W']) / len(d)) * 100
            }
        
        s1 = get_stats(d1)
        s2 = get_stats(d2)
        
        comp_data = {
            'Metric': ['Games Played', 'Points (PTS)', 'Rebounds (REB)', 'Assists (AST)', 'Steals (STL)', 'Blocks (BLK)', 'Turnovers (TOV)', 'True Shooting (TS%)', 'Game Score', 'Win Percentage'],
            f'{p1}': [s1['GP'], s1['PTS'], s1['REB'], s1['AST'], s1['STL'], s1['BLK'], s1['TOV'], s1['TS%'], s1['GmSc'], s1['Win%']],
            f'{p2}': [s2['GP'], s2['PTS'], s2['REB'], s2['AST'], s2['STL'], s2['BLK'], s2['TOV'], s2['TS%'], s2['GmSc'], s2['Win%']]
        }
        
        comp_df = pd.DataFrame(comp_data).set_index('Metric')
        st.dataframe(comp_df.style.format("{:.1f}"), use_container_width=True, height=400)

# ==========================================
# TAB 4: STREAK LAB (Fix: Unique Columns)
# ==========================================
with tabs[3]:
    st.subheader("🔥 Streak Lab: Consecutive Games")
    
    # Controls
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1: streak_stat = st.selectbox("Statistic", ["PTS", "AST", "REB", "STL", "BLK", "GAME_SCORE"])
    with sc2: streak_val = st.number_input("Threshold (>=)", min_value=1, value=30)
    with sc3: min_len = st.number_input("Min Streak Length", min_value=2, value=3)
    with sc4: streak_mode = st.radio("Mode", ["All Time", "Active Streaks Only"])
    
    if st.button("🔎 Search Streaks"):
        # TIKUN: Avoid duplicate columns if streak_stat is 'PTS', 'AST' or 'REB'
        target_cols = ['PLAYER_NAME', 'GAME_DATE', 'Date_Str', 'WL', streak_stat]
        # Add context columns only if they are not already the target stat
        if 'PTS' not in target_cols: target_cols.append('PTS')
        if 'AST' not in target_cols: target_cols.append('AST')
        if 'REB' not in target_cols: target_cols.append('REB')

        # Select unique columns and copy
        s_df = df[target_cols].sort_values(['PLAYER_NAME', 'GAME_DATE']).copy()
        
        # Identify games meeting criteria
        s_df['is_hit'] = s_df[streak_stat] >= streak_val
        
        # Create groups for consecutive hits
        hits = s_df[s_df['is_hit']].copy()
        
        # 'Shift' logic to find consecutive groups
        s_df['grp'] = (s_df['is_hit'] != s_df['is_hit'].shift()).cumsum()
        s_df = s_df[s_df['is_hit']] # Keep only hits
        
        # Aggregation
        streaks = s_df.groupby(['PLAYER_NAME', 'grp']).agg(
            Length=('GAME_DATE', 'count'),
            Start_Date=('Date_Str', 'first'),
            End_Date=('Date_Str', 'last'),
            Avg_Stat=(streak_stat, 'mean'),
            Wins=('WL', lambda x: (x=='W').sum()),
            Last_Game_Date=('GAME_DATE', 'last')
        ).reset_index()
        
        # Filter by min length
        streaks = streaks[streaks['Length'] >= min_len]
        
        # Active Logic
        if streak_mode == "Active Streaks Only":
            last_games = df.groupby('PLAYER_NAME')['GAME_DATE'].max().reset_index()
            streaks = streaks.merge(last_games, on='PLAYER_NAME', suffixes=('', '_max'))
            streaks = streaks[streaks['Last_Game_Date'] == streaks['GAME_DATE_max']]
        
        # Sort and Display
        streaks = streaks.sort_values(['Length', 'Avg_Stat'], ascending=[False, False])
        
        st.markdown(f"### Results: {streak_val}+ {streak_stat}")
        
        display_cols = ['PLAYER_NAME', 'Length', 'Start_Date', 'End_Date', 'Avg_Stat', 'Wins']
        st.dataframe(
            streaks[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Avg_Stat": st.column_config.NumberColumn(f"Avg {streak_stat}", format="%.1f"),
                "Wins": st.column_config.NumberColumn("Wins in Streak")
            }
        )

# ==========================================
# TAB 5: RECORD BOOK (Lists)
# ==========================================
with tabs[4]:
    st.subheader("🏆 League Records (Loaded Data)")
    
    # Choose Season for records
    rec_season = st.selectbox("Season", ["All Time"] + all_seasons)
    rec_df = df if rec_season == "All Time" else df[df['SEASON_ID'] == rec_season]
    
    col_pts, col_ast, col_reb = st.columns(3)
    
    def show_leaderboard(title, col_name, emoji):
        st.markdown(f"#### {emoji} {title}")
        leaders = rec_df.nlargest(10, col_name)[['Date_Str', 'PLAYER_NAME', 'OPPONENT', col_name]]
        st.dataframe(leaders, use_container_width=True, hide_index=True)

    with col_pts: show_leaderboard("Points", "PTS", "🏀")
    with col_ast: show_leaderboard("Assists", "AST", "🅰️")
    with col_reb: show_leaderboard("Rebounds", "REB", "💪")
    
    st.divider()
    
    col_gmsc, col_3pm = st.columns(2)
    with col_gmsc: show_leaderboard("GameScore", "GAME_SCORE", "🔥")
    # Note: 3PM not explicitly in numeric conversion, ensuring fallback
    if 'FG3M' in rec_df.columns:
         with col_3pm: show_leaderboard("3-Pointers Made", "FG3M", "👌")
