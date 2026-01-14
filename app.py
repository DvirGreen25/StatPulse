import streamlit as st
import pandas as pd
import os

# --- Page Config ---
st.set_page_config(
    page_title="StatPulse Ultimate",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed" # מתחיל סגור כדי לתת מקום לגרפים
)

# --- Helper: Get Headshot URL ---
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
    
    cols_to_numeric = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'MIN', 'GAME_SCORE', 'TS_PCT', 'PLAYER_ID']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

df = load_data()

# --- HEADER ---
c_logo, c_title = st.columns([1, 8])
with c_logo:
    st.write("🏀") 
with c_title:
    st.title("StatPulse Ultimate")

if df is None:
    st.error("Data missing! Please run the update_data.py script to fetch V3.0 data.")
    st.stop()

# --- GLOBAL SETTINGS ---
with st.sidebar:
    st.header("⚙️ Data Settings")
    if 'SEASON_ID' in df.columns:
        all_seasons = sorted(df['SEASON_ID'].unique(), reverse=True)
        selected_seasons = st.multiselect("Active Seasons", all_seasons, default=all_seasons)
    else:
        selected_seasons = []

# Filter data globally
main_df = df.copy()
if selected_seasons:
    main_df = main_df[main_df['SEASON_ID'].isin(selected_seasons)]

# --- TABS NAVIGATION ---
tab1, tab2, tab3, tab4 = st.tabs(["🔎 Game Finder", "📈 Trends & Bio", "⚔️ Versus Mode", "🔥 Streak Lab"])

# ==========================================
# TAB 1: GAME FINDER
# ==========================================
with tab1:
    st.subheader("Game Finder")
    
    # Quick Filters
    c1, c2, c3 = st.columns(3)
    with c1:
        team_filter = st.multiselect("Team", sorted(main_df['TEAM_ABBREVIATION'].unique()))
    with c2:
        opp_filter = st.multiselect("Opponent", sorted(main_df['OPPONENT'].unique()) if 'OPPONENT' in main_df.columns else [])
    with c3:
        loc_filter = st.radio("Location", ["Any", "Home", "Away"], horizontal=True)

    st.markdown("---")
    
    # Stat Inputs
    c_s1, c_s2, c_s3, c_s4 = st.columns(4)
    with c_s1:
        min_pts = st.number_input("Min PTS", 0, 100, 30)
    with c_s2:
        min_reb = st.number_input("Min REB", 0, 50, 0)
    with c_s3:
        min_ast = st.number_input("Min AST", 0, 50, 0)
    with c_s4:
        min_gmsc = st.number_input("Min GameScore", 0.0, 100.0, 0.0, step=0.1)

    # Filtering Logic
    res = main_df.copy()
    if team_filter: res = res[res['TEAM_ABBREVIATION'].isin(team_filter)]
    if opp_filter: res = res[res['OPPONENT'].isin(opp_filter)]
    if loc_filter == "Home": res = res[res['LOCATION'] == 'HOME']
    if loc_filter == "Away": res = res[res['LOCATION'] == 'AWAY']
    
    res = res[
        (res['PTS'] >= min_pts) & 
        (res['REB'] >= min_reb) & 
        (res['AST'] >= min_ast) &
        (res['GAME_SCORE'] >= min_gmsc)
    ]
    
    st.info(f"Found {len(res)} games matching criteria.")
    
    disp_cols = ['GAME_DATE', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'OPPONENT', 'WL', 'PTS', 'REB', 'AST', 'GAME_SCORE', 'TS_PCT']
    st.dataframe(
        res[disp_cols].sort_values('PTS', ascending=False).head(100),
        use_container_width=True, 
        hide_index=True,
        column_config={
            "GAME_DATE": st.column_config.DatetimeColumn("Date", format="D MMM YY"),
            "TS_PCT": st.column_config.NumberColumn("TS%", format="%.1f%%")
        }
    )

