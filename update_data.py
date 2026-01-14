from nba_api.stats.endpoints import leaguegamelog
import pandas as pd
import time
import os

# הגדרות
folder_path = r'C:\StatPulse'
filename = 'nba_data_live.csv'
full_path = os.path.join(folder_path, filename)

start_year = 2020 
end_year = 2025 # עדכני לעונה הנוכחית

print("--- StatPulse V3.0 Data Engine Started ---")

all_data = []
season_types = ['Regular Season', 'Playoffs']

for year in range(start_year, end_year + 1):
    season_str = f'{year}-{str(year+1)[-2:]}'
    print(f"Fetching data for {season_str}...")
    
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
                # Keep PLAYER_ID for headshots!
                all_data.append(df_temp)
            time.sleep(0.6)
        except Exception as e:
            print(f"Error extracting {season_str}: {e}")

if all_data:
    print("Processing Data & Advanced Stats...")
    df = pd.concat(all_data, ignore_index=True)
    
    # 1. המרה למספרים
    cols = ['PTS', 'FGA', 'FTA', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'MIN', 'PLAYER_ID']
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 2. חישוב TS% (True Shooting) - סקאלה של 0-100
    df['TS_PCT'] = (df['PTS'] / (2 * (df['FGA'] + 0.44 * df['FTA']))) * 100
    df['TS_PCT'] = df['TS_PCT'].fillna(0).round(1)

    # 3. חישוב Game Score
    df['GAME_SCORE'] = (
        df['PTS'] + 0.4 * df['FGA'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FTA']) + 
        0.7 * df['REB'] + 0.3 * df['REB'] + df['STL'] + 0.7 * df['AST'] + 0.7 * df['BLK'] - 
        0.4 * df['PF'] - df['TOV']
    ).round(1)

    # 4. ניקוי שם היריבה ובית/חוץ
    df['OPPONENT'] = df['MATCHUP'].apply(lambda x: x.split(' ')[-1])
    df['LOCATION'] = df['MATCHUP'].apply(lambda x: 'HOME' if ' vs. ' in str(x) else 'AWAY')

    # שמירה
    df.to_csv(full_path, index=False)
    print(f"SUCCESS! Database V3.0 Ready. Rows: {len(df)}")

else:
    print("No data found.")