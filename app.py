import streamlit as st
import pandas as pd
import os

# --- Page Config ---
st.set_page_config(
    page_title="StatPulse Pro: Ultimate History",
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
    h1 {color: #1d428a;}
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def get_headshot_url(player_id):
    return f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{int(player_id)}.png"

# --- NEW DATA ENGINE (הלב החדש של המערכת) ---
@st.cache_data(ttl=3600)
def load_data_pro():
    # 1. הגדרת העמודות שאנחנו חייבים (חוסך זיכרון + מונע טעויות)
    required_cols = [
        'SEASON_ID', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 
        'GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 
        'STL', 'BLK', 'TOV', 'GAME_SCORE', 'FGA', 'FTA', 'MIN'
    ]

    # פונקציית עזר לטעינה בטוחה
    def safe_read(file_path):
        try:
            # טוען רק עמודות שקיימות בקובץ מתוך הרשימה שלנו
            return pd.read_csv(file_path, usecols=lambda c: c in required_cols)
        except Exception as e:
            st.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()

    # 2. טעינת הקבצים
    history_df = pd.DataFrame()
    if os.path.exists('nba_history.csv.zip'):
        history_df = safe_read('nba_history.csv.zip')

    live_df = pd.DataFrame()
    if os.path.exists('nba_current.csv'):
        live_df = safe_read('nba_current.csv')

    # 3. איחוד
    if not history_df.empty and not live_df.empty:
        df = pd.concat([history_df, live_df], ignore_index=True)
    elif not history_df.empty:
        df = history_df
    elif not live_df.empty:
        df = live_df
    else:
        return None

    # 4. ניקוי והשלמת עמודות חסרות (התיקון הקריטי!) 🛠️
    # אם עמודה כמו GAME_SCORE חסרה בגלל שהיא לא הייתה בהיסטוריה הישנה - נוסיף אותה כאפס
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0.0

    # הסרת כפילויות
    df = df.loc[:, ~df.columns.duplicated()]

    # המרת תאריכים
    if 'GAME_DATE' in df.columns:
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df['Date_Str'] = df['GAME_DATE'].dt.strftime('%Y-%m-%d')
    
    # המרה למספרים (כדי שהסינונים יעבדו)
    numeric_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'GAME_SCORE', 'MIN']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

# טעינת הנתונים
df = load_data_pro()

# --- HEADER ---
c_logo, c_title = st.columns([1, 15])
with c_logo:
    st.write("🏀")
with c_title:
    st.title("StatPulse Pro: The Database (1946-2026)")

if df is None:
    st.error("Data missing! Please upload 'nba_history.csv.zip' to GitHub.")
    st.stop()

# --- MAIN TABS (הפיצ'רים המקוריים שלך חזרו!) ---
tabs = st.tabs(["🔎 Game Finder", "👤 Player Reference", "⚔️ Versus Comparison", "🔥 Streak Lab", "🏆 Record Book"])

# ==========================================
# TAB 1: GAME FINDER
# ==========================================
with tabs[0]:
    # --- Top Bar Filters ---
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            all_seasons = sorted(df['SEASON_ID'].astype(str).unique(), reverse=True) if 'SEASON_ID' in df.columns else []
            sel_seasons = st.multiselect("Select Season(s)", all_seasons, default=all_seasons[:1], key="gf_season")
        with c2:
            teams = sorted(df['TEAM_ABBREVIATION'].astype(str).unique())
            sel_team = st.multiselect("Filter Team", teams, key="gf_team")
        with c3:
            # בדיקה אם קיימת עמודת יריב
            opps = sorted(df['MATCHUP'].apply(lambda x: x.split(' ')[-1] if isinstance(x, str) else '').unique())
            sel_opp = st.multiselect("Filter Matchup/Opponent", opps, key="gf_opp")

    # Filter Data
    gf_df = df.copy()
    if sel_seasons: gf_df = gf_df[gf_df['SEASON_ID'].isin(sel_seasons)]
    if sel_team: gf_df = gf_df[gf_df['TEAM_ABBREVIATION'].isin(sel_team)]
    
    # סינון קצת יותר חכם ליריבות (כי הנתונים ההיסטוריים לא תמיד כוללים עמודת OPPONENT נקייה)
    if sel_opp: 
        gf_df = gf_df[gf_df['MATCHUP'].str.contains('|'.join(sel_opp), na=False)]

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
    
    st.success(f"Found {len(res)} games in history.")
    
    # Display Table (Clean Dates)
    cols_show = ['Date_Str', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'GAME_SCORE']
    cols_show = [c for c in cols_show if c in res.columns]
    
    st.dataframe(
        res[cols_show].sort_values('PTS', ascending=False).head(100),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date_Str": st.column_config.TextColumn("Date"),
            "GAME_SCORE": st.column_config.NumberColumn("GmSc", format="%.1f")
        }
    )

