# update_data.py - רץ כל יום בגיטהאב
from nba_api.stats.endpoints import leaguegamelog
import pandas as pd
import time
from datetime import datetime

# --- לוגיקה אוטומטית לעונה הנוכחית ---
now = datetime.now()
# אם אנחנו במחצית השנייה של השנה (אוקטובר-דצמבר), העונה מתחילה בשנה הנוכחית
# אם אנחנו במחצית הראשונה (ינואר-יוני), העונה התחילה בשנה שעברה
if now.month >= 10:
    current_season_start = now.year
else:
    current_season_start = now.year - 1

season_str = f'{current_season_start}-{str(current_season_start+1)[-2:]}'
print(f"--- Daily Update for Active Season: {season_str} ---")

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
            all_data.append(df_temp)
        time.sleep(0.6)
    except Exception as e:
        print(f"Error fetching data: {e}")

if all_data:
    df = pd.concat(all_data, ignore_index=True)
    # שומרים בשם נפרד - רק העונה החיה!
    df.to_csv('nba_current.csv', index=False)
    print(f"SUCCESS! Updated nba_current.csv with {len(df)} rows.")
else:
    print("No games found yet for this season (or API error).")
