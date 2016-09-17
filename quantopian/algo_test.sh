#!/bin/bash

FREQUENCY=minute # can be minute or daily
CAPITAL_BASE=100000
ALGO_FILE=algo/intraday_levels_algorithm.py
START_DATE=2011-1-1
END_DATE=2012-1-1

python -m zipline run --data-frequency ${FREQUENCY} --capital-base ${CAPITAL_BASE} --algofile ${ALGO_FILE} --start ${START_DATE} --end ${END_DATE}