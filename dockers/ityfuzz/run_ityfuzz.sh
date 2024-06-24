#!/bin/bash

# =========================
# Parse Arguments
# =========================

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Input seed for fuzzer

if [ "$#" -ne 3 ]
then
    echo "USAGE:"
    echo "  run_ityfuzz.sh SOURCE TIMEOUT SEED"
    exit 1
fi

SOURCE=$1
TIME_LIMIT=$2
((TIME_LIMIT*=60)) # convert to seconds
SEED=$3

# =========================
# Environment setup
# =========================

# through the container copy we might have changed the
# owner so we set it back to maze
sudo chown -R maze:maze $SOURCE

HOMEDIR=/home/maze
WORKDIR=$HOMEDIR/workspace
OUTDIR=$WORKDIR/outputs
BUILDDIR=$WORKDIR/build

OUTBASE=$(basename $SOURCE .sol).ityfuzz.log

LOGFILE=$OUTDIR/$OUTBASE
FAILFILE=$OUTDIR/$OUTBASE.fail
TIMEFILE=$OUTDIR/$OUTBASE.time

# Create dummy file to indicate running start
touch $WORKDIR/.start

# Create a log file
touch $LOGFILE

# =========================
# Compilation
# =========================

# set and install specific solidity version
solc-select install 0.8.26
solc-select use 0.8.26

echo "=> Solc Compilation:" >> $LOGFILE
solc $SOURCE --abi --bin --overwrite -o $BUILDDIR --evm-version paris --optimize --optimize-runs 99999 &>> $LOGFILE

# check if compilation was successful
if [ $? -ne 0 ]; then
    echo "failure" > $FAILFILE
fi

# =========================
# Start Fuzzing
# =========================

echo "=> ItyFuzz Fuzzing:" >> $LOGFILE
/usr/bin/time -o $TIMEFILE -f "%e" -- timeout $TIME_LIMIT ityfuzz evm -t "$BUILDDIR/*" --seed $SEED &>> $LOGFILE
