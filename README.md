# Olympia

Olympia is a bug synthesizer based on [Fuzzle](https://github.com/SoftSec-KAIST/Fuzzle), able to generate buggy
`solidity` programs for evaluating solidity fuzzers.
Olympia uses randomly created mazes and path constraints from existing, known
CVEs to generate more realistic programs.

## Installation

Please follow the steps of the provided [installation instructions](INSTALL.md) inside the `INSTALL.md`.

## Usage

Interacting with olympia is done via two top level scripts:
 * `olympia/olympia.py`
 * `olympia/olympia_wrapper.py`

For a quick usage information on available options run:

```bash
$ python olympia/olympia.py -h
```

or

```bash
$ python olympia/olympia_wrapper.py -h
```

### Benchmark Generation

#### Single Benchmark Instance

The basic benchmark generation is controlled with the `olympia/olympia.py` script.
Olympia requires a dimension size and an output folder. For example, the following command generates a `benchmark` folder for a single benchmark instance inspired by a 10x10 maze.

```bash
$ python olympia/olympia.py -d 10 -o benchmark
```
The generated folder structure will look as follows:

```
./benchmark/
      |
      +--- bin/
      |
      +--- png/
      |
      +--- sln/
      |
      +--- sol_tx/
      |
      +--- src/
      |
      +--- txt/
      |
      +--- programs.list
      |
      +--- reproducible_generation.sh
```

(Since olympia is based on Fuzzle, the `bin` folder is generated for compatibility reasons and can be ignored.)

The `png` folder contains images of the mazes used for the benchmark instances.

The `sln` folder contains `*.txt` files with the solution on how to reach the entry of the maze. The solution is provided by a list of cells inside of the maze.

The `sol_tx` folder contains `*.txt` files with a solution on how to reach the buggy state of the generated contract. The files contain a list of arrays which are used as arguments to the generated `step()` functions.

The `src` folder contains the solidity benchmark files. For each instance, olympia will generate a simple solidity contract inside a `*.sol` file and a foundry compatible `*.foundry.sol` file.

The `txt` folder contains a textual representation of the maze in form of 0s (walls) and 1s (walkable tiles).

The `programs.list` file contains information on the generated benchmark instances. Each line contains information on maze properties used for translation.

The `reproducible_generation.sh` can be seen as a history of the benchmark folder and contains all the commands to reproduce the current folder using the underlying `generation.sh` script.


#### Multiple Benchmark Instances

To conveniently generate a benchmark with multiple instances olympia provides the `olympia/olympia_wrapper.py`.
As the name suggests, it wraps the original olympia generation and provides additional functionality.
Additionally to the output folder, olympia's wrapper takes a list of dimensions and a number of the amount of desired instances per provided dimensions. For example, the following command generates 2 instances for maze dimensions 5x5 and 10x10 each and stores them in the `benchmark` folder.

```bash
$ python olympia/olympia_wrapper.py -d 5 10 -i 2 -o benchmark
```

#### Benchmark Settings

One of the main limitations is the dimension (`-d`) of the used mazes.
Olympia limits the provided dimension to be at least 5.
While there is no enforced upper bound, everything above 30 will likely exceed the EVM allowed byte-size.

The following list of options provides an overview of the possible settings for olympia benchmark generation.
Each flag can be provided to olympia and its wrapper.
The underlying generation process will then pick one at random for each generated instance.

  * `-a` list of the maze generation algorithm
    - `Backtracking`
    - `Kruskal`
    - `Prims`
    - `Wilsons`
    - `Sidewinder`
  * `-m` list of generation methods responsible to fill the different branch condition holes.
    - `default`  (path conditions will only consist of simple "<", "<=", ">" and ">=" relations)
    - `equality` (based on equality percentage provided with `-e`, path conditions may contain the "==" relations)
    - `CVE` (uses the provided CVE files to generate complex path conditions)
  * `-e` list of percentages to pick the equality relation for path conditions
    - [0 - 100]
  * `-c` list of percentages to introduce cycles, i.e. the possibility to walk back from one cell to the previous cell
    - [0 - 100]

When the `CVE` generation method is selected, olympia will use the content of the `CVEs` folder to select a random SMT file.
To disable one of the provided files, move it into the `CVEs/disable` folder.

To reliably reproduce benchmark generations, an integer seed can be provided by using the `-s` flag.

Finally, for every generated solidity contract a compilation and bug-reachability check is performed.
However, these tests do NOT include gas or byte-size checks of the compiled binaries.
Since this task is very time consuming it can be turned off using the `--disable-reachability-check` flag.

#### Example Generation

The following example command generates 10 solidity benchmark instances. From the 10 instances, 5 of dimension 10x10 and 5 of dimension 20x20. Moreover, it restricts the generation method to be of the type `default` and `equality` (with a 25% or 50% chance of picking the "==" relation if `equality` is selected).
The cycle property is turned off as indicated by the provided value of 0%.
Finally, the used maze generation algorithm will be either `Kruskal` or `Prims`.

```bash
$ python olympia/olympia_wrapper.py \
    -o benchmark \
    -d 10 20 \
    -i 5 \
    -m default equality \
    -e 25 50 \
    -c 0 \
    -a Kruskal Prims
```

### Running a Fuzzing Experiment

To run fuzzers on the generated benchmark in a separate docker container:

```
$ python3 ./scripts/run_tools.py <CONFIG_FILE> <FUZZ_OUT>
```

An example of the configuration file (`<CONFIG_FILE>`) is provided below.

```json
{ "MazeList" : "benchmarks/programs.list"
, "Repeats"  : 2
, "Workers"  : 10
, "Seeds"    : [4321, 1234]
, "Duration" : 30
, "MazeDir"  : "benchmarks"
, "Tools"    : ["echidna", "foundry", "ityfuzz", "medusa"]
}
```

- `MazeList`: path to the list of programs in the benchmark
- `Repeats` : number of repeats for each fuzzer
- `Workers` : number of available CPUs cores for the fuzzing run (each tool will get a dedicated core per campaign)
- `Seeds`   : list of seeds provided to the tools for a specific repetition
- `Duration`: length of fuzzing campaign in minutes
- `MazeDir` : path to a directory that contains benchmark programs for each programming language
- `Tools`   : list of one or more of the available fuzzers (`echidna`, `foundry`, `ityfuzz`, `medusa`)

Note that all paths (`MazeList` and `MazeDir`) should be either absolute paths or relative paths from the configuration file.

The provided `example.conf` is an example configuration file.

After the experiment is finished, the output directory (`<FUZZ_OUT>`) will
contain generated reports on whether the bug was found and, if so, how long it took to find.

### Storing and Summarizing Results

Once the fuzzing campaign is finished, the coverage and bug finding results can be summarized in csv format using the script as follows:

```bash
$ python scripts/save_results.py <FUZZ_OUT> <OUT_DIR>
```

- `<FUZZ_OUT>`: directory that contains fuzzing outputs
- `<OUT_DIR>`: path to save the output file to

The script summarizes the fuzzing results found in the `<FUZZ_OUT>` directory and stores them into a csv file inside of the `<OUT_DIR>`.

## Basic Usage Example

This section explains how to generate a small benchmark and run experiments.
To follow the examples, make sure to complete the [installation](INSTALL.md) first.

To run a simple benchmark on a single generated program, start by generating the program from the `olympia` director.

```bash
$ python olympia/olympia.py -d 5 -o benchmark
```

This will construct a solidity program from a 5 by 5 maze using random generation methods
(see the previous [settings](#benchmark-settings) section for more information).

Additionally, edit the provided `example.conf` file to point to the generated `benchmark`, the
`programs.list` file inside of the `benchmark` folder, and define the fuzzers to be benchmarked:

```json
{ "MazeList" : "benchmark/programs.list"
, "Repeats"  : 2
, "Workers"  : 2
, "Seeds"    : [4321, 1234]
, "Duration" : 60
, "MazeDir"  : "benchmark"
, "Tools"    : ["echidna"]
}
```
The above setting runs the `echidna` fuzzer with 2 repetitions, using the seeds `4312` and `1234`, and a 60 minute timeout on the benchmark files defined in `benchmark/programs.list`.

The benchmark can then be started by running the following command from the `scripts` directory:

```bash
$ python3 ./scripts/run_tools.py example.conf outputs
```

This will store the benchmark outputs of all fuzzing campaigns to `outputs`.
A comprehensive report of the campaign's results will be stored in a `report.txt` file of each campaign's directory while another file, with the ending `.tc` will contain the fuzzer's output for the campaign (this can be used for debugging).

Finally, to collect and generate a single data file run following command

```bash
$ python3 ./scripts/save_results.py outputs ./
```

This will collect the benchmark results from `output` and generate
a `.csv` file inside of `./` (i.e. the current directory) for further processing.
