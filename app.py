import streamlit as st
import pandas as pd
import os

# --- Page Config ---
st.set_page_config(page_title="StatPulse Pro V3", page_icon="🏀", layout="wide")

# --- Static Data: 30 Active Teams Mapping ---
TEAMS = {
    'ATL': {'name': 'Atlanta Hawks', 'id': '1610612737'}, 'BOS': {'name': 'Boston Celtics', 'id': '1610612738'},
    'BKN': {'name': 'Brooklyn Nets', 'id': '1610612751'}, 'CHA': {'name': 'Charlotte Hornets', 'id': '1610612766'},
    'CHI': {'name': 'Chicago Bulls', 'id': '1610612741'}, 'CLE': {'name': 'Cleveland Cavaliers', 'id': '1610612739'},
    'DAL': {'name': 'Dallas Mavericks', 'id': '1610612742'}, 'DEN': {'name': 'Denver Nuggets', 'id': '1610612743'},
    'DET': {'name': 'Detroit Pistons', 'id': '1610612765'}, 'GSW': {'name': 'Golden State Warriors', 'id': '1610612744'},
    'HOU': {'name': 'Houston Rockets', 'id': '1610612745'}, 'IND': {'name': 'Indiana Pacers', 'id': '1610612754'},
    'LAC': {'name': 'LA Clippers', 'id': '1610612746'}, 'LAL': {'name': 'Los Angeles Lakers', 'id': '1610612747'},
    'MEM': {'name': 'Memphis Grizzlies', 'id': '1610612763'}, 'MIA': {'name': 'Miami Heat', 'id': '1610612748'},
    'MIL': {'name': 'Milwaukee Bucks', 'id': '1610612749'}, 'MIN': {'name': 'Minnesota Timberwolves', 'id': '1610612750'},
    'NOP': {'name': 'New Orleans Pelicans', 'id': '1610612740'}, 'NYK': {'name': 'New York Knicks', 'id': '1610612752'},
    'OKC': {'name': 'Oklahoma City Thunder', 'id': '1610612760'}, 'ORL': {'name': 'Orlando Magic', 'id': '1610612753'},
    'PHI': {'name': 'Philadelphia 76ers', 'id': '1610612755'}, 'PHX': {'name': 'Phoenix Suns', 'id': '1610612756'},
    'POR': {'name': 'Portland Trail Blazers', 'id': '1610612757'}, 'SAC': {'name': 'Sacramento Kings', 'id': '1610612758'},
    'SAS': {'name': 'San Antonio Spurs', 'id': '1610612759'}, 'TOR': {'name': 'Toronto Raptors', 'id': '1610612761'},
    'UTA': {'name': 'Utah Jazz', 'id': '1610612762'}, 'WAS': {'name': 'Washington Wizards', 'id': '1610612764'}
}

# --- Helpers ---
def get_headshot(pid): return f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{int(pid)}.png"
def get_logo(tid): return f"https://cdn.nba.com/logos/nba/{tid}/primary/L/logo.svg"

