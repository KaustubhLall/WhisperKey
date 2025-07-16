"""
OpenAI Usage and Costs API integration for WhisperKey
Based on OpenAI's official Admin API documentation
"""
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, List

import requests

from .database import CostRecord, TranscriptionDatabase

logger = logging.getLogger("billing")


class OpenAIUsageAPI:
    """Handles OpenAI Usage and Costs API integration using Admin API keys"""

    def __init__(self, admin_api_key: str, config: Dict):
        self.admin_api_key = admin_api_key
        self.config = config
        self.db = TranscriptionDatabase()
        self.base_url = "https://api.openai.com/v1/organization"

        # Create API key hash for multi-key support
        self.api_key_hash = hashlib.sha256(admin_api_key.encode()).hexdigest()[:16]

        logger.info("OpenAI Usage API initialized with admin key")

    def is_cost_tracking_enabled(self) -> bool:
        """Check if cost tracking is enabled and admin key is available"""
        enabled = self.config.get('cost_tracking', {}).get('enabled', False)
        has_admin_key = self.admin_api_key is not None

        if enabled and not has_admin_key:
            logger.warning("Cost tracking enabled but no admin API key available")
            return False

        return enabled and has_admin_key

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.admin_api_key}",
            "Content-Type": "application/json",
        }

    def _get_paginated_data(self, url: str, params: Dict) -> List[Dict]:
        """Retrieve paginated data from the API"""
        headers = self._get_headers()
        all_data = []
        page_cursor = None

        while True:
            if page_cursor:
                params["page"] = page_cursor

            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)

                if response.status_code == 200:
                    data_json = response.json()
                    all_data.extend(data_json.get("data", []))

                    page_cursor = data_json.get("next_page")
                    if not page_cursor:
                        break
                elif response.status_code == 401:
                    logger.error("Admin API key unauthorized")
                    break
                elif response.status_code == 403:
                    logger.error("Admin API key lacks required permissions")
                    break
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    break

            except requests.exceptions.Timeout:
                logger.error("API request timeout")
                break
            except requests.exceptions.ConnectionError:
                logger.error("API connection error")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break

        logger.info(f"Retrieved {len(all_data)} data points from API")
        return all_data

    def fetch_completions_usage(self, days_back: int = 30) -> List[Dict]:
        """Fetch completions usage data from the past N days"""
        if not self.is_cost_tracking_enabled():
            logger.warning("Cost tracking is disabled")
            return []

        # Calculate start time
        start_time = int(time.time()) - (days_back * 24 * 60 * 60)

        url = f"{self.base_url}/usage/completions"
        params = {
            "start_time": start_time,
            "bucket_width": "1d",  # Daily buckets
            "group_by": ["model"],  # Group by model for better insights
            "limit": days_back,
        }

        logger.info(f"Fetching completions usage for last {days_back} days")
        return self._get_paginated_data(url, params)

    def fetch_costs_data(self, days_back: int = 30) -> List[Dict]:
        """Fetch costs data from the past N days"""
        if not self.is_cost_tracking_enabled():
            logger.warning("Cost tracking is disabled")
            return []

        # Calculate start time
        start_time = int(time.time()) - (days_back * 24 * 60 * 60)

        url = f"{self.base_url}/costs"
        params = {
            "start_time": start_time,
            "bucket_width": "1d",  # Daily buckets
            "group_by": ["line_item"],  # Group by line item
            "limit": days_back,
        }

        logger.info(f"Fetching costs data for last {days_back} days")
        return self._get_paginated_data(url, params)

    def sync_usage_and_costs(self, days_back: int = 30) -> bool:
        """Sync both usage and cost data"""
        try:
            # Fetch costs data (this is what we mainly care about for billing)
            costs_data = self.fetch_costs_data(days_back)

            if not costs_data:
                logger.warning("No costs data retrieved")
                return False

            # Process and store cost records
            records_added = 0
            cost_records = self._parse_costs_data(costs_data)

            for cost_record in cost_records:
                record_id = self.db.add_cost_record(cost_record)
                if record_id:
                    records_added += 1
                    logger.debug(f"Added cost record for {cost_record.date}: ${cost_record.cost_usd:.4f}")

            logger.info(f"Cost sync completed: {records_added} records added/updated")
            return records_added > 0

        except Exception as e:
            logger.error(f"Error during sync: {e}")
            return False

    def get_daily_cost(self, date_str: str) -> float:
        """Get cost for a specific date with detailed logging"""
        if not self.is_cost_tracking_enabled():
            logger.debug(f"Cost tracking disabled, returning 0 for {date_str}")
            return 0.0

        try:
            costs = self.get_cost_breakdown(90)
            logger.info(f"Looking for cost data for {date_str} in {len(costs)} records")

            for cost in costs:
                logger.debug(f"Checking cost record: {cost.date} = ${cost.cost_usd:.4f}")
                if cost.date == date_str:
                    logger.info(f"Found cost for {date_str}: ${cost.cost_usd:.4f}")
                    return cost.cost_usd

            logger.info(f"No cost data found for {date_str}")
            return 0.0
        except Exception as e:
            logger.error(f"Error getting daily cost for {date_str}: {e}")
            return 0.0

    def _parse_costs_data(self, costs_data: List[Dict]) -> List[CostRecord]:
        """Parse costs data into CostRecord objects with detailed logging"""
        try:
            records = []
            logger.info(f"Parsing {len(costs_data)} cost data entries")
            
            for item in costs_data:
                try:
                    date_str = item.get('date', '')
                    cost_usd = item.get('cost', 0.0)
                    raw_json = json.dumps(item)
                    
                    record = CostRecord(
                        date=date_str,
                        cost_usd=cost_usd,
                        api_key_hash=self.api_key_hash,
                        raw_json=raw_json,
                        last_updated=datetime.now().isoformat()
                    )
                    records.append(record)
                    
                except Exception as e:
                    logger.error(f"Error parsing cost item: {e}")
            
            logger.info(f"Successfully parsed {len(records)} cost records")
            return records
            
        except Exception as e:
            logger.error(f"Error parsing costs data: {e}")
            return []

    def manual_refresh(self, callback=None) -> bool:
        """Manual cost refresh triggered by user with detailed logging"""
        try:
            logger.info("Starting manual cost refresh")
            
            # Sync data
            success = self.sync_usage_and_costs(30)
            
            if success:
                logger.info("Manual cost refresh completed successfully")
            else:
                logger.error("Manual cost refresh failed")
                
            # Call callback if provided
            if callback:
                callback(success)
                
            return success
            
        except Exception as e:
            logger.error(f"Error in manual refresh: {e}")
            if callback:
                callback(False)
            return False
            
    def get_monthly_spend(self, year, month) -> float:
        """Get total spend for a specific month"""
        try:
            if not self.is_cost_tracking_enabled():
                return 0.0
                
            # Format month string (e.g., "2025-07")
            month_str = f"{year:04d}-{month:02d}"
            
            # Get all costs from database
            all_costs = self.db.get_all_costs(100)
            
            # Filter by month and sum costs
            monthly_costs = [cost for cost in all_costs if cost.date.startswith(month_str)]
            total = sum(cost.cost_usd for cost in monthly_costs)
            
            logger.debug(f"Monthly spend for {month_str}: ${total:.2f}")
            return total
            
        except Exception as e:
            logger.error(f"Error getting monthly spend: {e}")
            return 0.0
            
    def get_cost_breakdown(self, days_back=30) -> List[CostRecord]:
        """Get cost breakdown for the past N days"""
        try:
            if not self.is_cost_tracking_enabled():
                return []
                
            # Get all costs from database
            all_costs = self.db.get_all_costs(days_back)
            
            # Sort by date (newest first)
            sorted_costs = sorted(all_costs, key=lambda x: x.date, reverse=True)
            
            return sorted_costs
            
        except Exception as e:
            logger.error(f"Error getting cost breakdown: {e}")
            return []
            
    def get_usage_analytics(self, days_back=30) -> Dict:
        """Get usage analytics for the past N days"""
        try:
            if not self.is_cost_tracking_enabled():
                return {"total_cost": 0.0, "total_requests": 0, "daily_costs": []}
                
            # Get cost breakdown
            costs = self.get_cost_breakdown(days_back)
            
            # Calculate totals
            total_cost = sum(cost.cost_usd for cost in costs)
            
            # Get daily breakdown
            daily_costs = {}
            for cost in costs:
                if cost.date not in daily_costs:
                    daily_costs[cost.date] = 0.0
                daily_costs[cost.date] += cost.cost_usd
                
            # Format for return
            return {
                "total_cost": total_cost,
                "total_requests": len(costs),
                "daily_costs": [{"date": date, "cost": cost} for date, cost in daily_costs.items()]
            }
            
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            return {"total_cost": 0.0, "total_requests": 0, "daily_costs": []}


