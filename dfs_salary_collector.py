import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Optional
import logging
from bs4 import BeautifulSoup
import time
from data_models import DFSSalaryData, DatabaseManager

class DFSSalaryCollector:
    def __init__(self, db_manager: DatabaseManager, api_key: Optional[str] = None):
        self.db_manager = db_manager
        self.api_key = api_key  # For paid APIs like SportsDataIO
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
    def collect_fantasypros_salary_changes(self, week: int, season: int) -> List[DFSSalaryData]:
        """Scrape salary change data from FantasyPros (free source)"""
        salary_data = []
        
        try:
            # DraftKings salary changes
            dk_url = "https://www.fantasypros.com/daily-fantasy/nfl/draftkings-salary-changes.php"
            dk_data = self._scrape_fantasypros_salaries(dk_url, "DraftKings", week, season)
            salary_data.extend(dk_data)
            
            time.sleep(2)  # Be respectful with scraping
            
            # FanDuel salary changes  
            fd_url = "https://www.fantasypros.com/daily-fantasy/nfl/fanduel-salary-changes.php"
            fd_data = self._scrape_fantasypros_salaries(fd_url, "FanDuel", week, season)
            
            # Merge DK and FD data
            merged_data = self._merge_salary_data(dk_data, fd_data, week, season)
            
            return merged_data
            
        except Exception as e:
            self.logger.error(f"Error collecting FantasyPros salary data: {e}")
            return []
    
    def _scrape_fantasypros_salaries(self, url: str, platform: str, week: int, season: int) -> List[Dict]:
        """Scrape salary data from FantasyPros"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the salary table (structure may vary)
            table = soup.find('table', class_='table')
            if not table:
                self.logger.warning(f"Could not find salary table on {url}")
                return []
            
            salary_data = []
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    try:
                        player_name = cells[0].get_text(strip=True)
                        position = cells[1].get_text(strip=True)
                        current_salary = self._parse_salary(cells[2].get_text(strip=True))
                        salary_change = self._parse_salary_change(cells[3].get_text(strip=True))
                        
                        if current_salary and player_name:
                            salary_data.append({
                                'player_name': player_name,
                                'position': position,
                                'platform': platform,
                                'current_salary': current_salary,
                                'salary_change': salary_change,
                                'week': week,
                                'season': season
                            })
                            
                    except Exception as e:
                        self.logger.debug(f"Error parsing row: {e}")
                        continue
            
            return salary_data
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return []
    
    def _merge_salary_data(self, dk_data: List[Dict], fd_data: List[Dict], 
                          week: int, season: int) -> List[DFSSalaryData]:
        """Merge DraftKings and FanDuel salary data"""
        merged_data = []
        
        # Create lookup dictionaries
        dk_lookup = {item['player_name']: item for item in dk_data}
        fd_lookup = {item['player_name']: item for item in fd_data}
        
        # Get all unique player names
        all_players = set(dk_lookup.keys()) | set(fd_lookup.keys())
        
        for player_name in all_players:
            dk_info = dk_lookup.get(player_name, {})
            fd_info = fd_lookup.get(player_name, {})
            
            # Generate player ID (simplified - in production would use proper ID mapping)
            player_id = self._generate_player_id(player_name)
            
            salary_data = DFSSalaryData(
                player_id=player_id,
                player_name=player_name,
                week=week,
                season=season,
                date=datetime.now(),
                
                draftkings_salary=dk_info.get('current_salary'),
                fanduel_salary=fd_info.get('current_salary'),
                dk_salary_change=dk_info.get('salary_change'),
                fd_salary_change=fd_info.get('salary_change'),
                
                # Calculate percentage changes
                dk_percent_change=self._calculate_percent_change(
                    dk_info.get('current_salary'), dk_info.get('salary_change')
                ),
                fd_percent_change=self._calculate_percent_change(
                    fd_info.get('current_salary'), fd_info.get('salary_change')
                )
            )
            
            merged_data.append(salary_data)
        
        # Save to database
        for data in merged_data:
            self.db_manager.save_salary_data(data)
            
        return merged_data
    
    def collect_sportsdata_salaries(self, week: int, season: int) -> List[DFSSalaryData]:
        """Collect salary data using SportsDataIO API (requires paid subscription)"""
        if not self.api_key:
            self.logger.warning("No API key provided for SportsDataIO")
            return []
            
        try:
            url = f"https://api.sportsdata.io/v3/nfl/scores/json/DfsSlatesByWeek/{season}/{week}"
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            salary_data = []
            
            for slate in data:
                for dfs_slate in slate.get('DfsSlates', []):
                    for player in dfs_slate.get('DfsSlatePlayers', []):
                        salary_info = DFSSalaryData(
                            player_id=str(player.get('PlayerID', '')),
                            player_name=player.get('Name', ''),
                            week=week,
                            season=season,
                            date=datetime.now(),
                            
                            draftkings_salary=player.get('Salary') if dfs_slate.get('Operator') == 'DraftKings' else None,
                            fanduel_salary=player.get('Salary') if dfs_slate.get('Operator') == 'FanDuel' else None,
                        )
                        
                        salary_data.append(salary_info)
                        
            return salary_data
            
        except Exception as e:
            self.logger.error(f"Error collecting SportsDataIO salary data: {e}")
            return []
    
    def _parse_salary(self, salary_text: str) -> Optional[int]:
        """Parse salary from text like '$7,500' to integer 7500"""
        try:
            # Remove $ and , then convert to int
            cleaned = salary_text.replace('$', '').replace(',', '').strip()
            if cleaned and cleaned.isdigit():
                return int(cleaned)
        except:
            pass
        return None
    
    def _parse_salary_change(self, change_text: str) -> Optional[int]:
        """Parse salary change from text like '+$500' or '-$300'"""
        try:
            cleaned = change_text.replace('$', '').replace(',', '').strip()
            if cleaned and (cleaned.startswith('+') or cleaned.startswith('-')):
                return int(cleaned)
        except:
            pass
        return None
    
    def _calculate_percent_change(self, current_salary: Optional[int], 
                                 salary_change: Optional[int]) -> Optional[float]:
        """Calculate percentage change in salary"""
        if current_salary and salary_change and current_salary > 0:
            previous_salary = current_salary - salary_change
            if previous_salary > 0:
                return (salary_change / previous_salary) * 100
        return None
    
    def _generate_player_id(self, player_name: str) -> str:
        """Generate a simple player ID from name (in production, use proper player ID mapping)"""
        return player_name.lower().replace(' ', '_').replace('.', '').replace("'", "")
    
    def get_historical_salary_changes(self, player_id: str, weeks: int = 5) -> List[Dict]:
        """Get historical salary changes for a player"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM dfs_salaries 
                WHERE player_id = ? 
                ORDER BY week DESC, season DESC
                LIMIT ?
            """, (player_id, weeks))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    db_manager = DatabaseManager()
    collector = DFSSalaryCollector(db_manager)
    
    # Collect current week salary data
    current_week = 10  # Example
    season = 2024
    
    salary_data = collector.collect_fantasypros_salary_changes(current_week, season)
    print(f"Collected {len(salary_data)} salary records")