# ==========================================
# TAB 2: PLAYER REFERENCE (BBREF STYLE)
# ==========================================
with tabs[1]:
    all_players = sorted(df['PLAYER_NAME'].dropna().unique())
    col_sel, col_season = st.columns([2, 2])
    with col_sel:
        # Default to SGA if exists
        def_idx = all_players.index("Shai Gilgeous-Alexander") if "Shai Gilgeous-Alexander" in all_players else 0
        p_sel = st.selectbox("Search Player", all_players, index=def_idx)
    with col_season:
        p_seasons_avail = sorted(df[df['PLAYER_NAME'] == p_sel]['SEASON_ID'].unique(), reverse=True)
        p_season = st.multiselect("Filter Season (Optional)", p_seasons_avail, default=None)

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
            st.markdown(f"**Current/Last Team:** {p_data.iloc[0]['TEAM_ABBREVIATION']}")
        with c_car:
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
            numeric_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'MIN', 'GAME_SCORE']
            numeric_cols = [c for c in numeric_cols if c in p_data.columns]
            season_avg = p_data.groupby('SEASON_ID')[numeric_cols].mean()
            st.dataframe(season_avg.style.format("{:.1f}"), use_container_width=True)
            
            st.markdown("### 🗓️ Recent Game Log")
            st.dataframe(
                p_data[['Date_Str', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'STL', 'BLK']].head(10),
                use_container_width=True, hide_index=True
            )

        with t2:
            p_data['WIN_VAL'] = p_data['WL'].apply(lambda x: 1 if x == 'W' else 0)
            
            # בדיקת בית/חוץ לפי ה-Matchup (כי אין עמודת LOCATION בהיסטוריה לפעמים)
            p_data['LOCATION'] = p_data['MATCHUP'].apply(lambda x: 'Home' if ' vs. ' in str(x) else 'Away')

            st.markdown("### 🏠 Home vs Away Splits")
            split_loc = p_data.groupby('LOCATION')[['PTS', 'REB', 'AST', 'WIN_VAL']].mean()
            split_loc['Win%'] = split_loc['WIN_VAL'] * 100
            st.dataframe(split_loc.drop(columns=['WIN_VAL']).style.format("{:.1f}"), use_container_width=True)

