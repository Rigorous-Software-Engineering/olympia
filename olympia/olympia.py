from enum import StrEnum
from pathlib import Path
from subprocess import Popen, PIPE
from random import Random
from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime
import os
from dataclasses import dataclass

from utils.reachability_test import run_test as run_reachability_test
from utils.custom_logging import logger


# ====================================================
# Hardcoded constants
# ====================================================

OLYMPIA_DIR = Path(os.path.dirname(__file__))
CVE_FOLDER = OLYMPIA_DIR / "../CVEs"
GENERATION_SH = OLYMPIA_DIR / "../scripts/generate.sh"

EQUALITY_METHOD_PERCENTAGE = [25, 50, 75, 100]
CYCLE_PERCENTAGE = [0, 25, 50, 75, 100]

# ====================================================
# Generation Settings
# ====================================================

class MazeGenAlgorithmKind(StrEnum):
    BACKTRACKING = "Backtracking"
    KRUSKAL      = "Kruskal"
    PRIMS        = "Prims"
    WILSONS      = "Wilsons"
    SIDEWINDER   = "Sidewinder"

class MazeGenMethodKind(StrEnum):
    CVE      = "CVE"
    DEFAULT  = "default"
    EQUALITY = "equality"

@dataclass
class MazeGenerationMethod():
    kind                : MazeGenMethodKind
    smt_file            : Path | None = None
    equality_percentage : int  | None = None

    @property
    def gen_filename(self) -> str:
        match self.kind:
            case MazeGenMethodKind.CVE | MazeGenMethodKind.DEFAULT:
                return f"{self.kind.value}_gen"
            case MazeGenMethodKind.EQUALITY:
                assert self.equality_percentage, "equality method without equality percentage"
                return f"equality{self.equality_percentage}_gen"

    @property
    def entry_name(self) -> str:
        match self.kind:
            case MazeGenMethodKind.CVE:
                assert self.smt_file, "CVE method without smt file"
                smt_base = self.smt_file.stem
                return f"{smt_base}_gen"
            case MazeGenMethodKind.DEFAULT:
                return f"{self.kind.DEFAULT.value}_gen"
            case MazeGenMethodKind.EQUALITY:
                assert self.equality_percentage, "equality method without equality percentage"
                return f"equality{self.equality_percentage}_gen"

@dataclass
class GenerationSetting():
    algorithm  : MazeGenAlgorithmKind
    dimension  : int
    maze_seed  : int
    cycles     : int
    method     : MazeGenerationMethod
    output_dir : Path

    @property
    def program_entry(self) -> str:
        return ",".join(
            [ f"{self.algorithm}"
            , f"{self.dimension}"
            , f"{self.dimension}"
            , f"{self.maze_seed}"
            , "1" # number hardcoded to 1
            , f"{self.cycles}percent"
            , f"{self.method.entry_name}"
            ])

    @property 
    def base_name(self) -> str:
        return self.program_entry.replace(",", "_")

@dataclass
class GenerationResult():
    setting    : GenerationSetting
    command    : str
    stdout     : bytes
    stderr     : bytes
    returncode : int


# ====================================================
# Generation Logic
# ====================================================

