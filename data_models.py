from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import sqlite3

@dataclass
class PlayerWeeklyStats:
    player_id: str
    player_name: str
    team: str
    position: str
    week: int
    season: int
    date: datetime
    
    # Core stats
    snaps: Optional[int] = None
    snap_percentage: Optional[float] = None
    targets: Optional[int] = None
    receptions: Optional[int] = None
    receiving_yards: Optional[int] = None
    receiving_tds: Optional[int] = None
    carries: Optional[int] = None
    rushing_yards: Optional[int] = None
    rushing_tds: Optional[int] = None
    
    # Advanced metrics
    air_yards: Optional[int] = None
    yards_after_catch: Optional[int] = None
    red_zone_targets: Optional[int] = None
    target_share: Optional[float] = None

@dataclass
class DFSSalaryData:
    player_id: str
    player_name: str
    week: int
    season: int
    date: datetime
    
    # Salary data
    draftkings_salary: Optional[int] = None
    fanduel_salary: Optional[int] = None
    
    # Week-over-week changes
    dk_salary_change: Optional[int] = None
    fd_salary_change: Optional[int] = None
    dk_percent_change: Optional[float] = None
    fd_percent_change: Optional[float] = None

@dataclass
class WeeklyAnalysis:
    player_id: str
    week: int
    season: int
    
    # Performance metrics
    fantasy_points: float
    usage_score: float  # Composite of snaps, targets, carries
    efficiency_score: float  # Yards per opportunity
    
    # Salary correlation
    salary_performance_correlation: Optional[float] = None
    market_value_vs_performance: Optional[str] = None  # "undervalued", "overvalued", "fair"

class DatabaseManager:
    def __init__(self, db_path: str = "nfl_dfs_tracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    player_id TEXT,
                    player_name TEXT,
                    team TEXT,
                    position TEXT,
                    week INTEGER,
                    season INTEGER,
                    date TEXT,
                    snaps INTEGER,
                    snap_percentage REAL,
                    targets INTEGER,
                    receptions INTEGER,
                    receiving_yards INTEGER,
                    receiving_tds INTEGER,
                    carries INTEGER,
                    rushing_yards INTEGER,
                    rushing_tds INTEGER,
                    air_yards INTEGER,
                    yards_after_catch INTEGER,
                    red_zone_targets INTEGER,
                    target_share REAL,
                    PRIMARY KEY (player_id, week, season)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dfs_salaries (
                    player_id TEXT,
                    player_name TEXT,
                    week INTEGER,
                    season INTEGER,
                    date TEXT,
                    draftkings_salary INTEGER,
                    fanduel_salary INTEGER,
                    dk_salary_change INTEGER,
                    fd_salary_change INTEGER,
                    dk_percent_change REAL,
                    fd_percent_change REAL,
                    PRIMARY KEY (player_id, week, season)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weekly_analysis (
                    player_id TEXT,
                    week INTEGER,
                    season INTEGER,
                    fantasy_points REAL,
                    usage_score REAL,
                    efficiency_score REAL,
                    salary_performance_correlation REAL,
                    market_value_vs_performance TEXT,
                    PRIMARY KEY (player_id, week, season)
                )
            """)
    
    def save_player_stats(self, stats: PlayerWeeklyStats):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO player_stats VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                stats.player_id, stats.player_name, stats.team, stats.position,
                stats.week, stats.season, stats.date.isoformat(),
                stats.snaps, stats.snap_percentage, stats.targets, stats.receptions,
                stats.receiving_yards, stats.receiving_tds, stats.carries,
                stats.rushing_yards, stats.rushing_tds, stats.air_yards,
                stats.yards_after_catch, stats.red_zone_targets, stats.target_share
            ))
    
    def save_salary_data(self, salary: DFSSalaryData):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO dfs_salaries VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                salary.player_id, salary.player_name, salary.week, salary.season,
                salary.date.isoformat(), salary.draftkings_salary, salary.fanduel_salary,
                salary.dk_salary_change, salary.fd_salary_change,
                salary.dk_percent_change, salary.fd_percent_change
            ))
    
    def get_player_weekly_data(self, player_id: str, weeks: int = 5) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM player_stats 
                WHERE player_id = ? 
                ORDER BY week DESC 
                LIMIT ?
            """, (player_id, weeks))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]