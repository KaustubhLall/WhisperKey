"""
OpenAI Billing API integration for cost tracking
"""
import requests
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from database import CostRecord, TranscriptionDatabase

logger = logging.getLogger("billing")

class OpenAIBillingAPI:
    """Handles OpenAI Billing API integration for cost tracking"""
    
    def __init__(self, api_key: str, config: Dict):
        self.api_key = api_key
        self.config = config
        self.db = TranscriptionDatabase()
        self.base_url = "https://api.openai.com/v1"
        
        # Create API key hash for multi-key support
        self.api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def is_cost_tracking_enabled(self) -> bool:
        """Check if cost tracking is enabled in config"""
        return self.config.get('cost_tracking', {}).get('enabled', False)
    
    def should_sync_costs(self) -> bool:
        """Check if cost sync is needed (≥24 hours since last fetch)"""
        if not self.is_cost_tracking_enabled():
            return False
        
        last_sync = self.db.get_last_cost_sync()
        if not last_sync:
            logger.info("No previous cost sync found, sync needed")
            return True
        
        try:
            last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            time_diff = datetime.now() - last_sync_dt.replace(tzinfo=None)
            
            hours_since_sync = time_diff.total_seconds() / 3600
            sync_needed = hours_since_sync >= 24
            
            logger.info(f"Hours since last sync: {hours_since_sync:.1f}, sync needed: {sync_needed}")
            return sync_needed
            
        except Exception as e:
            logger.error(f"Error checking sync timing: {e}")
            return True  # Default to sync if we can't determine
    
    def fetch_costs(self, start_date: str, end_date: str) -> Optional[Dict]:
        """Fetch costs from OpenAI Billing API"""
        if not self.is_cost_tracking_enabled():
            logger.warning("Cost tracking is disabled")
            return None
        
        url = f"{self.base_url}/costs"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        try:
            logger.info(f"Fetching costs from {start_date} to {end_date}")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched cost data: {len(data.get('data', []))} records")
                return data
            elif response.status_code == 401:
                logger.error("API key unauthorized for billing access")
                return None
            elif response.status_code == 403:
                logger.error("API key lacks billing permissions")
                return None
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("API request timeout")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("API connection error")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching costs: {e}")
            return None
    
    def sync_daily_costs(self, days_back: int = 30) -> bool:
        """Sync daily costs for the past N days"""
        if not self.is_cost_tracking_enabled():
            logger.warning("Cost tracking is disabled, skipping sync")
            return False
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Fetch costs from API
            cost_data = self.fetch_costs(start_str, end_str)
            if not cost_data:
                logger.error("Failed to fetch cost data")
                return False
            
            # Process and store cost records
            records_added = 0
            for daily_cost in cost_data.get('data', []):
                try:
                    date = daily_cost.get('date', '')
                    cost_usd = float(daily_cost.get('cost', 0.0))
                    
                    if date and cost_usd >= 0:
                        cost_record = CostRecord(
                            date=date,
                            cost_usd=cost_usd,
                            raw_json=json.dumps(daily_cost),
                            last_updated=datetime.now().isoformat(),
                            api_key_hash=self.api_key_hash
                        )
                        
                        record_id = self.db.add_cost_record(cost_record)
                        if record_id:
                            records_added += 1
                            logger.debug(f"Added cost record for {date}: ${cost_usd:.4f}")
                        
                except Exception as e:
                    logger.error(f"Error processing cost record: {e}")
                    continue
            
            logger.info(f"Cost sync completed: {records_added} records added/updated")
            return records_added > 0
            
        except Exception as e:
            logger.error(f"Error during cost sync: {e}")
            return False
    
    def get_monthly_spend(self, year: int = None, month: int = None) -> float:
        """Get monthly spend from database"""
        if not self.is_cost_tracking_enabled():
            return 0.0
        
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        return self.db.get_monthly_cost(year, month)
    
    def get_cost_breakdown(self, limit: int = 30) -> List[CostRecord]:
        """Get detailed cost breakdown"""
        if not self.is_cost_tracking_enabled():
            return []
        
        return self.db.get_cost_history(limit)
    
    def manual_refresh(self, callback=None) -> bool:
        """Manual cost refresh triggered by user"""
        logger.info("Manual cost refresh requested")
        
        try:
            success = self.sync_daily_costs(days_back=60)  # Sync more days on manual refresh
            
            if callback:
                callback(success)
            
            return success
            
        except Exception as e:
            logger.error(f"Error during manual refresh: {e}")
            if callback:
                callback(False)
            return False


def cli_sync_costs(api_key: str, config: Dict) -> bool:
    """Standalone CLI function for cost syncing"""
    print("OpenAI Cost Sync Tool")
    print("=" * 20)
    
    try:
        billing = OpenAIBillingAPI(api_key, config)
        
        if not billing.is_cost_tracking_enabled():
            print("❌ Cost tracking is disabled in configuration")
            return False
        
        print("🔄 Syncing costs from OpenAI API...")
        success = billing.sync_daily_costs(days_back=90)  # More days for CLI
        
        if success:
            # Show current month spend
            now = datetime.now()
            monthly_spend = billing.get_monthly_spend(now.year, now.month)
            print(f"✅ Sync completed successfully")
            print(f"💰 Current month spend: ${monthly_spend:.2f}")
            
            # Show recent cost breakdown
            print("\n📊 Recent cost breakdown:")
            costs = billing.get_cost_breakdown(10)
            for cost in costs[:5]:
                print(f"  {cost.date}: ${cost.cost_usd:.4f}")
            
            return True
        else:
            print("❌ Cost sync failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    import sys
    import os
    import yaml
    from pathlib import Path
    
    # Load config for standalone usage
    config_path = Path(__file__).parent / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    # Get API key from environment or config
    api_key = os.getenv('OPENAI_API_KEY') or config.get('transcription', {}).get('api_key', '')
    
    if not api_key:
        print("❌ No OpenAI API key found. Set OPENAI_API_KEY environment variable or add to config.yaml")
        sys.exit(1)
    
    # Run CLI sync
    success = cli_sync_costs(api_key, config)
    sys.exit(0 if success else 1)