def exec_generation_sh(setting: GenerationSetting) -> GenerationResult:
    """
    Executes the generation.sh inside of tht script folder with the generated
    and provided settings. It returns a result object containing the status of
    the execution together with the settings and the called command
    """
    # set the command and flags
    command = \
        [ str(Path(GENERATION_SH).absolute())
        , "-a", f"{setting.algorithm}"
        , "-w", f"{setting.dimension}"
        , "-h", f"{setting.dimension}"
        , "-o", f"{setting.output_dir}"
        , "-r", f"{setting.maze_seed}"
        , "-n", "1" # number hardcoded to 1
        , "-c", f"{setting.cycles}"
        , "-g", f"{setting.method.gen_filename}"
        , "-e", "default"
        ]
    if setting.method.kind == MazeGenMethodKind.CVE:
        assert setting.method.smt_file, "CVE method has no smt file"
        command.append(f"-s {setting.method.smt_file}")

    # subprocess.run(single_line_command, shell=True, check=True)
    process = Popen(command, shell=False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    command_str = " ".join(command)
    returncode = process.returncode

    return GenerationResult(setting, command_str, stdout, stderr, returncode)

def pick_random_smt_from_path(smt_dir: Path, rng: Random) -> Path:
    """
    Collects all SMT files inside of the provided directory and choses a
    random one using the provided random. This function fails if the passed
    directory is empty or cannot be found.
    """ 
    assert smt_dir and smt_dir.is_dir, f"unable to locate SMT directory {smt_dir}"
    smt_files = list(smt_dir.glob("*.smt2"))
    assert len(smt_files) > 0, f"no SMT files in folder {smt_dir}"
    return rng.choice(smt_files)

def random_generation_settings \
    ( seed: int
    , dimension: int
    , output_dir: Path
    , algorithms: list[MazeGenAlgorithmKind]
    , equalities: list[int]
    , cycles: list[int]
    , methods: list[MazeGenMethodKind]
    ) -> GenerationSetting:
    """
    Generates a generation setting object using the provided seed, dimension and output_dir.
    The settings are picked at random using a new Random object seeded with the provided seed.
    """
    rng = Random(seed) # get a local random

    algorithm = rng.choice(algorithms)
    maze_seed = rng.randint(1000000, 9999999)
    cycle = rng.choice(cycles)
    method_kind = rng.choice(methods)

    match method_kind:
        case MazeGenMethodKind.CVE:
            smt_file = pick_random_smt_from_path(CVE_FOLDER, rng)
            method = MazeGenerationMethod(method_kind, smt_file=smt_file)
        case MazeGenMethodKind.EQUALITY:
            equality_percentage = rng.choice(equalities)
            method = MazeGenerationMethod(method_kind, equality_percentage=equality_percentage)
        case _:
            method = MazeGenerationMethod(method_kind)

    return GenerationSetting(algorithm, dimension, maze_seed, cycle, method, output_dir)


def check_generation_error(result: GenerationResult) -> bool:
    """
    This function checks if the generation result contains an error.
    No error is detected it returns false and returns. Otherwise, it
    generates two debug files containing the STDOUT and STDERR of the
    generation call inside of the output directory.
    """
    if result.returncode == 0:
        return False # success

    logger.error(f"{result.command}")
    logger.error(f"return code {result.returncode}")
    logger.error(f"Maze generation exited with an error!")

    debug_stdout_file = result.setting.output_dir / f"{result.setting.base_name}.stdout.txt"
    debug_stderr_file = result.setting.output_dir / f"{result.setting.base_name}.stderr.txt"

    with open(debug_stdout_file, "wb") as fh:
        fh.write(result.stdout)

    with open(debug_stderr_file, "wb") as fh:
        fh.write(result.stderr)

    return True # error


def check_reachability_error(result: GenerationResult) -> bool:
    """
    This function checks if

        * the generated contract is correct and
        * the bug inside of the contract is reachable.

    This is done by compiling the solidity contract and executing
    each step to reach the bug. If the compilation succeeded and the
    bug is reachable this function returns False, otherwise True.
    """
    alg, w, h, r, n, cyc, m = result.setting.program_entry.split(",")

    solidity_src = result.setting.output_dir / "src"
    solidity_file = f"{alg}_{w}x{h}_{r}_{n}_{cyc}_{m}.sol"
    solidity_path = solidity_src / solidity_file

    solution_src = result.setting.output_dir / "sol_tx"
    solution_file = f"{alg}_{w}x{h}_{r}_{n}_{cyc}_{m}_transactions.txt"
    solution_path = solution_src / solution_file

    assert solidity_path.is_file(), f"unable to locate file {solidity_path}"

    if not run_reachability_test(solidity_path, solution_path):
        logger.error(f"Unable to compile solidity file {solidity_path}")
        return True # error

    return False # success

def generate \
    ( seed: int
    , dimension: int
    , output_dir: Path
    , algorithms: list[MazeGenAlgorithmKind]
    , equalities: list[int]
    , cycles: list[int]
    , methods: list[MazeGenMethodKind]
    , disable_check: bool
    ) -> bool:
    """
    This function generates a single entry of a benchmark. The maze used for this
    instance will have the provided dimensions and other settings are picked at random.
    Additionally, if the `disable_check` is False, the generated contract is tested for
    compilation errors and if the bug is reachable.
    """
    assert dimension >= 5, "unable to deal with dimension of <5"
    assert CVE_FOLDER and CVE_FOLDER.is_dir, f"unable to find CVE folder {CVE_FOLDER}"
    assert GENERATION_SH and GENERATION_SH.is_file, f"unable to find generation script {GENERATION_SH}"

    if not output_dir.is_dir():
        os.mkdir(output_dir)
    output_dir = output_dir.absolute()

    # debug and reproducibility
    reproducible_sh = output_dir / "reproducible_generation.sh"
    programs_list = output_dir / "programs.list"
    success = True # default is true

    # generate setting and files
    gen_setting = random_generation_settings(seed, dimension, output_dir,
        algorithms, equalities, cycles, methods)
    generation_result = exec_generation_sh(gen_setting)

    # check for problems and reachability
    if check_generation_error(generation_result):
        success = False
    if success and not disable_check:
        if check_reachability_error(generation_result):
            success = False

    # finalize by writing the generation info
    with open(reproducible_sh, "a") as fh:
        fh.write(f"# generation command: ./olympia --output {output_dir} --dimension {dimension} --seed {seed}\n")
        fh.write(f"{generation_result.command}\n")
    with open(programs_list, "a") as fh:
        fh.write(gen_setting.program_entry)
        fh.write("\n")

    return success


# ====================================================
# Implementation of Command line Client
# ====================================================

def argparse_percent(x) -> int:
    x = int(x)
    if x < 0 or 100 < x:
        raise ArgumentTypeError("percent must be between [0, 100]")
    return x

def dimension_value(x) -> int:
    x = int(x)
    if x < 5:
        raise ArgumentTypeError("dimensions must be greater than 5")
    return x

def get_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="Olympia",
        description="Benchmarking tool that generates Solidity \
        programs based on mazes to compare \
        fuzzers for Solidity-based smart contracts.")

    parser.add_argument("-o", "--output"
        , metavar="OUTPUT_DIR"
        , type=Path
        , help="path to output directory"
        , required=True
        )
    parser.add_argument("-d", "--dimension"
        , metavar="DIMENSION"
        , type=dimension_value
        , help="maze dimensions (must be >=5)"
        , required=True
        )
    parser.add_argument("-s", "--seed"
        , metavar="SEED"
        , type=int
        , help="an integer seed value for random setting selection"
        )
    parser.add_argument("-a", "--algorithm"
        , help="list of maze algorithms"
        , nargs="+"
        , type=MazeGenAlgorithmKind
        , choices=list(MazeGenAlgorithmKind)
        , default=list(MazeGenAlgorithmKind)
        )
    parser.add_argument("-e", "--equality"
        , help="list of equality percentages"
        , nargs="+"
        , type=argparse_percent
        , default=EQUALITY_METHOD_PERCENTAGE
        )
    parser.add_argument("-c", "--cycle"
        , help="list of cycle percentages"
        , nargs="+"
        , type=argparse_percent
        , default=CYCLE_PERCENTAGE
        )
    parser.add_argument("-m", "--method"
        , help="list of generation methods"
        , nargs="+"
        , type=MazeGenMethodKind
        , choices=list(MazeGenMethodKind)
        , default=list(MazeGenMethodKind)
        )
    parser.add_argument("--disable-reachability-check"
        , help="disables the required solidity compilation and bug reachability check"
        , action='store_true'
        , default=False
        )
    return parser

if __name__ == "__main__":
    parser = get_arg_parser()
    args = parser.parse_args()
    if args.seed:
        seed = args.seed
    else:
        seed = int(datetime.now().timestamp() * 1000000) % 1000000
        logger.debug(f"No seed provided, using seed: {seed}")
    dimension = args.dimension
    output_dir = args.output
    algorithms = args.algorithm
    equalities = args.equality
    cycles = args.cycle
    methods = args.method
    disable_check = args.disable_reachability_check

    success = generate(seed, dimension, output_dir, algorithms,
        equalities, cycles, methods, disable_check)
    
    exit(0 if success else 1)