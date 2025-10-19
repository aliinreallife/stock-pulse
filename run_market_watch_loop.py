"""
Run get_market_watch_data every 90 seconds until stopped.
Press Ctrl+C to stop the loop.
"""

import time
import json
import os
from datetime import datetime
from get_market_watch_data import get_market_watch_data

def run_market_watch_loop():
    """Run market watch data collection every 90 seconds."""
    print("Starting market watch data collection loop...")
    print("Running every 90 seconds")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            start_time = datetime.now()
            
            print(f"\n[{start_time.strftime('%H:%M:%S')}] Iteration {iteration} - Collecting market watch data...")
            
            try:
                # Get market watch data
                data = get_market_watch_data()
                
                # Save the data (same logic as in get_market_watch_data.py)
                
                timestamp = start_time.strftime("%Y%m%d_%H%M%S")
                export_dir = "export/market_watch"
                os.makedirs(export_dir, exist_ok=True)
                
                save_path = f"{export_dir}/market_watch_{timestamp}.json"
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Success: Market watch data saved to: {save_path}")
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                print(f"⏱️  Completed in {duration:.1f} seconds")
                
            except Exception as e:
                print(f"❌ Error collecting data: {e}")
            
            # Wait 90 seconds before next iteration
            print(f"⏳ Waiting 90 seconds until next collection...")
            time.sleep(90)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Stopped by user (Ctrl+C)")
        print(f"Total iterations completed: {iteration}")
        print("Market watch data collection stopped.")

if __name__ == "__main__":
    run_market_watch_loop()