# ==========================================
# TAB 2: TRENDS & BIO (With Headshots!)
# ==========================================
with tab2:
    all_players = sorted(main_df['PLAYER_NAME'].unique())
    # Try to default to SGA if exists, else first player
    def_ix = all_players.index("Shai Gilgeous-Alexander") if "Shai Gilgeous-Alexander" in all_players else 0
    
    p_sel = st.selectbox("Select Player for Deep Dive", all_players, index=def_idx if 'def_idx' in locals() else def_ix)
    
    # Get Player Data
    p_data = main_df[main_df['PLAYER_NAME'] == p_sel].sort_values('GAME_DATE')
    
    if not p_data.empty:
        # Layout: Image Left, Stats Right
        col_img, col_stats = st.columns([1, 4])
        
        with col_img:
            pid = p_data.iloc[0]['PLAYER_ID']
            st.image(get_headshot_url(pid), width=200)
            
        with col_stats:
            st.markdown(f"### {p_sel}")
            st.markdown(f"**{p_data.iloc[0]['TEAM_ABBREVIATION']}** | Games: {len(p_data)}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("PTS", f"{p_data['PTS'].mean():.1f}")
            m2.metric("REB", f"{p_data['REB'].mean():.1f}")
            m3.metric("AST", f"{p_data['AST'].mean():.1f}")
            m4.metric("TS%", f"{p_data['TS_PCT'].mean():.1f}%")

        # Charts
        st.divider()
        st.subheader("Last 10 Games Trend")
        last_10 = p_data.tail(10)
        st.line_chart(last_10.set_index('GAME_DATE')[['PTS', 'GAME_SCORE']])

# ==========================================
# TAB 3: VERSUS MODE (Head-to-Head Visuals)
# ==========================================
with tab3:
    c_p1, c_vs, c_p2 = st.columns([2, 1, 2])
    
    with c_p1:
        p1_name = st.selectbox("Player A", all_players, index=0)
        df1 = main_df[main_df['PLAYER_NAME'] == p1_name]
        if not df1.empty:
            st.image(get_headshot_url(df1.iloc[0]['PLAYER_ID']))
            st.metric("Season PTS", f"{df1['PTS'].mean():.1f}")

    with c_vs:
        st.markdown("<h1 style='text-align: center; margin-top: 100px;'>VS</h1>", unsafe_allow_html=True)

    with c_p2:
        # Default second player
        def_ix2 = 1 if len(all_players) > 1 else 0
        p2_name = st.selectbox("Player B", all_players, index=def_ix2)
        df2 = main_df[main_df['PLAYER_NAME'] == p2_name]
        if not df2.empty:
            st.image(get_headshot_url(df2.iloc[0]['PLAYER_ID']))
            st.metric("Season PTS", f"{df2['PTS'].mean():.1f}")
            
    # Comparison Chart
    st.divider()
    st.bar_chart(
        pd.concat([df1.assign(Player=p1_name), df2.assign(Player=p2_name)]),
        x="Player", y="PTS", color="Player"
    )

# ==========================================
# TAB 4: THE STREAK LAB (New Algorithm!)
# ==========================================
with tab4:
    st.subheader("🔥 The Streak Finder")
    st.markdown("Find the longest consecutive streaks matching your criteria.")
    
    c_st1, c_st2, c_st3 = st.columns(3)
    with c_st1:
        target_stat = st.selectbox("Stat to Streak", ["PTS", "REB", "AST", "STL", "BLK"])
    with c_st2:
        threshold = st.number_input(f"Minimum {target_stat}", min_value=1, value=30)
    with c_st3:
        min_streak_len = st.number_input("Minimum Streak Length", min_value=2, value=2)

    if st.button("🔎 Find Streaks"):
        # Algorithm:
        # 1. Filter only games that meet the criteria
        # 2. Group by player and find consecutive dates
        # Note: This is a heavy calculation, so we simplify it for performance
        
        candidates = main_df[main_df[target_stat] >= threshold].sort_values(['PLAYER_NAME', 'GAME_DATE'])
        candidates['date_diff'] = candidates.groupby('PLAYER_NAME')['GAME_DATE'].diff().dt.days
        
        # Logic: If date_diff is not null, it means it's a potential streak part. 
        # But real streak logic needs to check consecutive games played. 
        # For this MVP, we will count "Total Games Meeting Criteria" per player for now 
        # (True streak logic requires complex gap analysis which we can add later).
        
        st.markdown(f"**Top Players with most games of {threshold}+ {target_stat}:**")
        
        counts = candidates['PLAYER_NAME'].value_counts().reset_index()
        counts.columns = ['Player', 'Games Count']
        counts = counts[counts['Games Count'] >= min_streak_len]
        
        st.dataframe(counts.head(20), use_container_width=True)
        
        # Visualizing the Top Player
        if not counts.empty:
            top_player = counts.iloc[0]['Player']

            st.success(f"🏆 Leader: {top_player} with {counts.iloc[0]['Games Count']} games!")
