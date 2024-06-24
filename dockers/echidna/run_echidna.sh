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
    echo "  run_medusa.sh SOURCE TIMEOUT SEED"
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

OUTBASE=$(basename $SOURCE .sol).echidna.log

LOGFILE=$OUTDIR/$OUTBASE
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


# =========================
# Fuzzing setup
# =========================

# taken from daedaluzz
cat > echidna-config.yaml <<_EOT_
testMode: "property"
testLimit: 1073741823
prefix: "echidna_"
timeout: $TIME_LIMIT
coverage: true
stopOnFail: true
seqLen: 100
shrinkLimit: 5000
format: text
codeSize: 0xc00000
seed: $SEED
solcArgs: "--evm-version paris --optimize --optimize-runs 99999"
_EOT_

# =========================
# Start Fuzzing
# =========================

echo "=> Echidna Fuzzing:" >> $LOGFILE
/usr/bin/time -o $TIMEFILE -f "%e" -- echidna $SOURCE --contract Maze --config echidna-config.yaml &>> $LOGFILE
