import nfl_data_py as nfl
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import logging
from data_models import PlayerWeeklyStats, DatabaseManager

class NFLStatsCollector:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
    def get_current_week(self) -> tuple[int, int]:
        """Get current NFL week and season"""
        current_date = datetime.now()
        
        # NFL season typically starts in September
        if current_date.month >= 9:
            season = current_date.year
        else:
            season = current_date.year - 1
            
        # Simple week calculation (can be refined)
        season_start = datetime(season, 9, 1)
        weeks_since_start = (current_date - season_start).days // 7
        week = min(max(1, weeks_since_start), 18)  # Regular season is weeks 1-18
        
        return week, season
    
    def collect_weekly_stats(self, week: int, season: int) -> List[PlayerWeeklyStats]:
        """Collect weekly stats for all players"""
        self.logger.info(f"Collecting stats for Week {week}, {season}")
        
        try:
            # Get weekly data from nfl_data_py
            weekly_data = nfl.import_weekly_data([season])
            
            # Filter for specific week
            week_data = weekly_data[weekly_data['week'] == week].copy()
            
            # Get roster data for position info
            roster_data = nfl.import_rosters([season])
            
            # Merge with roster for position info
            merged_data = week_data.merge(
                roster_data[['player_id', 'position', 'team']].drop_duplicates(),
                on=['player_id'], 
                how='left',
                suffixes=('', '_roster')
            )
            
            player_stats = []
            
            for _, row in merged_data.iterrows():
                try:
                    stats = PlayerWeeklyStats(
                        player_id=row.get('player_id', ''),
                        player_name=row.get('player_display_name', ''),
                        team=row.get('recent_team', row.get('team', '')),
                        position=row.get('position', ''),
                        week=week,
                        season=season,
                        date=datetime.now(),
                        
                        # Core receiving stats
                        targets=self._safe_int(row.get('targets')),
                        receptions=self._safe_int(row.get('receptions')),
                        receiving_yards=self._safe_int(row.get('receiving_yards')),
                        receiving_tds=self._safe_int(row.get('receiving_tds')),
                        
                        # Core rushing stats  
                        carries=self._safe_int(row.get('carries')),
                        rushing_yards=self._safe_int(row.get('rushing_yards')),
                        rushing_tds=self._safe_int(row.get('rushing_tds')),
                        
                        # Advanced metrics
                        air_yards=self._safe_int(row.get('receiving_air_yards')),
                        yards_after_catch=self._safe_int(row.get('receiving_yards_after_catch')),
                        target_share=self._safe_float(row.get('target_share'))
                    )
                    
                    # Only save players with meaningful stats
                    if (stats.targets and stats.targets > 0) or (stats.carries and stats.carries > 0):
                        player_stats.append(stats)
                        
                except Exception as e:
                    self.logger.error(f"Error processing player {row.get('player_display_name', 'Unknown')}: {e}")
                    continue
            
            # Save to database
            for stats in player_stats:
                self.db_manager.save_player_stats(stats)
                
            self.logger.info(f"Saved {len(player_stats)} player stat records")
            return player_stats
            
        except Exception as e:
            self.logger.error(f"Error collecting weekly stats: {e}")
            return []
    
    def get_snap_counts(self, week: int, season: int) -> Dict[str, Dict]:
        """Get snap count data (requires additional processing of play-by-play data)"""
        try:
            # Get play-by-play data for the week
            pbp_data = nfl.import_pbp_data([season])
            
            # Filter for the specific week
            week_pbp = pbp_data[pbp_data['week'] == week].copy()
            
            snap_counts = {}
            
            # Process offensive snaps
            offense_snaps = week_pbp.groupby(['posteam', 'week']).agg({
                'play_id': 'count'
            }).reset_index()
            
            # This is a simplified version - more complex snap counting would require
            # parsing the participation data from play-by-play
            
            return snap_counts
            
        except Exception as e:
            self.logger.error(f"Error getting snap counts: {e}")
            return {}
    
    def _safe_int(self, value) -> int:
        """Safely convert value to int"""
        try:
            if pd.isna(value):
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def collect_latest_week(self):
        """Collect stats for the most recent completed week"""
        current_week, season = self.get_current_week()
        
        # Collect previous week (assuming Tuesday update after Monday games)
        if datetime.now().weekday() < 1:  # Before Tuesday
            target_week = current_week - 1
        else:
            target_week = current_week
            
        if target_week < 1:
            target_week = 18
            season -= 1
            
        return self.collect_weekly_stats(target_week, season)
    
    def backfill_season_data(self, season: int, start_week: int = 1, end_week: int = None):
        """Backfill data for entire season"""
        if end_week is None:
            current_week, current_season = self.get_current_week()
            if season == current_season:
                end_week = current_week - 1
            else:
                end_week = 18
        
        for week in range(start_week, end_week + 1):
            self.logger.info(f"Backfilling Week {week}, {season}")
            self.collect_weekly_stats(week, season)

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    db_manager = DatabaseManager()
    collector = NFLStatsCollector(db_manager)
    
    # Collect latest week
    stats = collector.collect_latest_week()
    print(f"Collected {len(stats)} player records")