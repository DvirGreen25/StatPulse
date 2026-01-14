import streamlit as st
import pandas as pd
import os

# --- Page Config ---
st.set_page_config(
    page_title="StatPulse Elite",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Helpers ---
def get_headshot_url(player_id):
    return f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{int(player_id)}.png"

def get_team_logo(team_abbr):
    # Dictionary mapping abbr to ID (Partial list for demo, works for main teams)
    # A cleaner way requires a full mapping, but we'll use a generic fallback or mapped IDs if possible.
    # Trick: We can try to construct the URL if we had Team IDs. 
    # Since we only have Abbr in the CSV, we'll use a placeholder or text for now, 
    # OR we can update the data fetcher to get Team IDs later.
    # For now, let's stick to a clean text representation with colors or a public logo API.
    return f"https://assets.sportsdata.io/assets/nba/logos/{team_abbr}.png" # Public placeholder API

# --- Data Loading ---
@st.cache_data
def load_data():
    file_path = 'nba_data_live.csv' # Relative path for Cloud
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
st.title("🏀 StatPulse Elite")
if df is None:
    st.error("Waiting for data... (Github Action is running)")
    st.stop()

# --- GLOBAL SETTINGS ---
with st.sidebar:
    st.header("⚙️ Data Settings")
    if 'SEASON_ID' in df.columns:
        all_seasons = sorted(df['SEASON_ID'].unique(), reverse=True)
        selected_seasons = st.multiselect("Active Seasons", all_seasons, default=all_seasons)
    else:
        selected_seasons = []

main_df = df.copy()
if selected_seasons:
    main_df = main_df[main_df['SEASON_ID'].isin(selected_seasons)]

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔎 Game Finder", "👤 Player Profile", "⚔️ Head-to-Head", "🔥 Streak Lab", "📜 Records"])

# ==========================================
# TAB 1: GAME FINDER (Classic)
# ==========================================
with tab1:
    st.subheader("Game Finder")
    c1, c2, c3, c4 = st.columns(4)
    with c1: team_filter = st.multiselect("Team", sorted(main_df['TEAM_ABBREVIATION'].unique()))
    with c2: min_pts = st.number_input("Min PTS", 0, 100, 30)
    with c3: min_ast = st.number_input("Min AST", 0, 50, 0)
    with c4: min_reb = st.number_input("Min REB", 0, 50, 0)

    res = main_df.copy()
    if team_filter: res = res[res['TEAM_ABBREVIATION'].isin(team_filter)]
    res = res[(res['PTS'] >= min_pts) & (res['AST'] >= min_ast) & (res['REB'] >= min_reb)]
    
    st.dataframe(
        res[['GAME_DATE', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'OPPONENT', 'PTS', 'REB', 'AST', 'GAME_SCORE']].sort_values('PTS', ascending=False).head(50),
        use_container_width=True, hide_index=True
    )

# ==========================================
# TAB 2: PLAYER PROFILE (The Basketball-Reference Clone)
# ==========================================
with tab2:
    all_players = sorted(main_df['PLAYER_NAME'].unique())
    p_sel = st.selectbox("Search Player", all_players, index=0)
    
    p_data = main_df[main_df['PLAYER_NAME'] == p_sel].sort_values('GAME_DATE', ascending=False)
    
    if not p_data.empty:
        pid = p_data.iloc[0]['PLAYER_ID']
        team = p_data.iloc[0]['TEAM_ABBREVIATION']
        
        # Header Section
        col_head_img, col_head_info, col_head_stats = st.columns([1, 2, 3])
        
        with col_head_img:
            st.image(get_headshot_url(pid))
        
        with col_head_info:
            st.markdown(f"## {p_sel}")
            st.markdown(f"**Team:** {team}")
            st.markdown(f"**Games Tracked:** {len(p_data)}")
        
        with col_head_stats:
            # Career (in loaded dataset) Averages
            avg_pts = p_data['PTS'].mean()
            avg_reb = p_data['REB'].mean()
            avg_ast = p_data['AST'].mean()
            best_gmsc = p_data['GAME_SCORE'].max()
            
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("AVG PTS", f"{avg_pts:.1f}")
            s2.metric("AVG REB", f"{avg_reb:.1f}")
            s3.metric("AVG AST", f"{avg_ast:.1f}")
            s4.metric("Best GmSc", f"{best_gmsc}")

        st.divider()
        
        # Split: Season Stats Table vs Last 5 Games
        c_stats, c_log = st.columns([1, 1])
        
        with c_stats:
            st.markdown("### 📊 Season Splits")
            season_stats = p_data.groupby('SEASON_ID')[['PTS', 'REB', 'AST', 'TS_PCT', 'GAME_SCORE']].mean().sort_index(ascending=False)
            st.dataframe(season_stats.style.format("{:.1f}"), use_container_width=True)

        with c_log:
            st.markdown("### 🗓️ Last 5 Games")
            st.dataframe(
                p_data[['GAME_DATE', 'OPPONENT', 'WL', 'PTS', 'REB', 'AST']].head(5),
                use_container_width=True, hide_index=True
            )
            
        # Graph
        st.markdown("### 📈 Performance Trend")
        st.line_chart(p_data.set_index('GAME_DATE')[['PTS', 'GAME_SCORE']].head(50))

# ==========================================
# TAB 3: VERSUS
# ==========================================
with tab3:
    c1, c2 = st.columns(2)
    p1 = c1.selectbox("Player A", all_players, key="v1")
    p2 = c2.selectbox("Player B", all_players, key="v2", index=1)
    
    d1 = main_df[main_df['PLAYER_NAME'] == p1]
    d2 = main_df[main_df['PLAYER_NAME'] == p2]
    
    if not d1.empty and not d2.empty:
        c1.image(get_headshot_url(d1.iloc[0]['PLAYER_ID']), width=150)
        c2.image(get_headshot_url(d2.iloc[0]['PLAYER_ID']), width=150)
        
        comp_df = pd.DataFrame({
            'Metric': ['PTS', 'REB', 'AST', 'TS%'],
            f'{p1}': [d1['PTS'].mean(), d1['REB'].mean(), d1['AST'].mean(), d1['TS_PCT'].mean()],
            f'{p2}': [d2['PTS'].mean(), d2['REB'].mean(), d2['AST'].mean(), d2['TS_PCT'].mean()]
        }).set_index('Metric')
        
        st.table(comp_df.style.format("{:.1f}"))

# ==========================================
# TAB 4: STREAK LAB
# ==========================================
with tab4:
    st.subheader("🔥 The Hot Hand")
    stat = st.selectbox("Choose Stat", ["PTS", "AST", "REB"])
    val = st.number_input(f"Value needed (e.g. 30+ {stat})", min_value=10, value=30)
    
    # Simple logic: Count total games above threshold
    leaders = main_df[main_df[stat] >= val]['PLAYER_NAME'].value_counts().head(10)
    st.bar_chart(leaders)

# ==========================================
# TAB 5: RECORDS & HISTORY
# ==========================================
with tab5:
    st.subheader("🏆 Records (In Loaded Data)")
    
    r1, r2, r3 = st.columns(3)
    
    with r1:
        max_pts = main_df.loc[main_df['PTS'].idxmax()]
        st.info(f"**Highest PTS**: {max_pts['PTS']} by {max_pts['PLAYER_NAME']}")
        st.caption(f"vs {max_pts['OPPONENT']} on {max_pts['GAME_DATE'].date()}")
        
    with r2:
        max_ast = main_df.loc[main_df['AST'].idxmax()]
        st.success(f"**Highest AST**: {max_ast['AST']} by {max_ast['PLAYER_NAME']}")
    
    with r3:
        max_gmsc = main_df.loc[main_df['GAME_SCORE'].idxmax()]
        st.warning(f"**Best GameScore**: {max_gmsc['GAME_SCORE']} by {max_gmsc['PLAYER_NAME']}")
    
    st.markdown("---")
    st.markdown("### Top 20 Performances of All Time (Loaded)")
    st.dataframe(
        main_df.nlargest(20, 'GAME_SCORE')[['GAME_DATE', 'PLAYER_NAME', 'PTS', 'REB', 'AST', 'GAME_SCORE', 'TS_PCT']],
        use_container_width=True, hide_index=True
    )
