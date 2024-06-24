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

OUTBASE=$(basename $SOURCE .sol).medusa.log

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

cat > medusa.json <<_EOT_
{
	"fuzzing": {
		"workers": 1,
		"workerResetLimit": 100,
		"timeout": $TIME_LIMIT,
		"testLimit": 0,
		"callSequenceLength":100,
		"corpusDirectory": "",
		"coverageEnabled": true,
		"targetContracts": [ "Maze" ],
		"targetContractsBalances": [],
		"constructorArgs": {},
		"deployerAddress": "0x30000",
		"senderAddresses": [
			"0x10000",
			"0x20000",
			"0x30000"
		],
		"blockNumberDelayMax": 60480,
		"blockTimestampDelayMax": 604800,
		"blockGasLimit": 125000000,
		"transactionGasLimit": 12500000,
		"testing": {
			"stopOnFailedTest": true,
			"stopOnFailedContractMatching": true,
			"stopOnNoTests": true,
			"testAllContracts": false,
			"traceAll": false,
			"assertionTesting": {
				"enabled": false,
				"testViewMethods": false,
				"panicCodeConfig": {
					"failOnCompilerInsertedPanic": false,
					"failOnAssertion": true,
					"failOnArithmeticUnderflow": false,
					"failOnDivideByZero": false,
					"failOnEnumTypeConversionOutOfBounds": false,
					"failOnIncorrectStorageAccess": false,
					"failOnPopEmptyArray": false,
					"failOnOutOfBoundsArrayAccess": false,
					"failOnAllocateTooMuchMemory": false,
					"failOnCallUninitializedVariable": false
				}
			},
			"propertyTesting": {
				"enabled": true,
				"testPrefixes": [
					"echidna_"
				]
			},
			"optimizationTesting": {
				"enabled": false,
				"testPrefixes": [
					"optimize_"
				]
			}
		},
		"chainConfig": {
			"codeSizeCheckDisabled": true,
			"cheatCodes": {
				"cheatCodesEnabled": true,
				"enableFFI": false
			}
		}
	},
	"compilation": {
		"platform": "crytic-compile",
		"platformConfig": {
			"target": ".",
			"solcVersion": "0.8.26",
			"exportDirectory": "",
			"args": ["--compile-force-framework", "solc", "--solc-args", "--evm-version paris --optimize --optimize-runs 99999"]
		}
	},
	"logging": {
		"level": "info",
		"logDirectory": "",
		"noColor": true
	}
}
_EOT_

# copy source into the working directory
cp $SOURCE $WORKDIR

# =========================
# Start Fuzzing
# =========================

echo "=> Medusa Fuzzing:" >> $LOGFILE
/usr/bin/time -o $TIMEFILE -f "%e" -- medusa fuzz --config medusa.json &>> $LOGFILE
