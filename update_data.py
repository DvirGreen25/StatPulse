from nba_api.stats.endpoints import leaguegamelog
import pandas as pd
import time
import os

# הגדרות - נתיב יחסי לענן
full_path = 'nba_data_live.csv'

# --- שינוי הטווח: מ-2009 ועד היום ---
start_year = 2009 
end_year = 2025 # מייצר את עונת 2025-26

print(f"--- StatPulse V5.0 Data Engine Started ({start_year}-{end_year + 1}) ---")

all_data = []
season_types = ['Regular Season', 'Playoffs']

# לולאה על כל השנים
for year in range(start_year, end_year + 1):
    # יצירת פורמט עונה (למשל 2025-26)
    season_str = f'{year}-{str(year+1)[-2:]}'
    print(f"Fetching data for {season_str}...")
    
    for s_type in season_types:
        try:
            # שליפת נתונים מה-API
            log = leaguegamelog.LeagueGameLog(
                season=season_str, 
                season_type_all_star=s_type, 
                player_or_team_abbreviation='P'
            )
            df_temp = log.get_data_frames()[0]
            if not df_temp.empty:
                df_temp['SEASON_ID'] = season_str
                # שמירה על סוג משחק (פלייאוף/רגיל) לצורך פילוח עתידי
                df_temp['GAME_TYPE'] = 'Playoffs' if 'Playoffs' in s_type else 'Regular'
                all_data.append(df_temp)
            
            # הפסקה קצרה למנוע חסימה ע"י ה-NBA
            time.sleep(0.6)
            
        except Exception as e:
            print(f"Error extracting {season_str}: {e}")

if all_data:
    print("Processing massive dataset...")
    df = pd.concat(all_data, ignore_index=True)
    
    # 1. המרה למספרים (כולל עמודות חדשות לחישובים)
    cols = ['PTS', 'FGA', 'FTA', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'MIN', 'PLAYER_ID', 'FG3M', 'GAME_SCORE']
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 2. חישוב TS% (True Shooting)
    # הנוסחה: PTS / (2 * (FGA + 0.44 * FTA)) * 100
    df['TS_PCT'] = (df['PTS'] / (2 * (df['FGA'] + 0.44 * df['FTA']))) * 100
    df['TS_PCT'] = df['TS_PCT'].fillna(0).round(1)

    # 3. חישוב Game Score (אם לא קיים במידע הגולמי, נחשב לבד ליתר ביטחון)
    # רוב הפעמים ה-API מביא את זה, אבל אם נרצה לחשב לבד בעתיד זו הנוסחה.
    # כרגע נסתמך על מה שהמרנו למעלה או נשאיר ככה.
    
    # 4. ניקוי שם היריבה ובית/חוץ
    if 'MATCHUP' in df.columns:
        df['OPPONENT'] = df['MATCHUP'].apply(lambda x: str(x).split(' ')[-1])
        df['LOCATION'] = df['MATCHUP'].apply(lambda x: 'HOME' if ' vs. ' in str(x) else 'AWAY')

    # שמירה
    df.to_csv(full_path, index=False)
    print(f"SUCCESS! Database updated. Total Games: {len(df)}")
    print(f"Seasons covered: {start_year}-{start_year+1} to {end_year}-{end_year+1}")

else:
    print("No data found. Something went wrong.")
