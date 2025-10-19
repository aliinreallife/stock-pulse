import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from get_market_watch_data import get_market_watch_data
from get_instrument_data import get_price_change


@dataclass
class OptimizationConfig:
    """Configuration for different optimizations that can be enabled/disabled."""
    use_orjson: bool = False
    use_parallel_market_watch: bool = False
    
    def to_dict(self) -> Dict[str, bool]:
        """Convert config to dictionary for JSON serialization."""
        return {
            "use_orjson": self.use_orjson,
            "use_parallel_market_watch": self.use_parallel_market_watch
        }
    
    def get_enabled_optimizations(self) -> List[str]:
        """Get list of enabled optimization names."""
        enabled = []
        if self.use_orjson:
            enabled.append("orjson")
        if self.use_parallel_market_watch:
            enabled.append("parallel_market_watch")
        return enabled


class PerformanceChecker:
    """Performance checker to measure execution times of API functions."""
    
    def __init__(self, results_dir: str = "performance_results"):
        self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)
    
    def measure_execution_time(self, func, *args, optimization_config: Optional[OptimizationConfig] = None, **kwargs) -> Dict[str, Any]:
        """Measure execution time of a function and return results."""
        # Use time.perf_counter() for more accurate timing
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        end_time = time.perf_counter()
        
        execution_time = end_time - start_time
        
        result_data = {
            "function_name": func.__name__,
            "execution_time_seconds": execution_time,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "error": error,
            "args": args,
            "kwargs": kwargs
        }
        
        # Add optimization configuration if provided
        if optimization_config:
            result_data["optimization_config"] = optimization_config.to_dict()
            result_data["enabled_optimizations"] = optimization_config.get_enabled_optimizations()
        
        return result_data
    
    def run_market_watch_performance_test(self, optimization_config: Optional[OptimizationConfig] = None) -> Dict[str, Any]:
        """Run performance test for get_market_watch_data function."""
        config_desc = ""
        if optimization_config:
            enabled = optimization_config.get_enabled_optimizations()
            config_desc = f" (with optimizations: {', '.join(enabled) if enabled else 'none'})"
        
        print(f"Running performance test for get_market_watch_data{config_desc}...")
        result = self.measure_execution_time(get_market_watch_data, optimization_config=optimization_config)
        print(f"Market watch data fetch completed in {result['execution_time_seconds']:.3f} seconds")
        return result
    
    def run_price_change_performance_test(self, ins_code: int = 28854105556435129, optimization_config: Optional[OptimizationConfig] = None) -> Dict[str, Any]:
        """Run performance test for get_price_change function."""
        config_desc = ""
        if optimization_config:
            enabled = optimization_config.get_enabled_optimizations()
            config_desc = f" (with optimizations: {', '.join(enabled) if enabled else 'none'})"
        
        print(f"Running performance test for get_price_change with ins_code: {ins_code}{config_desc}...")
        result = self.measure_execution_time(get_price_change, ins_code, optimization_config=optimization_config)
        print(f"Price change fetch completed in {result['execution_time_seconds']:.3f} seconds")
        return result
    
    def save_performance_results(self, results: List[Dict[str, Any]], filename: str = None) -> str:
        """Save performance results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_results_{timestamp}.json"
        
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Performance results saved to: {filepath}")
        return filepath
    
    def load_performance_history(self) -> List[Dict[str, Any]]:
        """Load all performance results from the results directory."""
        all_results = []
        
        for filename in os.listdir(self.results_dir):
            if filename.startswith("performance_results_") and filename.endswith(".json"):
                filepath = os.path.join(self.results_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        results = json.load(f)
                        if isinstance(results, list):
                            all_results.extend(results)
                        else:
                            all_results.append(results)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Sort by timestamp
        all_results.sort(key=lambda x: x.get("timestamp", ""))
        return all_results
    
    def compare_performance(self, function_name: str = None) -> Dict[str, Any]:
        """Compare performance metrics across different runs."""
        history = self.load_performance_history()
        
        if function_name:
            history = [r for r in history if r.get("function_name") == function_name]
        
        if not history:
            return {"message": "No performance data found"}
        
        # Calculate statistics
        execution_times = [r["execution_time_seconds"] for r in history if r.get("success", False)]
        
        if not execution_times:
            return {"message": "No successful executions found"}
        
        stats = {
            "function_name": function_name or "all_functions",
            "total_runs": len(history),
            "successful_runs": len(execution_times),
            "failed_runs": len(history) - len(execution_times),
            "average_time": sum(execution_times) / len(execution_times),
            "min_time": min(execution_times),
            "max_time": max(execution_times),
            "latest_time": execution_times[-1] if execution_times else None,
            "performance_trend": "improving" if len(execution_times) > 1 and execution_times[-1] < execution_times[0] else "stable"
        }
        
        return stats
    
    def run_full_performance_test(self, ins_code: int = 28854105556435129, optimization_config: Optional[OptimizationConfig] = None) -> List[Dict[str, Any]]:
        """Run both performance tests and save results."""
        config_desc = ""
        if optimization_config:
            enabled = optimization_config.get_enabled_optimizations()
            config_desc = f" (with optimizations: {', '.join(enabled) if enabled else 'none'})"
        
        print("=" * 50)
        print(f"Starting Full Performance Test{config_desc}")
        print("=" * 50)
        
        results = []
        
        # Test get_market_watch_data
        market_watch_result = self.run_market_watch_performance_test(optimization_config)
        results.append(market_watch_result)
        
        print("-" * 30)
        
        # Test get_price_change
        price_change_result = self.run_price_change_performance_test(ins_code, optimization_config)
        results.append(price_change_result)
        
        # Save results
        self.save_performance_results(results)
        
        # Show comparison
        print("\n" + "=" * 50)
        print("Performance Comparison")
        print("=" * 50)
        
        for function_name in ["get_market_watch_data", "get_price_change"]:
            comparison = self.compare_performance(function_name)
            if "message" not in comparison:
                print(f"\n{function_name}:")
                print(f"  Average time: {comparison['average_time']:.3f}s")
                print(f"  Min time: {comparison['min_time']:.3f}s")
                print(f"  Max time: {comparison['max_time']:.3f}s")
                print(f"  Latest time: {comparison['latest_time']:.3f}s")
                print(f"  Total runs: {comparison['total_runs']}")
                print(f"  Success rate: {comparison['successful_runs']}/{comparison['total_runs']}")
        
        return results
    
    def run_optimization_comparison_test(self, ins_code: int = 28854105556435129) -> Dict[str, Any]:
        """Run performance tests with different optimization configurations and compare results."""
        print("=" * 60)
        print("Starting Optimization Comparison Test")
        print("=" * 60)
        
        # Define different optimization configurations to test
        configs = [
            OptimizationConfig(),  # No optimizations (baseline)
            OptimizationConfig(use_orjson=True),  # Only orjson
            OptimizationConfig(use_parallel_market_watch=True),  # Only parallel market watch
            OptimizationConfig(use_orjson=True, use_parallel_market_watch=True),  # orjson + parallel
        ]
        
        all_results = []
        
        for i, config in enumerate(configs, 1):
            print(f"\n--- Configuration {i}/{len(configs)} ---")
            enabled = config.get_enabled_optimizations()
            config_name = f"Config {i}: {', '.join(enabled) if enabled else 'baseline (no optimizations)'}"
            print(f"Testing: {config_name}")
            
            results = self.run_full_performance_test(ins_code, config)
            all_results.extend(results)
            
            print(f"Completed configuration {i}")
            
            # Add small delay between configurations to avoid timing conflicts
            if i < len(configs):
                time.sleep(0.5)
        
        # Save all results
        self.save_performance_results(all_results, "optimization_comparison_results.json")
        
        # Generate comparison report
        self.generate_optimization_report()
        
        return {"total_configurations_tested": len(configs), "total_tests_run": len(all_results)}
    
    def generate_optimization_report(self):
        """Generate a detailed report comparing different optimization configurations."""
        print("\n" + "=" * 60)
        print("OPTIMIZATION COMPARISON REPORT")
        print("=" * 60)
        
        history = self.load_performance_history()
        
        # Group results by optimization configuration
        config_groups = {}
        for result in history:
            if "enabled_optimizations" in result:
                key = tuple(sorted(result["enabled_optimizations"]))
                if key not in config_groups:
                    config_groups[key] = []
                config_groups[key].append(result)
        
        if not config_groups:
            print("No optimization data found.")
            return
        
        # Calculate statistics for each configuration
        config_stats = {}
        for config_key, results in config_groups.items():
            config_name = ", ".join(config_key) if config_key else "baseline (no optimizations)"
            
            # Separate by function
            market_watch_times = [r["execution_time_seconds"] for r in results 
                                if r["function_name"] == "get_market_watch_data" and r.get("success", False)]
            price_change_times = [r["execution_time_seconds"] for r in results 
                                if r["function_name"] == "get_price_change" and r.get("success", False)]
            
            config_stats[config_name] = {
                "market_watch": {
                    "avg": sum(market_watch_times) / len(market_watch_times) if market_watch_times else 0,
                    "min": min(market_watch_times) if market_watch_times else 0,
                    "max": max(market_watch_times) if market_watch_times else 0,
                    "count": len(market_watch_times)
                },
                "price_change": {
                    "avg": sum(price_change_times) / len(price_change_times) if price_change_times else 0,
                    "min": min(price_change_times) if price_change_times else 0,
                    "max": max(price_change_times) if price_change_times else 0,
                    "count": len(price_change_times)
                }
            }
        
        # Find baseline (no optimizations)
        baseline_key = None
        for key in config_groups.keys():
            if not key:  # Empty tuple means no optimizations
                baseline_key = key
                break
        
        if baseline_key:
            baseline_name = "baseline (no optimizations)"
            baseline_market_watch = config_stats[baseline_name]["market_watch"]["avg"]
            baseline_price_change = config_stats[baseline_name]["price_change"]["avg"]
            
            print(f"\nBaseline Performance:")
            print(f"  Market Watch: {baseline_market_watch:.3f}s")
            print(f"  Price Change: {baseline_price_change:.3f}s")
            
            print(f"\nOptimization Impact:")
            for config_name, stats in config_stats.items():
                if config_name != baseline_name:
                    market_watch_improvement = ((baseline_market_watch - stats["market_watch"]["avg"]) / baseline_market_watch) * 100
                    price_change_improvement = ((baseline_price_change - stats["price_change"]["avg"]) / baseline_price_change) * 100
                    
                    print(f"\n{config_name}:")
                    print(f"  Market Watch: {stats['market_watch']['avg']:.3f}s ({market_watch_improvement:+.1f}%)")
                    print(f"  Price Change: {stats['price_change']['avg']:.3f}s ({price_change_improvement:+.1f}%)")
        
        # Find best performing configurations
        print(f"\nBest Performing Configurations:")
        
        # For market watch
        best_market_watch = min(config_stats.items(), key=lambda x: x[1]["market_watch"]["avg"])
        print(f"  Market Watch: {best_market_watch[0]} ({best_market_watch[1]['market_watch']['avg']:.3f}s)")
        
        # For price change
        best_price_change = min(config_stats.items(), key=lambda x: x[1]["price_change"]["avg"])
        print(f"  Price Change: {best_price_change[0]} ({best_price_change[1]['price_change']['avg']:.3f}s)")


def main():
    """Main function to run performance tests."""
    import sys
    
    checker = PerformanceChecker()
    
    # You can modify the ins_code here if needed
    ins_code = 28854105556435129
    
    # Check command line arguments for test type
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "comparison":
            # Run optimization comparison test
            print("Running optimization comparison test...")
            results = checker.run_optimization_comparison_test(ins_code)
            print(f"\nOptimization comparison test completed. Results saved in '{checker.results_dir}' directory.")
        elif test_type == "baseline":
            # Run baseline test (no optimizations)
            print("Running baseline performance test...")
            results = checker.run_full_performance_test(ins_code, OptimizationConfig())
            print(f"\nBaseline test completed. Results saved in '{checker.results_dir}' directory.")
        elif test_type == "orjson":
            # Run test with orjson optimization
            print("Running performance test with orjson optimization...")
            config = OptimizationConfig(use_orjson=True)
            results = checker.run_full_performance_test(ins_code, config)
            print(f"\nOrjson test completed. Results saved in '{checker.results_dir}' directory.")
        elif test_type == "parallel":
            # Run test with parallel market watch optimization
            print("Running performance test with parallel market watch optimization...")
            config = OptimizationConfig(use_parallel_market_watch=True)
            results = checker.run_full_performance_test(ins_code, config)
            print(f"\nParallel test completed. Results saved in '{checker.results_dir}' directory.")
        elif test_type == "both":
            # Run test with both optimizations
            print("Running performance test with both optimizations...")
            config = OptimizationConfig(use_orjson=True, use_parallel_market_watch=True)
            results = checker.run_full_performance_test(ins_code, config)
            print(f"\nBoth optimizations test completed. Results saved in '{checker.results_dir}' directory.")
        else:
            print("Unknown test type. Available options:")
            print("  baseline  - Run without optimizations")
            print("  orjson    - Run with orjson optimization")
            print("  parallel  - Run with parallel market watch optimization")
            print("  both      - Run with both optimizations")
            print("  comparison - Run all configurations and compare")
            return
    else:
        print("No test type provided. Available options:")
        print("  baseline  - Run without optimizations")
        print("  orjson    - Run with orjson optimization")
        print("  parallel  - Run with parallel market watch optimization")
        print("  both      - Run with both optimizations")
        print("  comparison - Run all configurations and compare")
        return


if __name__ == "__main__":
    main()
