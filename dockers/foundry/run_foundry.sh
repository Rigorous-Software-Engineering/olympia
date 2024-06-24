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
PROJECTDIR=$WORKDIR/foundry-project
TESTDIR=$PROJECTDIR/test

OUTBASE=$(basename $SOURCE .foundry.sol).foundry.log
TESTFILE=$(basename $SOURCE .foundry.sol).t.sol

LOGFILE=$OUTDIR/$OUTBASE

# Create dummy file to indicate running start
touch $WORKDIR/.start

# Create a log file
touch $LOGFILE

# seed randomness
RANDOM=$SEED


# =========================
# Compilation
# =========================

# set and install specific solidity version
solc-select install 0.8.26
solc-select use 0.8.26

# =========================
# Fuzzing setup
# =========================

echo "=> Foundry Project Setup" >> $LOGFILE

forge init --no-git foundry-project # start a new foundry project
cd foundry-project                  # move into the project
rm ./script/* ./src/* ./test/*      # remove default counter files
cp $SOURCE $TESTDIR/$TESTFILE       # copy source file into test folder

# overwrite foundry toml
cat > foundry.toml <<_EOT_
[profile.default]
src = "src"
out = "out"
test = "test"
libs = ["lib"]
optimizer = true
optimizer_runs = 99999
via_ir = false
evm_version = "paris"
solc_version = "0.8.26"
verbosity = 1

[fuzz]
# seed is set via flag
runs = 1000
max_test_rejects = 1073741823
dictionary_weight = 40
include_storage = true
include_push_bytes = true

[invariant]
runs = 1000
depth = 150
fail_on_revert = false
call_override = false
dictionary_weight = 80
include_storage = true
include_push_bytes = true
shrink_run_limit = 5000
_EOT_

forge build # build the current project

# =========================
# Start Fuzzing
# =========================

echo "=> Foundry Fuzzing:" >> $LOGFILE

START_TIME=$(date +%s)
END_TIME=$((START_TIME + TIME_LIMIT))
while true; do
    NOW_TIME=$(date +%s)
    if [ $END_TIME -lt $NOW_TIME ]; then
        break
    fi
    forge test --isolate --fuzz-seed $RANDOM --match-path $TESTFILE &>> $LOGFILE
done
