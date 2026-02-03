import streamlit as st
import pandas as pd
import os

# --- הגדרות עמוד ועיצוב ---
st.set_page_config(
    page_title="StatPulse Pro",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS לשיפור המראה ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    .stMetric {background-color: #ffffff; border: 1px solid #e0e0e0; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    div[data-testid="column"] {text-align: center;} 
    h1, h2, h3 {font-family: 'Helvetica Neue', sans-serif; color: #1d428a;}
</style>
""", unsafe_allow_html=True)

def get_headshot_url(player_id):
    return f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{int(player_id)}.png"

# --- מנוע נתונים משודרג ---
@st.cache_data(ttl=3600)
def load_data_v2():
    # הרחבנו את רשימת העמודות כדי שיהיה יותר דאטה בפרופיל
    required_cols = [
        'SEASON_ID', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 
        'GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 
        'STL', 'BLK', 'TOV', 'GAME_SCORE', 'FGA', 'FGM', 'FG3M', 'FG3A', 'FTA', 'FTM', 'MIN', 'PLUS_MINUS'
    ]

    def safe_read(file_path):
        try:
            return pd.read_csv(file_path, usecols=lambda c: c in required_cols)
        except:
            return pd.DataFrame()

    # טעינה כפולה
    history = safe_read('nba_history.csv.zip')
    live = safe_read('nba_current.csv') # וודא שהרצת את ה-Action בגיטאהב!

    if not history.empty and not live.empty:
        df = pd.concat([history, live], ignore_index=True)
    elif not history.empty:
        df = history
    elif not live.empty:
        df = live
    else:
        return None

    # השלמת חוסרים לנתונים היסטוריים (למשל פלוס מינוס שלא היה קיים פעם)
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    df = df.loc[:, ~df.columns.duplicated()]

    # המרות סוגים
    if 'GAME_DATE' in df.columns:
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df['Date_Str'] = df['GAME_DATE'].dt.strftime('%Y-%m-%d') # תאריך יפה
    
    numeric_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'GAME_SCORE', 'FGA', 'FGM', 'FG3A', 'FG3M', 'FTA', 'FTM', 'MIN']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- חישוב אחוזים (Feature Engineering) ---
    # מונעים חילוק באפס
    df['FG_PCT'] = df.apply(lambda x: (x['FGM'] / x['FGA'] * 100) if x['FGA'] > 0 else 0, axis=1)
    df['FG3_PCT'] = df.apply(lambda x: (x['FG3M'] / x['FG3A'] * 100) if x['FG3A'] > 0 else 0, axis=1)
    df['FT_PCT'] = df.apply(lambda x: (x['FTM'] / x['FTA'] * 100) if x['FTA'] > 0 else 0, axis=1)

    return df

df = load_data_v2()

# --- HEADER ---
c1, c2 = st.columns([1, 10])
with c1: st.write("🏀")
with c2: st.title("StatPulse Pro: The Database")

if df is None:
    st.error("Data Missing. Please ensure GitHub Actions has run correctly.")
    st.stop()

# --- TABS ---
tabs = st.tabs(["🔎 Game Finder", "👤 Player Profile", "⚔️ Head-to-Head", "🔥 Streaks", "🏆 Records"])

# ==========================================
# 1. GAME FINDER (FIXED SORTING & UI)
# ==========================================
with tabs[0]:
    # Filters
    with st.expander("Filter Options", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            all_seasons = sorted(df['SEASON_ID'].astype(str).unique(), reverse=True)
            sel_seasons = st.multiselect("Season", all_seasons, default=all_seasons[:1])
        with c2:
            teams = sorted(df['TEAM_ABBREVIATION'].astype(str).unique())
            sel_team = st.multiselect("Team", teams)
        with c3:
            opps = sorted(df['MATCHUP'].astype(str).unique())
            sel_opp = st.multiselect("Opponent", opps[:100]) # Limiting list for speed

    # Logic
    gf_df = df.copy()
    if sel_seasons: gf_df = gf_df[gf_df['SEASON_ID'].isin(sel_seasons)]
    if sel_team: gf_df = gf_df[gf_df['TEAM_ABBREVIATION'].isin(sel_team)]
    
    st.markdown("---")
    
    # Stats Inputs
    c1, c2, c3, c4 = st.columns(4)
    with c1: min_pts = st.number_input("Min Points", 0, 100, 30)
    with c2: min_ast = st.number_input("Min Assists", 0, 50, 0)
    with c3: min_reb = st.number_input("Min Rebounds", 0, 50, 0)
    with c4: sort_order = st.selectbox("Sort Results By", ["Points (High to Low)", "Date (Newest)", "Date (Oldest)"])

    # Filtering
    res = gf_df[
        (gf_df['PTS'] >= min_pts) & 
        (gf_df['AST'] >= min_ast) & 
        (gf_df['REB'] >= min_reb)
    ]

    # Sorting Logic Fix
    if sort_order == "Points (High to Low)":
        res = res.sort_values('PTS', ascending=False)
    elif sort_order == "Date (Newest)":
        res = res.sort_values('GAME_DATE', ascending=False)
    else:
        res = res.sort_values('GAME_DATE', ascending=True)

    st.success(f"Found {len(res)} games matching criteria.")

    # Clean Table Display
    cols_show = ['Date_Str', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'FG_PCT', 'FG3M', 'GAME_SCORE']
    
    st.dataframe(
        res[cols_show].head(1000), # Showing top 1000 to avoid "missing 20 points" issue
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date_Str": "Date",
            "PLAYER_NAME": "Player",
            "TEAM_ABBREVIATION": "Team",
            "MATCHUP": "Matchup",
            "WL": "W/L",
            "FG_PCT": st.column_config.NumberColumn("FG%", format="%.1f%%"),
            "GAME_SCORE": st.column_config.NumberColumn("GmSc", format="%.1f")
        }
    )

# ==========================================
# 2. PLAYER PROFILE (ENRICHED)
# ==========================================
with tabs[1]:
    all_players = sorted(df['PLAYER_NAME'].dropna().unique())
    col_search, _ = st.columns([1, 2])
    with col_search:
        p_sel = st.selectbox("Select Player", all_players, index=all_players.index("Shai Gilgeous-Alexander") if "Shai Gilgeous-Alexander" in all_players else 0)

    p_data = df[df['PLAYER_NAME'] == p_sel].sort_values('GAME_DATE', ascending=False)
    
    if not p_data.empty:
        # Header with Image
        c_img, c_stats = st.columns([1, 4])
        with c_img:
            st.image(get_headshot_url(p_data.iloc[0]['PLAYER_ID']))
            st.caption(f"Team: {p_data.iloc[0]['TEAM_ABBREVIATION']}")
        
        with c_stats:
            # Career Totals Summary
            tot_gp = len(p_data)
            tot_pts = p_data['PTS'].sum()
            avg_pts = p_data['PTS'].mean()
            avg_reb = p_data['REB'].mean()
            avg_ast = p_data['AST'].mean()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Games Played", tot_gp)
            m2.metric("PPG", f"{avg_pts:.1f}")
            m3.metric("RPG", f"{avg_reb:.1f}")
            m4.metric("APG", f"{avg_ast:.1f}")
        
        st.divider()

        # Detailed Season Stats Table
        st.subheader("📊 Season Averages")
        season_stats = p_data.groupby('SEASON_ID').agg({
            'PTS': 'mean', 'REB': 'mean', 'AST': 'mean', 'STL': 'mean', 'BLK': 'mean',
            'FG_PCT': 'mean', 'FG3_PCT': 'mean', 'FT_PCT': 'mean', 'MIN': 'mean', 'GAME_SCORE': 'mean'
        }).sort_index(ascending=False)
        
        st.dataframe(
            season_stats,
            use_container_width=True,
            column_config={
                "FG_PCT": st.column_config.NumberColumn("FG%", format="%.1f%%"),
                "FG3_PCT": st.column_config.NumberColumn("3P%", format="%.1f%%"),
                "FT_PCT": st.column_config.NumberColumn("FT%", format="%.1f%%"),
                "GAME_SCORE": st.column_config.NumberColumn("GmSc", format="%.1f")
            }
        )

        st.subheader("📋 Last 10 Games")
        st.dataframe(
            p_data[['Date_Str', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT', 'FG3M']].head(10),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date_Str": "Date",
                "FG_PCT": st.column_config.NumberColumn("FG%", format="%.1f%%")
            }
        )

# ==========================================
# 3. HEAD TO HEAD (BEAUTIFUL)
# ==========================================
with tabs[2]:
    c1, c2, c3 = st.columns([1, 0.2, 1])
    
    with c1:
        p1 = st.selectbox("Player 1", all_players, index=0)
        img1 = get_headshot_url(df[df['PLAYER_NAME'] == p1].iloc[0]['PLAYER_ID'])
        st.image(img1, width=200)
        
    with c3:
        p2 = st.selectbox("Player 2", all_players, index=1)
        img2 = get_headshot_url(df[df['PLAYER_NAME'] == p2].iloc[0]['PLAYER_ID'])
        st.image(img2, width=200)

    # Calculation
    d1 = df[df['PLAYER_NAME'] == p1]
    d2 = df[df['PLAYER_NAME'] == p2]

    # Comparison Table
    st.divider()
    st.markdown("<h3 style='text-align: center'>Career Averages Comparison</h3>", unsafe_allow_html=True)
    
    stats_list = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT', 'FG3_PCT', 'GAME_SCORE']
    
    comp_data = []
    for stat in stats_list:
        v1 = d1[stat].mean()
        v2 = d2[stat].mean()
        diff = v1 - v2
        winner = p1 if v1 > v2 else p2
        comp_data.append({
            "Stat": stat,
            f"{p1}": f"{v1:.1f}",
            f"{p2}": f"{v2:.1f}",
            "Diff": f"{abs(diff):.1f}"
        })
    
    comp_df = pd.DataFrame(comp_data)
    st.dataframe(
        comp_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stat": st.column_config.TextColumn("Category", width="medium"),
        }
    )

# ==========================================
# 4. STREAKS (UNCHANGED BUT CLEANER)
# ==========================================
with tabs[3]:
    st.subheader("🔥 Streak Finder")
    # (אותו לוגיקה אבל עם תצוגה נקייה יותר)
    c1, c2, c3 = st.columns(3)
    with c1: stat = st.selectbox("Stat", ['PTS', 'AST', 'REB', 'STL', 'BLK'])
    with c2: thresh = st.number_input("Threshold", value=30)
    with c3: length = st.number_input("Min Games", value=3)

    if st.button("Find Streaks"):
        # (מטעמי מקום השארתי את הלוגיקה זהה, רק שים לב לשינוי התצוגה למטה)
        s_df = df.sort_values(['PLAYER_NAME', 'GAME_DATE'])
        s_df['is_hit'] = s_df[stat] >= thresh
        s_df['grp'] = (s_df['is_hit'] != s_df['is_hit'].shift()).cumsum()
        s_df = s_df[s_df['is_hit']]
        
        res = s_df.groupby(['PLAYER_NAME', 'grp']).agg(
            Games=('GAME_DATE', 'count'),
            Start=('Date_Str', 'first'),
            End=('Date_Str', 'last'),
            Avg=('PTS', 'mean')
        ).reset_index()
        
        res = res[res['Games'] >= length].sort_values('Games', ascending=False)
        
        st.dataframe(
            res[['PLAYER_NAME', 'Games', 'Start', 'End', 'Avg']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "PLAYER_NAME": "Player",
                "Avg": st.column_config.NumberColumn("Avg During Streak", format="%.1f")
            }
        )

# ==========================================
# 5. RECORDS
# ==========================================
with tabs[4]:
    st.subheader("🏆 All-Time Single Game Leaders")
    # טבלאות נקיות
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Points")
        st.dataframe(df.nlargest(10, 'PTS')[['Date_Str', 'PLAYER_NAME', 'PTS']], hide_index=True, use_container_width=True)
    with col2:
        st.markdown("#### Assists")
        st.dataframe(df.nlargest(10, 'AST')[['Date_Str', 'PLAYER_NAME', 'AST']], hide_index=True, use_container_width=True)
