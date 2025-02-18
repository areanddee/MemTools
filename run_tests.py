#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from preprocessor_analyzer import EnhancedModuleAnalyzer

class TestRunner:
    def __init__(self, tests_root: Path):
        self.tests_root = Path(tests_root)
        self.results = {}

    def discover_tests(self):
        """Find all test directories that contain preprocessor_config.json."""
        test_dirs = []
        for d in self.tests_root.glob("test*"):
            if d.is_dir() and (d / "preprocessor_config.json").exists():
                test_dirs.append(d)
        return sorted(test_dirs)

    def run_single_test(self, test_dir: Path):
        """Run analyzer on a single test directory."""
        print(f"\nRunning test in {test_dir.name}")
        print("=" * 50)
        
        config_file = test_dir / "preprocessor_config.json"
        with open(config_file) as f:
            config = json.load(f)
            if "test_description" in config["preprocessor_config"]:
                print(f"Test description: {config['preprocessor_config']['test_description']}")
        
        # Initialize analyzer for this test
        analyzer = EnhancedModuleAnalyzer(str(test_dir), str(config_file))
        
        # Find main program file
        main_program = None
        for f90_file in test_dir.glob("*.F90"):
            with open(f90_file) as f:
                if 'program' in f.read().lower():
                    main_program = f90_file
                    break
        
        if not main_program:
            print("No main program found, analyzing all files separately")
            test_results = {}
            for f90_file in test_dir.glob("*.F90"):
                print(f"Analyzing {f90_file.name}")
                result = analyzer.analyze_module(f90_file.name)
                test_results.update(result)  # Merge results at top level
        else:
            print(f"Analyzing from main program: {main_program.name}")
            test_results = analyzer.analyze_module(main_program.name)
            
        # Save results for this test
        output_file = test_dir / "memory_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(test_results, f, indent=2)
            
        print(f"\nResults saved to {output_file}")
        return test_results

    def run_all_tests(self):
        """Discover and run all tests."""
        test_dirs = self.discover_tests()
        print(f"Found {len(test_dirs)} test directories")
        
        for test_dir in test_dirs:
            try:
                self.results[test_dir.name] = self.run_single_test(test_dir)
            except Exception as e:
                print(f"Error in {test_dir.name}: {str(e)}")
                self.results[test_dir.name] = {"error": str(e)}
        
        # Save summary of all results
        summary_file = self.tests_root / "test_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nAll test results saved to {summary_file}")

def main():
    parser = argparse.ArgumentParser(description="Run memory analysis tests")
    parser.add_argument("--tests-dir", default="tests",
                       help="Root directory containing test subdirectories")
    parser.add_argument("--test", help="Run specific test (e.g., test1)")
    args = parser.parse_args()
    
    runner = TestRunner(args.tests_dir)
    
    if args.test:
        # Run specific test
        test_dir = Path(args.tests_dir) / args.test
        if not test_dir.is_dir():
            raise NotADirectoryError(f"Test directory {args.test} not found")
        runner.run_single_test(test_dir)
    else:
        # Run all tests
        runner.run_all_tests()

if __name__ == "__main__":
    main()