# Legacy compatibility class
class OpenAIBillingAPI(OpenAIUsageAPI):
    """Legacy compatibility wrapper for the updated Usage API"""

    def __init__(self, api_key: str, config: Dict):
        # Use admin API key if available, fallback to regular API key
        import os
        admin_api_key = os.getenv('OPENAI_ADMIN_API_KEY')

        if admin_api_key:
            super().__init__(admin_api_key, config)
            logger.info("Using admin API key for billing access")
        else:
            logger.warning("No admin API key found - billing features will be limited")
            # Initialize with dummy key to maintain compatibility
            super().__init__("dummy_key", config)

    def fetch_costs(self, start_date: str, end_date: str) -> Optional[Dict]:
        """Legacy method - redirects to new costs API"""
        try:
            # Calculate days between dates
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            days_back = (end_dt - start_dt).days + 1

            costs_data = self.fetch_costs_data(days_back)

            # Convert to legacy format
            return {
                "data": costs_data,
                "message": "Data retrieved from OpenAI Admin API"
            }

        except Exception as e:
            logger.error(f"Error in legacy fetch_costs: {e}")
            return None

    def sync_daily_costs(self, days_back: int = 30) -> bool:
        """Legacy method - redirects to new sync method"""
        return self.sync_usage_and_costs(days_back)


