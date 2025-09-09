#!/usr/bin/env python3
"""
NFL DFS Tracker - Automated Tuesday Updates
Runs every Tuesday to collect the latest stats and salary data
"""

import schedule
import time
import logging
from datetime import datetime, timedelta
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_models import DatabaseManager
from nfl_stats_collector import NFLStatsCollector
from dfs_salary_collector import DFSSalaryCollector
from analysis_engine import NFLDFSAnalysisEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nfl_dfs_tracker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class NFLDFSScheduler:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.stats_collector = NFLStatsCollector(self.db_manager)
        self.salary_collector = DFSSalaryCollector(self.db_manager)
        self.analyzer = NFLDFSAnalysisEngine(self.db_manager)
        
    def tuesday_update_job(self):
        """Main job that runs every Tuesday"""
        logger.info("Starting Tuesday NFL DFS update job")
        
        try:
            current_week, season = self.stats_collector.get_current_week()
            
            # Determine which week to collect (previous completed week)
            target_week = current_week - 1
            if target_week < 1:
                target_week = 18
                season -= 1
                
            logger.info(f"Collecting data for Week {target_week}, {season}")
            
            # Step 1: Collect NFL stats
            logger.info("Collecting NFL stats...")
            stats_collected = self.stats_collector.collect_weekly_stats(target_week, season)
            logger.info(f"Collected stats for {len(stats_collected)} players")
            
            # Step 2: Collect DFS salary data
            logger.info("Collecting DFS salary data...")
            salary_data = self.salary_collector.collect_fantasypros_salary_changes(target_week, season)
            logger.info(f"Collected salary data for {len(salary_data)} players")
            
            # Step 3: Run analysis
            logger.info("Running weekly analysis...")
            analyses = self.analyzer.analyze_weekly_performance(target_week, season)
            
            # Save analyses to database
            for analysis in analyses:
                self.save_analysis(analysis)
            
            logger.info(f"Completed analysis for {len(analyses)} players")
            
            # Step 4: Generate report
            logger.info("Generating weekly report...")
            report = self.analyzer.generate_weekly_report(target_week, season)
            
            # Save report to file
            self.save_weekly_report(report, target_week, season)
            
            logger.info(f"Tuesday update job completed successfully for Week {target_week}, {season}")
            
        except Exception as e:
            logger.error(f"Error in Tuesday update job: {e}", exc_info=True)
            
    def save_analysis(self, analysis):
        """Save weekly analysis to database"""
        import sqlite3
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO weekly_analysis VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis.player_id,
                analysis.week,
                analysis.season,
                analysis.fantasy_points,
                analysis.usage_score,
                analysis.efficiency_score,
                analysis.salary_performance_correlation,
                analysis.market_value_vs_performance
            ))
    
    def save_weekly_report(self, report, week, season):
        """Save weekly report to JSON file"""
        import json
        
        filename = f"reports/week_{week}_{season}_report.json"
        os.makedirs('reports', exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        logger.info(f"Saved weekly report to {filename}")
    
    def backfill_data(self, weeks_back=4):
        """Backfill data for the last few weeks"""
        logger.info(f"Starting backfill for last {weeks_back} weeks")
        
        current_week, season = self.stats_collector.get_current_week()
        
        for i in range(1, weeks_back + 1):
            target_week = current_week - i
            target_season = season
            
            if target_week < 1:
                target_week = 18 + target_week
                target_season = season - 1
                
            logger.info(f"Backfilling Week {target_week}, {target_season}")
            
            try:
                # Collect stats
                stats_collected = self.stats_collector.collect_weekly_stats(target_week, target_season)
                
                # Collect salary data (might not be available for older weeks)
                try:
                    salary_data = self.salary_collector.collect_fantasypros_salary_changes(target_week, target_season)
                except:
                    logger.warning(f"Could not collect salary data for Week {target_week}, {target_season}")
                    salary_data = []
                
                # Run analysis
                analyses = self.analyzer.analyze_weekly_performance(target_week, target_season)
                
                for analysis in analyses:
                    self.save_analysis(analysis)
                    
                logger.info(f"Backfilled Week {target_week}, {target_season} - {len(stats_collected)} stats, {len(analyses)} analyses")
                
            except Exception as e:
                logger.error(f"Error backfilling Week {target_week}, {target_season}: {e}")
                continue
                
    def run_scheduler(self):
        """Run the scheduler"""
        logger.info("Starting NFL DFS Tracker scheduler")
        
        # Schedule Tuesday updates at 10 AM ET
        schedule.every().tuesday.at("10:00").do(self.tuesday_update_job)
        
        # Also run a lighter update on Wednesday to catch any late corrections
        schedule.every().wednesday.at("12:00").do(self.tuesday_update_job)
        
        logger.info("Scheduled Tuesday updates at 10:00 AM and Wednesday updates at 12:00 PM")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    scheduler = NFLDFSScheduler()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "update":
            # Run update job once
            scheduler.tuesday_update_job()
            
        elif command == "backfill":
            # Backfill recent weeks
            weeks = int(sys.argv[2]) if len(sys.argv) > 2 else 4
            scheduler.backfill_data(weeks)
            
        elif command == "schedule":
            # Run scheduler
            scheduler.run_scheduler()
            
        else:
            print("Usage: python scheduler.py [update|backfill [weeks]|schedule]")
            print("  update    - Run update job once")
            print("  backfill  - Backfill recent weeks (default: 4)")
            print("  schedule  - Run scheduler continuously")
    else:
        # Default to running scheduler
        scheduler.run_scheduler()

if __name__ == "__main__":
    main()