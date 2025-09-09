import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr
from typing import Dict, List, Tuple, Optional
import sqlite3
import logging
from datetime import datetime, timedelta
from data_models import WeeklyAnalysis, DatabaseManager

class NFLDFSAnalysisEngine:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
    def calculate_fantasy_points(self, stats: Dict, scoring_system: str = "ppr") -> float:
        """Calculate fantasy points based on stats"""
        points = 0.0
        
        # Receiving points
        if stats.get('receptions'):
            points += stats['receptions'] * (1.0 if scoring_system == "ppr" else 0.5 if scoring_system == "half_ppr" else 0.0)
        
        if stats.get('receiving_yards'):
            points += stats['receiving_yards'] * 0.1
            
        if stats.get('receiving_tds'):
            points += stats['receiving_tds'] * 6.0
            
        # Rushing points
        if stats.get('rushing_yards'):
            points += stats['rushing_yards'] * 0.1
            
        if stats.get('rushing_tds'):
            points += stats['rushing_tds'] * 6.0
            
        return round(points, 2)
    
    def calculate_usage_score(self, stats: Dict) -> float:
        """Calculate usage score based on snaps, targets, carries"""
        usage = 0.0
        
        # Target share weight (40%)
        if stats.get('target_share'):
            usage += stats['target_share'] * 0.4
            
        # Targets weight (30%) 
        if stats.get('targets'):
            usage += min(stats['targets'] / 15.0, 1.0) * 0.3  # Normalize to 15 targets = 1.0
            
        # Carries weight (20%)
        if stats.get('carries'):
            usage += min(stats['carries'] / 25.0, 1.0) * 0.2  # Normalize to 25 carries = 1.0
            
        # Snap percentage weight (10%)
        if stats.get('snap_percentage'):
            usage += stats['snap_percentage'] / 100.0 * 0.1
            
        return round(usage * 100, 2)  # Return as percentage
    
    def calculate_efficiency_score(self, stats: Dict) -> float:
        """Calculate efficiency score (yards per opportunity)"""
        total_opportunities = (stats.get('targets', 0) + stats.get('carries', 0))
        total_yards = (stats.get('receiving_yards', 0) + stats.get('rushing_yards', 0))
        
        if total_opportunities == 0:
            return 0.0
            
        efficiency = total_yards / total_opportunities
        return round(efficiency, 2)
    
    def analyze_weekly_performance(self, week: int, season: int) -> List[WeeklyAnalysis]:
        """Analyze performance for all players in a given week"""
        analyses = []
        
        # Get combined stats and salary data
        query = """
            SELECT 
                ps.*,
                ds.draftkings_salary,
                ds.fanduel_salary,
                ds.dk_salary_change,
                ds.fd_salary_change,
                ds.dk_percent_change,
                ds.fd_percent_change
            FROM player_stats ps
            LEFT JOIN dfs_salaries ds ON ps.player_id = ds.player_id 
                AND ps.week = ds.week AND ps.season = ds.season
            WHERE ps.week = ? AND ps.season = ?
        """
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(week, season))
            
        for _, row in df.iterrows():
            stats_dict = row.to_dict()
            
            fantasy_points = self.calculate_fantasy_points(stats_dict)
            usage_score = self.calculate_usage_score(stats_dict)
            efficiency_score = self.calculate_efficiency_score(stats_dict)
            
            # Determine market value assessment
            market_assessment = self._assess_market_value(
                fantasy_points, usage_score, efficiency_score,
                row.get('dk_salary_change', 0), row.get('fd_salary_change', 0)
            )
            
            analysis = WeeklyAnalysis(
                player_id=row['player_id'],
                week=week,
                season=season,
                fantasy_points=fantasy_points,
                usage_score=usage_score,
                efficiency_score=efficiency_score,
                market_value_vs_performance=market_assessment
            )
            
            analyses.append(analysis)
            
        return analyses
    
    def calculate_salary_performance_correlation(self, player_id: str, weeks: int = 8) -> Optional[float]:
        """Calculate correlation between salary changes and performance over time"""
        query = """
            SELECT 
                ps.week,
                ps.season,
                ps.targets,
                ps.receptions,
                ps.receiving_yards,
                ps.receiving_tds,
                ps.carries,
                ps.rushing_yards,
                ps.rushing_tds,
                ds.dk_salary_change,
                ds.fd_salary_change
            FROM player_stats ps
            LEFT JOIN dfs_salaries ds ON ps.player_id = ds.player_id 
                AND ps.week = ds.week AND ps.season = ds.season
            WHERE ps.player_id = ?
            ORDER BY ps.season DESC, ps.week DESC
            LIMIT ?
        """
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(player_id, weeks))
            
        if len(df) < 3:  # Need at least 3 data points for correlation
            return None
            
        # Calculate fantasy points for each week
        fantasy_points = []
        salary_changes = []
        
        for _, row in df.iterrows():
            points = self.calculate_fantasy_points(row.to_dict())
            fantasy_points.append(points)
            
            # Average salary change across platforms
            dk_change = row.get('dk_salary_change', 0) or 0
            fd_change = row.get('fd_salary_change', 0) or 0
            avg_change = (dk_change + fd_change) / 2
            salary_changes.append(avg_change)
        
        # Calculate correlation
        try:
            correlation, p_value = pearsonr(fantasy_points, salary_changes)
            return round(correlation, 3) if not np.isnan(correlation) else None
        except:
            return None
    
    def _assess_market_value(self, fantasy_points: float, usage_score: float, 
                           efficiency_score: float, dk_change: int, fd_change: int) -> str:
        """Assess if player is undervalued, overvalued, or fairly valued"""
        
        # Combine performance metrics
        performance_score = (fantasy_points * 0.5) + (usage_score * 0.3) + (efficiency_score * 0.2)
        
        # Average salary change
        avg_salary_change = ((dk_change or 0) + (fd_change or 0)) / 2
        
        # Thresholds (can be adjusted based on analysis)
        if performance_score > 15 and avg_salary_change < 200:
            return "undervalued"
        elif performance_score < 8 and avg_salary_change > 200:
            return "overvalued" 
        else:
            return "fair"
    
    def get_top_performers_by_value(self, week: int, season: int, limit: int = 10) -> List[Dict]:
        """Get top performers by value (performance vs salary)"""
        query = """
            SELECT 
                ps.*,
                ds.draftkings_salary,
                ds.fanduel_salary,
                ds.dk_salary_change,
                ds.fd_salary_change,
                wa.fantasy_points,
                wa.usage_score,
                wa.efficiency_score,
                wa.market_value_vs_performance
            FROM player_stats ps
            LEFT JOIN dfs_salaries ds ON ps.player_id = ds.player_id 
                AND ps.week = ds.week AND ps.season = ds.season
            LEFT JOIN weekly_analysis wa ON ps.player_id = wa.player_id
                AND ps.week = wa.week AND ps.season = wa.season
            WHERE ps.week = ? AND ps.season = ?
            AND wa.fantasy_points > 10
            ORDER BY wa.fantasy_points DESC
            LIMIT ?
        """
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(week, season, limit))
            
        return df.to_dict('records')
    
    def identify_salary_trends(self, lookback_weeks: int = 4) -> List[Dict]:
        """Identify players with notable salary trends"""
        query = """
            SELECT 
                player_id,
                player_name,
                AVG(dk_salary_change) as avg_dk_change,
                AVG(fd_salary_change) as avg_fd_change,
                COUNT(*) as weeks_tracked
            FROM dfs_salaries
            WHERE week >= (SELECT MAX(week) - ? FROM dfs_salaries)
            GROUP BY player_id, player_name
            HAVING weeks_tracked >= 3
            ORDER BY avg_dk_change DESC
        """
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(lookback_weeks,))
            
        trends = []
        for _, row in df.iterrows():
            avg_change = (row['avg_dk_change'] + row['avg_fd_change']) / 2
            
            if avg_change > 300:
                trend = "rising_fast"
            elif avg_change > 100:
                trend = "rising"
            elif avg_change < -300:
                trend = "falling_fast"
            elif avg_change < -100:
                trend = "falling"
            else:
                trend = "stable"
                
            trends.append({
                'player_id': row['player_id'],
                'player_name': row['player_name'],
                'avg_salary_change': round(avg_change, 0),
                'trend': trend,
                'weeks_tracked': row['weeks_tracked']
            })
            
        return trends
    
    def generate_weekly_report(self, week: int, season: int) -> Dict:
        """Generate comprehensive weekly report"""
        report = {
            'week': week,
            'season': season,
            'generated_at': datetime.now().isoformat(),
            'top_performers': self.get_top_performers_by_value(week, season, 20),
            'salary_trends': self.identify_salary_trends(4),
            'summary_stats': self._get_weekly_summary_stats(week, season)
        }
        
        return report
    
    def _get_weekly_summary_stats(self, week: int, season: int) -> Dict:
        """Get summary statistics for the week"""
        query = """
            SELECT 
                COUNT(*) as total_players,
                AVG(fantasy_points) as avg_fantasy_points,
                AVG(usage_score) as avg_usage_score,
                COUNT(CASE WHEN market_value_vs_performance = 'undervalued' THEN 1 END) as undervalued_count,
                COUNT(CASE WHEN market_value_vs_performance = 'overvalued' THEN 1 END) as overvalued_count
            FROM weekly_analysis
            WHERE week = ? AND season = ?
        """
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.execute(query, (week, season))
            result = cursor.fetchone()
            
        if result:
            return {
                'total_players': result[0],
                'avg_fantasy_points': round(result[1] or 0, 2),
                'avg_usage_score': round(result[2] or 0, 2),
                'undervalued_count': result[3],
                'overvalued_count': result[4]
            }
        else:
            return {}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    db_manager = DatabaseManager()
    analyzer = NFLDFSAnalysisEngine(db_manager)
    
    # Example analysis
    week = 10
    season = 2024
    
    analyses = analyzer.analyze_weekly_performance(week, season)
    print(f"Analyzed {len(analyses)} players for Week {week}")
    
    report = analyzer.generate_weekly_report(week, season)
    print(f"Generated report with {len(report['top_performers'])} top performers")