# ==========================================
# TAB 3: VERSUS COMPARISON
# ==========================================
with tabs[2]:
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1: 
        p1 = st.selectbox("Player A", all_players, index=0, key="vs_1")
    with c2:
        vs_seasons = st.multiselect("Seasons", all_seasons, default=all_seasons[:1], key="vs_seas")
    with c3: 
        p2 = st.selectbox("Player B", all_players, index=min(1, len(all_players)-1), key="vs_2")

    d1 = df[(df['PLAYER_NAME'] == p1) & (df['SEASON_ID'].isin(vs_seasons))]
    d2 = df[(df['PLAYER_NAME'] == p2) & (df['SEASON_ID'].isin(vs_seasons))]
    
    if not d1.empty and not d2.empty:
        ic1, ic2 = st.columns(2)
        with ic1: st.image(get_headshot_url(d1.iloc[0]['PLAYER_ID']), width=150)
        with ic2: st.image(get_headshot_url(d2.iloc[0]['PLAYER_ID']), width=150)
        
        st.divider()

        def get_stats(d):
            return {
                'GP': len(d),
                'PTS': d['PTS'].mean(),
                'REB': d['REB'].mean(),
                'AST': d['AST'].mean(),
                'GmSc': d['GAME_SCORE'].mean() if 'GAME_SCORE' in d else 0,
            }
        
        s1 = get_stats(d1)
        s2 = get_stats(d2)
        
        comp_data = {
            'Metric': ['Games Played', 'Points (PTS)', 'Rebounds (REB)', 'Assists (AST)', 'Game Score'],
            f'{p1}': [s1['GP'], s1['PTS'], s1['REB'], s1['AST'], s1['GmSc']],
            f'{p2}': [s2['GP'], s2['PTS'], s2['REB'], s2['AST'], s2['GmSc']]
        }
        
        comp_df = pd.DataFrame(comp_data).set_index('Metric')
        st.dataframe(comp_df.style.format("{:.1f}"), use_container_width=True)

# ==========================================
# TAB 4: STREAK LAB
# ==========================================
with tabs[3]:
    st.subheader("🔥 Streak Lab: Consecutive Games")
    
    sc1, sc2, sc3 = st.columns(3)
    with sc1: streak_stat = st.selectbox("Statistic", ["PTS", "AST", "REB", "STL", "BLK"])
    with sc2: streak_val = st.number_input("Threshold (>=)", min_value=1, value=30)
    with sc3: min_len = st.number_input("Min Streak Length", min_value=2, value=3)
    
    if st.button("🔎 Search Streaks"):
        # Select relevant columns only
        s_df = df[['PLAYER_NAME', 'GAME_DATE', 'Date_Str', 'WL', streak_stat]].copy()
        s_df = s_df.sort_values(['PLAYER_NAME', 'GAME_DATE'])
        
        # Logic
        s_df['is_hit'] = s_df[streak_stat] >= streak_val
        s_df['grp'] = (s_df['is_hit'] != s_df['is_hit'].shift()).cumsum()
        s_df = s_df[s_df['is_hit']] # Keep only hits
        
        streaks = s_df.groupby(['PLAYER_NAME', 'grp']).agg(
            Length=('GAME_DATE', 'count'),
            Start_Date=('Date_Str', 'first'),
            End_Date=('Date_Str', 'last'),
            Avg_Stat=(streak_stat, 'mean')
        ).reset_index()
        
        streaks = streaks[streaks['Length'] >= min_len].sort_values('Length', ascending=False)
        
        st.dataframe(streaks[['PLAYER_NAME', 'Length', 'Start_Date', 'End_Date', 'Avg_Stat']], use_container_width=True)

# ==========================================
# TAB 5: RECORD BOOK
# ==========================================
with tabs[4]:
    st.subheader("🏆 League Records")
    rec_season = st.selectbox("Season", ["All Time"] + all_seasons)
    
    rec_df = df if rec_season == "All Time" else df[df['SEASON_ID'] == rec_season]
    
    col_pts, col_ast, col_reb = st.columns(3)
    
    def show_leaderboard(title, col_name, emoji):
        st.markdown(f"#### {emoji} {title}")
        if col_name in rec_df.columns:
            leaders = rec_df.nlargest(10, col_name)[['Date_Str', 'PLAYER_NAME', 'MATCHUP', col_name]]
            st.dataframe(leaders, use_container_width=True, hide_index=True)

    with col_pts: show_leaderboard("Points", "PTS", "🏀")
    with col_ast: show_leaderboard("Assists", "AST", "🅰️")
    with col_reb: show_leaderboard("Rebounds", "REB", "💪")