def cli_sync_costs(api_key: str, config: Dict) -> bool:
    """Standalone CLI function for cost syncing using Admin API"""
    print("OpenAI Usage & Costs Sync Tool")
    print("=" * 35)

    try:
        import os
        admin_api_key = os.getenv('OPENAI_ADMIN_API_KEY')

        if not admin_api_key:
            print("❌ No admin API key found. Set OPENAI_ADMIN_API_KEY environment variable.")
            print("   Admin API keys are required for billing data access.")
            print("   Get one at: https://platform.openai.com/settings/organization/admin-keys")
            return False

        usage_api = OpenAIUsageAPI(admin_api_key, config)

        if not usage_api.is_cost_tracking_enabled():
            print("❌ Cost tracking is disabled in configuration")
            return False

        print("🔄 Syncing usage and costs from OpenAI Admin API...")
        success = usage_api.sync_usage_and_costs(days_back=90)  # More days for CLI

        if success:
            # Show current month spend
            now = datetime.now()
            monthly_spend = usage_api.get_monthly_spend(now.year, now.month)
            print(f"✅ Sync completed successfully")
            print(f"💰 Current month spend: ${monthly_spend:.2f}")

            # Show usage analytics
            analytics = usage_api.get_usage_analytics(30)
            if analytics and "error" not in analytics:
                print(f"📊 Usage Analytics (Last 30 days):")
                print(f"   Total Cost: ${analytics['total_cost']:.4f}")
                print(f"   Total API Requests: {analytics['total_requests']:,}")

                # Check for token and model data
                if 'total_input_tokens' in analytics:
                    print(f"   Total Input Tokens: {analytics['total_input_tokens']:,}")
                if 'total_output_tokens' in analytics:
                    print(f"   Total Output Tokens: {analytics['total_output_tokens']:,}")
                if 'models_used' in analytics:
                    print(f"   Models Used: {len(analytics['models_used'])}")

            # Show recent cost breakdown
            print("\n📊 Recent cost breakdown:")
            costs = usage_api.get_cost_breakdown(10)
            for cost in costs[:5]:
                print(f"  {cost.date}: ${cost.cost_usd:.4f}")

            return True
        else:
            print("❌ Sync failed - check logs for details")
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
    config_path = Path(__file__).parent.parent / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {'cost_tracking': {'enabled': True}}

    # Run CLI sync
    success = cli_sync_costs("", config)
    sys.exit(0 if success else 1)
