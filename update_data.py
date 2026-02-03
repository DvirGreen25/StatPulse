# update_data.py - הסקריפט שרץ כל בוקר ומביא רק את העונה החיה
from nba_api.stats.endpoints import leaguegamelog
import pandas as pd
import time
from datetime import datetime

# --- חישוב אוטומטי של העונה הנוכחית ---
# אנחנו רוצים שהבוט ידע לבד איזו עונה להוריד
now = datetime.now()

# אם אנחנו בחודשים 10-12 (תחילת עונה), השנה היא השנה הנוכחית
# אם אנחנו בחודשים 1-9 (אמצע/סוף עונה), העונה התחילה בשנה שעברה
if now.month >= 10:
    start_year = now.year
else:
    start_year = now.year - 1

season_str = f'{start_year}-{str(start_year+1)[-2:]}' # יוצר למשל "2025-26"

print(f"--- 🔄 Daily Update Started for Season: {season_str} ---")

all_data = []
season_types = ['Regular Season', 'Playoffs']

for s_type in season_types:
    try:
        print(f"Fetching {s_type}...")
        log = leaguegamelog.LeagueGameLog(
            season=season_str, 
            season_type_all_star=s_type, 
            player_or_team_abbreviation='P'
        )
        df_temp = log.get_data_frames()[0]
        
        if not df_temp.empty:
            df_temp['SEASON_ID'] = season_str
            # חשוב: להוסיף את סוג העונה כדי שיתאים לקובץ ההיסטוריה
            df_temp['SEASON_TYPE'] = 'Playoffs' if 'Playoffs' in s_type else 'Regular'
            all_data.append(df_temp)
            
        time.sleep(0.5)
    except Exception as e:
        print(f"Note: {s_type} data not available yet (or error: {e})")

if all_data:
    df = pd.concat(all_data, ignore_index=True)
    
    # שמירה לקובץ נפרד - 'nba_current.csv'
    # שים לב: אנחנו שומרים CSV רגיל (לא ZIP) כי זה קובץ קטן יחסית
    output_file = 'nba_current.csv'
    
    # סינון עמודות כדי שיהיה תואם להיסטוריה
    cols_to_keep = ['SEASON_ID', 'SEASON_TYPE', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 
                    'GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'STL', 'BLK', 
                    'TOV', 'FGA', 'FTA', 'MIN', 'GAME_SCORE', 'FG3M']
    
    # (שמירה רק של עמודות שקיימות בפועל)
    available_cols = [c for c in cols_to_keep if c in df.columns]
    df = df[available_cols]

    df.to_csv(output_file, index=False)
    print(f"✅ SUCCESS! Updated {output_file} with {len(df)} games from {season_str}.")
else:
    print("⚠️ No games found. Is the season active?")
