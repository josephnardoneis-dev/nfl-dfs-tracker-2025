from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime, timedelta
from data_models import DatabaseManager
from analysis_engine import NFLDFSAnalysisEngine
from nfl_stats_collector import NFLStatsCollector
from dfs_salary_collector import DFSSalaryCollector
import sqlite3
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize components
db_manager = DatabaseManager()
analyzer = NFLDFSAnalysisEngine(db_manager)
stats_collector = NFLStatsCollector(db_manager)
salary_collector = DFSSalaryCollector(db_manager)

@app.route('/')
def index():
    """Main dashboard"""
    # Get the latest data we actually have in our database
    try:
        week, season = db_manager.get_latest_data_in_db()
        print(f"Using database data: {season} Week {week}")
    except Exception as e:
        print(f"Error getting database data, using fallback: {e}")
        week, season = 18, 2024  # Fallback
    
    # Get latest report
    try:
        report = analyzer.generate_weekly_report(week, season)
        summary_stats = report.get('summary_stats', {})
    except Exception as e:
        print(f"Error generating report: {e}")
        report = {}
        summary_stats = {}
    
    return render_template('index.html', 
                         week=week, 
                         season=season,
                         summary_stats=summary_stats)

@app.route('/api/weekly-report/<int:season>/<int:week>')
def get_weekly_report(season, week):
    """Get weekly analysis report"""
    try:
        report = analyzer.generate_weekly_report(week, season)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-analysis/<player_id>')
def get_player_analysis(player_id):
    """Get detailed analysis for a specific player"""
    try:
        weeks = request.args.get('weeks', 8, type=int)
        
        # Get player stats history
        stats_history = db_manager.get_player_weekly_data(player_id, weeks)
        
        # Calculate correlation
        correlation = analyzer.calculate_salary_performance_correlation(player_id, weeks)
        
        # Get salary history
        salary_history = salary_collector.get_historical_salary_changes(player_id, weeks)
        
        analysis = {
            'player_id': player_id,
            'stats_history': stats_history,
            'salary_history': salary_history,
            'correlation': correlation,
            'weeks_analyzed': weeks
        }
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/top-performers/<int:season>/<int:week>')
def get_top_performers(season, week):
    """Get top performers for a specific week"""
    try:
        limit = request.args.get('limit', 20, type=int)
        performers = analyzer.get_top_performers_by_value(week, season, limit)
        return jsonify(performers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/salary-trends')
def get_salary_trends():
    """Get current salary trends"""
    try:
        weeks = request.args.get('weeks', 4, type=int)
        trends = analyzer.identify_salary_trends(weeks)
        return jsonify(trends)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/collect-data')
def collect_latest_data():
    """Manually trigger data collection"""
    try:
        # Try to get the latest available data, but fall back to what we have
        try:
            target_week, target_season = stats_collector.get_latest_available_data()
        except Exception:
            target_week, target_season = db_manager.get_latest_data_in_db()
        
        # Try to collect stats but handle gracefully if no new data
        try:
            stats_collected = stats_collector.collect_weekly_stats(target_week, target_season)
            stats_count = len(stats_collected)
        except Exception as e:
            print(f"Error collecting stats: {e}")
            stats_count = 0
            
        # Try salary data collection
        try:
            salary_data = salary_collector.collect_fantasypros_salary_changes(target_week, target_season)
            salary_count = len(salary_data)
        except Exception as e:
            print(f"Error collecting salary data: {e}")
            salary_count = 0
        
        # Run analysis on existing data
        try:
            analyses = analyzer.analyze_weekly_performance(target_week, target_season)
            analysis_count = len(analyses)
        except Exception as e:
            print(f"Error running analysis: {e}")
            analysis_count = 0
        
        return jsonify({
            'success': True,
            'message': f'Data refresh completed (using {target_season} Week {target_week} data)',
            'stats_collected': stats_count,
            'salary_records': salary_count,
            'analyses_completed': analysis_count,
            'week': target_week,
            'season': target_season
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/players')
def players_page():
    """Players analysis page"""
    return render_template('players.html')

@app.route('/trends')
def trends_page():
    """Salary trends page"""
    return render_template('trends.html')

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5001)