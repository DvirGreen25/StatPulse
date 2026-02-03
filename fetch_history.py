# fetch_history.py - Run this ONCE locally
from nba_api.stats.endpoints import leaguegamelog
import pandas as pd
import time
import os

# היסטוריה מלאה!
start_year = 1946
end_year = 2024  # לא כולל העונה הנוכחית

print(f"--- 📜 Downloading NBA History Archive ({start_year}-{end_year}) ---")

all_data = []
season_types = ['Regular Season', 'Playoffs']

for year in range(start_year, end_year + 1):
    # חישוב הפורמט של העונה (למשל 1996-97)
    season_str = f'{year}-{str(year+1)[-2:]}'
    
    # טיפול באגים לשנת 1999 (שנת 2000 מסתיימת ב-00)
    if year == 1999:
        season_str = '1999-00'
        
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
                # הוספת סוג עונה (כדי שנבדיל בין פלייאוף לעונה סדירה)
                df_temp['SEASON_TYPE'] = 'Playoffs' if 'Playoffs' in s_type else 'Regular'
                all_data.append(df_temp)
            
            time.sleep(0.5) # נימוס לשרתים
        except Exception as e:
            pass # אם עונה לא קיימת (למשל בשנים הראשונות אין פלייאוף מסודר), מדלגים

if all_data:
    df = pd.concat(all_data, ignore_index=True)
    
    # שמירת עמודות קריטיות בלבד כדי לחסוך מקום
    cols_to_keep = ['SEASON_ID', 'SEASON_TYPE', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 
                    'GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'STL', 'BLK', 
                    'TOV', 'FGA', 'FTA', 'MIN', 'GAME_SCORE', 'FG3M']
    
    available_cols = [c for c in cols_to_keep if c in df.columns]
    df = df[available_cols]

    # שמירה לקובץ מכווץ (ZIP) כי הקובץ יהיה ענק!
    # פנדס יודע לשמור ולקרוא zip אוטומטית
    output_file = 'nba_history.csv.zip'
    df.to_csv(output_file, index=False, compression='zip')
    
    print(f"✅ DONE! Saved full history to {output_file} ({len(df)} games).")
    print("Now, upload this file to your GitHub repository.")
else:
    print("❌ Something went wrong, no data fetched.")
