#!/usr/bin/env python3
"""
Performance data analysis script for stock-pulse project.
Analyzes and compares performance results from different optimization configurations.
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Tuple
import statistics


def load_all_performance_data(results_dir: str = "performance_results") -> List[Dict[str, Any]]:
    """Load all performance results from the results directory."""
    all_results = []
    
    for filename in sorted(os.listdir(results_dir)):
        if filename.startswith("performance_results_") and filename.endswith(".json"):
            filepath = os.path.join(results_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    results = json.load(f)
                    if isinstance(results, list):
                        all_results.extend(results)
                    else:
                        all_results.append(results)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return all_results


def group_by_optimization_config(data: List[Dict[str, Any]]) -> Dict[Tuple, List[Dict[str, Any]]]:
    """Group performance data by optimization configuration."""
    groups = defaultdict(list)
    
    for result in data:
        if "enabled_optimizations" in result:
            config_key = tuple(sorted(result["enabled_optimizations"]))
            groups[config_key].append(result)
        else:
            # Handle old data without optimization config
            groups[()].append(result)
    
    return dict(groups)


def calculate_statistics(times: List[float]) -> Dict[str, float]:
    """Calculate performance statistics for a list of execution times."""
    if not times:
        return {}
    
    return {
        "count": len(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "p95": sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
    }


def analyze_performance_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze performance data and generate comprehensive report."""
    print("=" * 80)
    print("PERFORMANCE DATA ANALYSIS REPORT")
    print("=" * 80)
    
    # Group by optimization configuration
    config_groups = group_by_optimization_config(data)
    
    # Separate by function
    function_data = defaultdict(lambda: defaultdict(list))
    
    for result in data:
        function_name = result["function_name"]
        if "enabled_optimizations" in result:
            config_key = tuple(sorted(result["enabled_optimizations"]))
        else:
            config_key = ()
        
        if result.get("success", False):
            function_data[function_name][config_key].append(result["execution_time_seconds"])
    
    # Generate report
    report = {
        "total_tests": len(data),
        "successful_tests": len([r for r in data if r.get("success", False)]),
        "configurations": {},
        "function_analysis": {}
    }
    
    print(f"\n📊 OVERVIEW:")
    print(f"  Total test runs: {report['total_tests']}")
    print(f"  Successful runs: {report['successful_tests']}")
    print(f"  Success rate: {(report['successful_tests']/report['total_tests']*100):.1f}%")
    
    # Analyze each configuration
    print(f"\n🔧 CONFIGURATION ANALYSIS:")
    print("-" * 60)
    
    for config_key, results in config_groups.items():
        config_name = ", ".join(config_key) if config_key else "baseline (no optimizations)"
        successful_results = [r for r in results if r.get("success", False)]
        
        print(f"\nConfiguration: {config_name}")
        print(f"  Total runs: {len(results)}")
        print(f"  Successful runs: {len(successful_results)}")
        
        if successful_results:
            # Separate by function
            market_watch_times = [r["execution_time_seconds"] for r in successful_results 
                                if r["function_name"] == "get_market_watch_data"]
            price_change_times = [r["execution_time_seconds"] for r in successful_results 
                                if r["function_name"] == "get_price_change"]
            
            if market_watch_times:
                mw_stats = calculate_statistics(market_watch_times)
                print(f"  Market Watch Data:")
                print(f"    Average: {mw_stats['mean']:.3f}s")
                print(f"    Median:  {mw_stats['median']:.3f}s")
                print(f"    Min:     {mw_stats['min']:.3f}s")
                print(f"    Max:     {mw_stats['max']:.3f}s")
                print(f"    Std Dev: {mw_stats['stdev']:.3f}s")
            
            if price_change_times:
                pc_stats = calculate_statistics(price_change_times)
                print(f"  Price Change:")
                print(f"    Average: {pc_stats['mean']:.3f}s")
                print(f"    Median:  {pc_stats['median']:.3f}s")
                print(f"    Min:     {pc_stats['min']:.3f}s")
                print(f"    Max:     {pc_stats['max']:.3f}s")
                print(f"    Std Dev: {pc_stats['stdev']:.3f}s")
    
    # Find best performing configurations
    print(f"\n🏆 BEST PERFORMING CONFIGURATIONS:")
    print("-" * 60)
    
    # Market Watch Data
    mw_best_config = None
    mw_best_time = float('inf')
    
    for config_key, results in config_groups.items():
        mw_times = [r["execution_time_seconds"] for r in results 
                   if r["function_name"] == "get_market_watch_data" and r.get("success", False)]
        if mw_times:
            avg_time = statistics.mean(mw_times)
            if avg_time < mw_best_time:
                mw_best_time = avg_time
                mw_best_config = config_key
    
    if mw_best_config:
        config_name = ", ".join(mw_best_config) if mw_best_config else "baseline (no optimizations)"
        print(f"Market Watch Data: {config_name} ({mw_best_time:.3f}s avg)")
    
    # Price Change
    pc_best_config = None
    pc_best_time = float('inf')
    
    for config_key, results in config_groups.items():
        pc_times = [r["execution_time_seconds"] for r in results 
                   if r["function_name"] == "get_price_change" and r.get("success", False)]
        if pc_times:
            avg_time = statistics.mean(pc_times)
            if avg_time < pc_best_time:
                pc_best_time = avg_time
                pc_best_config = config_key
    
    if pc_best_config:
        config_name = ", ".join(pc_best_config) if pc_best_config else "baseline (no optimizations)"
        print(f"Price Change: {config_name} ({pc_best_time:.3f}s avg)")
    
    # Performance trends over time
    print(f"\n📈 PERFORMANCE TRENDS:")
    print("-" * 60)
    
    # Sort by timestamp
    sorted_data = sorted(data, key=lambda x: x.get("timestamp", ""))
    
    # Group by function and analyze trends
    for function_name in ["get_market_watch_data", "get_price_change"]:
        function_results = [r for r in sorted_data 
                          if r["function_name"] == function_name and r.get("success", False)]
        
        if len(function_results) >= 3:
            # Calculate trend (comparing first third vs last third)
            third = len(function_results) // 3
            first_third = [r["execution_time_seconds"] for r in function_results[:third]]
            last_third = [r["execution_time_seconds"] for r in function_results[-third:]]
            
            first_avg = statistics.mean(first_third)
            last_avg = statistics.mean(last_third)
            trend = ((last_avg - first_avg) / first_avg) * 100
            
            trend_desc = "improving" if trend < -5 else "degrading" if trend > 5 else "stable"
            print(f"{function_name}: {trend_desc} ({trend:+.1f}% change)")
    
    # Optimization impact analysis
    print(f"\n⚡ OPTIMIZATION IMPACT:")
    print("-" * 60)
    
    # Find baseline (no optimizations)
    baseline_config = None
    for config_key in config_groups.keys():
        if not config_key:  # Empty tuple means no optimizations
            baseline_config = config_key
            break
    
    if baseline_config is not None:
        baseline_results = config_groups[baseline_config]
        baseline_mw_times = [r["execution_time_seconds"] for r in baseline_results 
                           if r["function_name"] == "get_market_watch_data" and r.get("success", False)]
        baseline_pc_times = [r["execution_time_seconds"] for r in baseline_results 
                           if r["function_name"] == "get_price_change" and r.get("success", False)]
        
        baseline_mw_avg = statistics.mean(baseline_mw_times) if baseline_mw_times else 0
        baseline_pc_avg = statistics.mean(baseline_pc_times) if baseline_pc_times else 0
        
        print(f"Baseline Performance:")
        print(f"  Market Watch Data: {baseline_mw_avg:.3f}s")
        print(f"  Price Change: {baseline_pc_avg:.3f}s")
        
        print(f"\nOptimization Impact vs Baseline:")
        for config_key, results in config_groups.items():
            if config_key != baseline_config:
                config_name = ", ".join(config_key) if config_key else "baseline"
                
                mw_times = [r["execution_time_seconds"] for r in results 
                           if r["function_name"] == "get_market_watch_data" and r.get("success", False)]
                pc_times = [r["execution_time_seconds"] for r in results 
                           if r["function_name"] == "get_price_change" and r.get("success", False)]
                
                if mw_times and baseline_mw_avg > 0:
                    mw_avg = statistics.mean(mw_times)
                    mw_improvement = ((baseline_mw_avg - mw_avg) / baseline_mw_avg) * 100
                    print(f"  {config_name}:")
                    print(f"    Market Watch: {mw_avg:.3f}s ({mw_improvement:+.1f}%)")
                
                if pc_times and baseline_pc_avg > 0:
                    pc_avg = statistics.mean(pc_times)
                    pc_improvement = ((baseline_pc_avg - pc_avg) / baseline_pc_avg) * 100
                    print(f"    Price Change: {pc_avg:.3f}s ({pc_improvement:+.1f}%)")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    
    return report


def main():
    """Main function to run performance analysis."""
    print("Loading performance data...")
    data = load_all_performance_data()
    
    if not data:
        print("No performance data found!")
        return
    
    print(f"Loaded {len(data)} performance records")
    
    # Run analysis
    analyze_performance_data(data)


if __name__ == "__main__":
    main()