# --- Data Engine (Defensive Loading) ---
@st.cache_data(ttl=3600)
def load_data_v3():
    req_cols = ['SEASON_ID', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FGA', 'FGM', 'FG3M', 'FG3A', 'FTA', 'FTM', 'MIN', 'PLUS_MINUS', 'PF']
    
    # Try History
    try: hist = pd.read_csv('nba_history.csv.zip')
    except: hist = pd.DataFrame()
    
    # Try Live (2025/26)
    try: live = pd.read_csv('nba_current.csv')
    except: live = pd.DataFrame()
    
    if hist.empty and live.empty: return None
    
    df = pd.concat([hist, live], ignore_index=True).drop_duplicates(subset=['PLAYER_ID', 'GAME_DATE'])
    
    # Fill missing cols with 0
    for c in req_cols:
        if c not in df.columns: df[c] = 0
    
    # Conversions
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df['Date_Str'] = df['GAME_DATE'].dt.strftime('%Y-%m-%d')
    num_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FGA', 'FGM', 'FG3M', 'FG3A', 'FTA', 'FTM', 'MIN', 'PLUS_MINUS', 'PF']
    for c in num_cols: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    # Pcts
    df['FG%'] = (df['FGM'] / df['FGA'] * 100).fillna(0)
    df['3P%'] = (df['FG3M'] / df['FG3A'] * 100).fillna(0)
    
    return df

df = load_data_v3()

# --- SIDEBAR ---
with st.sidebar:
    st.title("Settings")
    if st.button("🔄 Hard Reset (Update 2026)"):
        st.cache_data.clear()
        st.rerun()
    if df is not None:
        has_2026 = any(df['SEASON_ID'].astype(str).str.contains('2025-26'))
        if has_2026: st.success("Season 2025/26 Loaded")
        else: st.warning("Season 2025/26 File Missing")

# --- MAIN TABS ---
if df is None:
    st.error("No data found! Please upload 'nba_history.csv.zip' to GitHub.")
    st.stop()

tabs = st.tabs(["🔎 Game Finder", "👤 Player Profile", "⚔️ Head-to-Head", "🔥 Streak Pro", "🏆 Record Index"])

# 1. GAME FINDER
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_seas = st.multiselect("Season", sorted(df['SEASON_ID'].astype(str).unique(), reverse=True))
    with c2:
        sel_team = st.multiselect("Team", options=list(TEAMS.keys()), format_func=lambda x: TEAMS[x]['name'])
    with c3:
        min_pts = st.number_input("Min Points", 0, 100, 20)
    
    with st.expander("Advanced Filters"):
        a1, a2, a3 = st.columns(3)
        with a1: min_ast = st.number_input("Min Assists", 0, 30, 0)
        with a2: min_reb = st.number_input("Min Rebounds", 0, 30, 0)
        with a3: min_pm = st.number_input("Min Plus/Minus", -50, 50, -50)

    res = df.copy()
    if sel_seas: res = res[res['SEASON_ID'].isin(sel_seas)]
    if sel_team: res = res[res['TEAM_ABBREVIATION'].isin(sel_team)]
    res = res[(res['PTS'] >= min_pts) & (res['AST'] >= min_ast) & (res['REB'] >= min_reb) & (res['PLUS_MINUS'] >= min_pm)]
    
    # Display with logos in sidebar or header (optional), keeping table clean
    st.dataframe(res[['Date_Str', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'PLUS_MINUS']].sort_values('PTS', ascending=False), use_container_width=True, hide_index=True)

# 2. PLAYER PROFILE
with tabs[1]:
    p_list = sorted(df['PLAYER_NAME'].dropna().unique())
    p_sel = st.selectbox("Search Player", p_list, index=p_list.index("Shai Gilgeous-Alexander") if "Shai Gilgeous-Alexander" in p_list else 0)
    p_df = df[df['PLAYER_NAME'] == p_sel].sort_values('GAME_DATE', ascending=False)
    
    c_img, c_bio = st.columns([1, 4])
    with c_img: st.image(get_headshot(p_df.iloc[0]['PLAYER_ID']))
    with c_bio: 
        t_abbr = p_df.iloc[0]['TEAM_ABBREVIATION']
        if t_abbr in TEAMS: st.image(get_logo(TEAMS[t_abbr]['id']), width=60)
        st.title(p_sel)

    view = st.radio("Section", ["Overview", "Game Logs", "Splits"], horizontal=True)
    if view == "Overview":
        st.table(p_df.groupby('SEASON_ID')[['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG%', 'MIN', 'PLUS_MINUS']].mean().sort_index(ascending=False).style.format("{:.1f}"))
    elif view == "Game Logs":
        st.dataframe(p_df[['Date_Str', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'MIN', 'PLUS_MINUS']], use_container_width=True, hide_index=True)
    elif view == "Splits":
        p_df['LOC'] = p_df['MATCHUP'].apply(lambda x: 'Home' if 'vs.' in x else 'Away')
        st.table(p_df.groupby('LOC')[['PTS', 'REB', 'AST', 'FG%']].mean().style.format("{:.1f}"))

# 3. HEAD TO HEAD
with tabs[2]:
    col1, col_vs, col2 = st.columns([2, 1, 2])
    with col1:
        p1 = st.selectbox("Player A", p_list, key="h1")
        st.image(get_headshot(df[df['PLAYER_NAME'] == p1].iloc[0]['PLAYER_ID']), width=150)
    with col2:
        p2 = st.selectbox("Player B", p_list, key="h2")
        st.image(get_headshot(df[df['PLAYER_NAME'] == p2].iloc[0]['PLAYER_ID']), width=150)

    d1, d2 = df[df['PLAYER_NAME'] == p1], df[df['PLAYER_NAME'] == p2]
    metrics = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG%', '3P%', 'MIN', 'PLUS_MINUS']
    comp = []
    for m in metrics:
        v1, v2 = d1[m].mean(), d2[m].mean()
        win = p1 if v1 > v2 else p2
        comp.append({"Metric": m, p1: f"{v1:.1f}", p2: f"{v2:.1f}", "Winner": win, "Diff": abs(v1-v2)})
    
    st.table(pd.DataFrame(comp).set_index("Metric"))

# 4. STREAK PRO
with tabs[3]:
    c1, c2, c3 = st.columns(3)
    with c1: s1 = st.selectbox("Stat 1", ['PTS', 'AST', 'REB'], key="s1"); v1 = st.number_input("Val 1", 0, 100, 10)
    with c2: s2 = st.selectbox("Stat 2", ['None', 'PTS', 'AST', 'REB'], key="s2"); v2 = st.number_input("Val 2", 0, 100, 0)
    with c3: active_only = st.checkbox("Active Streaks Only")
    
    if st.button("Search"):
        sdf = df.sort_values(['PLAYER_NAME', 'GAME_DATE'])
        hit = (sdf[s1] >= v1)
        if s2 != 'None': hit &= (sdf[s2] >= v2)
        sdf['hit'] = hit
        sdf['grp'] = (sdf['hit'] != sdf['hit'].shift()).cumsum()
        res = sdf[sdf['hit']].groupby(['PLAYER_NAME', 'grp']).agg(Len=('GAME_DATE', 'count'), End=('GAME_DATE', 'max')).reset_index()
        if active_only:
            last_date = df.groupby('PLAYER_NAME')['GAME_DATE'].max()
            res = res[res.apply(lambda x: x['End'] == last_date[x['PLAYER_NAME']], axis=1)]
        st.dataframe(res.sort_values('Len', ascending=False), use_container_width=True, hide_index=True)

# 5. RECORD INDEX
with tabs[4]:
    mode = st.radio("Type", ["Single Game", "Season Total", "Season Avg"], horizontal=True)
    stat = st.selectbox("Category", ['PTS', 'AST', 'REB', 'STL', 'BLK'])
    
    if mode == "Single Game":
        top = df.nlargest(1, stat).iloc[0]
        st.write(f"### Record Holder: {top['PLAYER_NAME']} ({top[stat]})")
        st.dataframe(df.nlargest(100, stat)[['Date_Str', 'PLAYER_NAME', stat]], use_container_width=True, hide_index=True)
    elif mode == "Season Total":
        seas = df.groupby(['PLAYER_NAME', 'SEASON_ID'])[stat].sum().reset_index()
        st.dataframe(seas.nlargest(100, stat), use_container_width=True, hide_index=True)
