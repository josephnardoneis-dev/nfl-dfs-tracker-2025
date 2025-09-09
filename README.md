# NFL DFS Tracker

An automated tool that tracks NFL player statistics and DFS salary changes, analyzing correlations between performance and market value movements.

## Features

- **Automated Data Collection**: Pulls NFL stats from `nfl-data-py` and salary data from FantasyPros
- **Performance Analysis**: Calculates fantasy points, usage scores, and efficiency metrics
- **Salary Correlation**: Tracks how DFS salaries respond to player performance
- **Market Value Assessment**: Identifies undervalued and overvalued players
- **Web Dashboard**: Clean interface to view analysis and trends
- **Tuesday Updates**: Automatically updates every Tuesday after NFL games

## Data Sources

- **NFL Stats**: [nfl-data-py](https://github.com/nflverse/nfl_data_py) - Free, comprehensive NFL data
- **DFS Salaries**: FantasyPros salary change tracking (free tier available)
- **Optional**: SportsDataIO API for real-time salary data (paid)

## Installation

1. Clone or download the project files
2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python data_models.py
```

## Usage

### Manual Data Collection
```bash
# Collect latest week's data
python nfl_stats_collector.py

# Collect salary data
python dfs_salary_collector.py

# Run analysis
python analysis_engine.py
```

### Web Interface
```bash
# Start the web server
python web_interface.py
```
Then visit `http://localhost:5000`

### Automated Updates
```bash
# Run once
python scheduler.py update

# Backfill recent weeks
python scheduler.py backfill 4

# Run continuous scheduler (Tuesday updates)
python scheduler.py schedule
```

## Key Metrics

### Usage Score
Composite metric combining:
- Target share (40%)
- Raw targets (30%) 
- Carries (20%)
- Snap percentage (10%)

### Efficiency Score
Yards per opportunity (targets + carries)

### Market Value Assessment
- **Undervalued**: High performance, low salary increase
- **Overvalued**: Low performance, high salary increase  
- **Fair**: Performance matches salary movement

## File Structure

```
nfl-dfs-tracker/
├── data_models.py          # Database models and management
├── nfl_stats_collector.py  # NFL stats collection
├── dfs_salary_collector.py # DFS salary collection
├── analysis_engine.py      # Performance analysis
├── web_interface.py        # Flask web app
├── scheduler.py           # Automated updates
├── templates/
│   └── index.html         # Web dashboard
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Database Schema

### player_stats
- Weekly player statistics (snaps, targets, carries, yards, TDs)
- Advanced metrics (air yards, YAC, target share)

### dfs_salaries  
- DraftKings and FanDuel salary data
- Week-over-week changes and percentages

### weekly_analysis
- Calculated fantasy points and composite scores
- Market value assessments and correlations

## GitHub Integration

To deploy on GitHub Pages or use GitHub Actions:

1. **Static Site**: The web interface can be modified to generate static HTML reports
2. **GitHub Actions**: Use the scheduler for automated weekly updates
3. **Data Storage**: SQLite database can be committed or use external storage

## API Endpoints

- `GET /api/weekly-report/{season}/{week}` - Full weekly analysis
- `GET /api/player-analysis/{player_id}` - Individual player deep dive
- `GET /api/top-performers/{season}/{week}` - Top performers list
- `GET /api/salary-trends` - Current salary trend analysis
- `POST /api/collect-data` - Manually trigger data collection

## Configuration

### API Keys (Optional)
For enhanced salary data, add SportsDataIO API key to `dfs_salary_collector.py`:
```python
collector = DFSSalaryCollector(db_manager, api_key="your-api-key")
```

### Scheduling
Modify `scheduler.py` to change update timing:
```python
schedule.every().tuesday.at("10:00").do(self.tuesday_update_job)
```

## Future Enhancements

- [ ] Weather data integration
- [ ] Injury report tracking  
- [ ] Props betting line movements
- [ ] Machine learning predictions
- [ ] Mobile-responsive design
- [ ] Player news sentiment analysis
- [ ] Slack/Discord notifications

## Contributing

Feel free to open issues or submit pull requests for improvements!

## License

MIT License - use freely for personal or commercial projects.