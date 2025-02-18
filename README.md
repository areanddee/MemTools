# MemTools

Tools for extracting memory usage data for a set of .F90 files.

Currently, runs two trivial examples with static and allocatable arrays.
The key tools are:
preprocessor_analyzer.py and run_tests.py

Tests are located in ./tests currently there are two:
                      ---- ./test1
                      ---- ./test2
To run the tests:
> python run_tests.py --test test{1,2}

