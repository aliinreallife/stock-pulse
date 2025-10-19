"""
Test TSE schemas on all exported data.
"""

import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from schemas import ClosingPriceResponse, BestLimitsResponse, TradeResponse

def test_all_schemas():
    """Test schemas on all exported data files."""
    export_dir = Path("export")
    
    # Get all instrument directories except full_market
    instrument_dirs = [d for d in export_dir.iterdir() if d.is_dir() and d.name != "full_market"]
    
    print("Testing TSE schemas on all exported data")
    print("=" * 50)
    
    total_tests = 0
    passed_tests = 0
    failed_files = []
    
    for instrument_dir in instrument_dirs:
        ins_code = instrument_dir.name
        print(f"\nTesting instrument: {ins_code}")
        
        # Test all closing price files
        closing_files = list(instrument_dir.glob("closing_price_*.json"))
        print(f"  Closing price files: {len(closing_files)}")
        
        for file_path in closing_files:
            total_tests += 1
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                closing_response = ClosingPriceResponse(**data)
                passed_tests += 1
                
            except Exception as e:
                failed_files.append((file_path.name, str(e)))
        
        # Test all best limits files
        best_limits_files = list(instrument_dir.glob("best_limits_*.json"))
        print(f"  Best limits files: {len(best_limits_files)}")
        
        for file_path in best_limits_files:
            total_tests += 1
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                best_limits_response = BestLimitsResponse(**data)
                passed_tests += 1
                
            except Exception as e:
                failed_files.append((file_path.name, str(e)))

        # Test all trade files
        trade_files = list(instrument_dir.glob("trade_*.json"))
        print(f"  Trade files: {len(trade_files)}")
        
        for file_path in trade_files:
            total_tests += 1
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                trade_response = TradeResponse(**data)
                passed_tests += 1
                
            except Exception as e:
                failed_files.append((file_path.name, str(e)))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Total files tested: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_files:
        print("\nFailed files:")
        for filename, error in failed_files:
            print(f"  {filename}: {error}")
    else:
        print("\nAll tests passed successfully.")

if __name__ == "__main__":
    test_all_schemas()