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
    current_week, current_season = stats_collector.get_current_week()
    
    # Get latest report
    try:
        report = analyzer.generate_weekly_report(current_week - 1, current_season)
        summary_stats = report.get('summary_stats', {})
    except:
        report = {}
        summary_stats = {}
    
    return render_template('index.html', 
                         week=current_week-1, 
                         season=current_season,
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
        current_week, current_season = stats_collector.get_current_week()
        
        # Collect stats for previous week (assuming Tuesday updates)
        target_week = current_week - 1 if datetime.now().weekday() >= 1 else current_week - 2
        
        # Collect NFL stats
        stats_collected = stats_collector.collect_weekly_stats(target_week, current_season)
        
        # Collect salary data
        salary_data = salary_collector.collect_fantasypros_salary_changes(target_week, current_season)
        
        # Run analysis
        analyses = analyzer.analyze_weekly_performance(target_week, current_season)
        
        return jsonify({
            'success': True,
            'stats_collected': len(stats_collected),
            'salary_records': len(salary_data),
            'analyses_completed': len(analyses),
            'week': target_week,
            'season': current_season
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/players')
def players_page():
    """Players analysis page"""
    return render_template('players.html')

@app.route('/trends')
def trends_page():
    """Salary trends page"""
    return render_template('trends.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)