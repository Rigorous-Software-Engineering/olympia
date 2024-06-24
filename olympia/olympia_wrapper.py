from pathlib import Path
from random import Random
from argparse import ArgumentParser
from datetime import datetime

import olympia
from utils.custom_logging import logger

# ====================================================
# Generation Wrapper Logic
# ====================================================

def generate \
    ( seed: int
    , dimensions: list[int]
    , instances: int
    , output_dir: Path
    , algorithms: list[olympia.MazeGenAlgorithmKind]
    , equalities: list[int]
    , cycles: list[int]
    , methods: list[olympia.MazeGenMethodKind]
    , disable_compile_check: bool
    ) -> bool:
    """
    Wrapper for the olympia benchmark instance generation. This wrapper takes a list of dimensions
    and how many instances each if these dimensions should have. Then it calls olympia this many times
    for each dimension to generate the instances. The whole generation is deterministic and based on the
    provided seed.
    """
    rng = Random(seed)
    dimensions_size = len(dimensions)
    dimensions_count = 1

    for dimensions_count, dimension in enumerate(dimensions, start=1):
        for instance in range(instances):
            instance_seed = rng.randint(100000, 999999)
            algorithms_str = " ".join(algorithms)
            equalities_str = " ".join(map(str, equalities))
            cycles_str = " ".join(map(str, cycles))
            methods_str = " ".join(map(str, methods))
            logger.debug(f"./olympia.py -s {instance_seed} -d {dimension} -o {output_dir} -a {algorithms_str} -c {cycles_str} -m {methods_str} -e {equalities_str}")
            success = olympia.generate(instance_seed, dimension, output_dir,
                algorithms, equalities, cycles, methods, disable_compile_check)
            logger.info(f"Dimensions: {dimensions_count}/{dimensions_size}  Instance: {instance+1}/{instances}")
            if not success:
                logger.warning("Wrapper stopped due to error(s)...")
                return False # exit failure
    return True # exit success

# ====================================================
# Implementation of Command line Client
# ====================================================

def get_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="Olympia Wrapper",
        description="This wrapper uses Olympia to generate a fixed \
                     amount of random test instances for a list of dimensions")

    parser.add_argument("-o", "--output"
        , metavar="OUTPUT_DIR"
        , type=Path
        , help="path to output directory"
        , required=True
        )
    parser.add_argument("-d", "--dimensions"
        , metavar="DIMENSIONS"
        , type=olympia.dimension_value
        , help="list of maze dimensions (must be >=5)"
        , required=True
        , nargs="+"
        )
    parser.add_argument("-s", "--seed"
        , metavar="SEED"
        , type=int
        , help="an integer seed used to seed the underlying Olympia generation"
        )
    parser.add_argument("-i", "--instances"
        , metavar="INSTANCES"
        , type=int
        , help="an integer for the amount of instances that should be generated"
        , required=True
        )
    parser.add_argument("-a", "--algorithm"
        , help="list of maze algorithms"
        , nargs="+"
        , type=olympia.MazeGenAlgorithmKind
        , choices=list(olympia.MazeGenAlgorithmKind)
        , default=list(olympia.MazeGenAlgorithmKind)
        )
    parser.add_argument("-e", "--equality"
        , help="list of equality percentages"
        , nargs="+"
        , type=olympia.argparse_percent
        , default=olympia.EQUALITY_METHOD_PERCENTAGE
        )
    parser.add_argument("-c", "--cycle"
        , help="list of cycle percentages"
        , nargs="+"
        , type=olympia.argparse_percent
        , default=olympia.CYCLE_PERCENTAGE
        )
    parser.add_argument("-m", "--method"
        , help="list of generation methods"
        , nargs="+"
        , type=olympia.MazeGenMethodKind
        , choices=list(olympia.MazeGenMethodKind)
        , default=list(olympia.MazeGenMethodKind)
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
    dimensions = args.dimensions
    instances = args.instances
    output = args.output
    algorithms = args.algorithm
    equalities = args.equality
    cycles = args.cycle
    methods = args.method
    disable_check = args.disable_reachability_check

    success = generate(seed, dimensions, instances, output,
        algorithms, equalities, cycles, methods, disable_check)

    exit(0 if success else 1)