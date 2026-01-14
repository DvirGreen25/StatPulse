# fetch_history.py - הרצה חד פעמית במחשב
from nba_api.stats.endpoints import leaguegamelog
import pandas as pd
import time
import os

start_year = 2000  # התחלה בטוחה
end_year = 2024    # עד העונה הקודמת (לא כולל הנוכחית)

print(f"--- Downloading History Archive ({start_year}-{end_year}) ---")

all_data = []
season_types = ['Regular Season', 'Playoffs']

for year in range(start_year, end_year + 1):
    season_str = f'{year}-{str(year+1)[-2:]}'
    print(f"Archiving {season_str}...")
    
    for s_type in season_types:
        try:
            log = leaguegamelog.LeagueGameLog(
                season=season_str, 
                season_type_all_star=s_type, 
                player_or_team_abbreviation='P'
            )
            df_temp = log.get_data_frames()[0]
            if not df_temp.empty:
                df_temp['SEASON_ID'] = season_str
                all_data.append(df_temp)
            time.sleep(0.6) # Delay to keep NBA happy
        except Exception as e:
            print(f"Error {season_str}: {e}")

if all_data:
    df = pd.concat(all_data, ignore_index=True)
    
    # ניקוי בסיסי כבר כאן כדי לחסוך מקום
    cols_to_keep = ['SEASON_ID', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 
                    'GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'STL', 'BLK', 
                    'TOV', 'FGA', 'FTA', 'MIN', 'PF'] # שומרים רק מה שחשוב
    
    # מסננים עמודות שלא קיימות
    available_cols = [c for c in cols_to_keep if c in df.columns]
    df = df[available_cols]

    df.to_csv('nba_history.csv', index=False)
    print(f"DONE! Saved nba_history.csv with {len(df)} games.")
else:
    print("No data fetched.")
