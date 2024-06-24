import os, sys
import json
import time
import subprocess
import logging
from pathlib import Path

TOOLS = ['echidna', 'foundry', 'ityfuzz', 'medusa']

# FIX accordingly (memory limit)
SPAWN_CMD = 'docker run --rm -m=8g --cpuset-cpus=%d -i -d --name %s %s'
CP_MAZE_CMD = 'docker cp %s %s:/home/maze/maze/'
CP_CMD = 'docker cp %s:/home/maze/outputs %s'
KILL_CMD = 'docker kill %s'

logging.basicConfig(format='[%(asctime)s] %(message)s', datefmt='%d/%m/%Y %I:%M:%S', level=logging.INFO)

def run_cmd(cmd_str):
    logging.info("Executing: %s" % cmd_str)
    cmd_args = cmd_str.split()
    try:
        subprocess.call(cmd_args)
    except Exception as e:
        logging.exception(e)
        exit(1)

def run_cmd_in_docker(container, cmd_str):
    logging.info("Executing (in container): %s" % cmd_str)
    cmd_prefix = "docker exec -d %s /bin/bash -c" % container
    cmd_args = cmd_prefix.split()
    cmd_args += [cmd_str]
    try:
        p = subprocess.Popen(cmd_args, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
        logging.info("command run_cmd finished")
    except Exception as e:
        logging.exception(e)
        exit(1)

def load_config(path):
    with open(path) as f:
        txt = f.read()
    conf = json.loads(txt)

    # resolve relative paths to absolute based on config file location
    config_root = Path(path).parent
    maze_list = Path(conf['MazeList'])
    if not maze_list.is_absolute(): # is relative
        conf['MazeList'] = str(config_root / maze_list) # relative repair path
    maze_dir = Path(conf['MazeDir'])
    if not maze_dir.is_absolute(): # is relative
        conf['MazeDir'] = str(config_root / maze_dir) # relative repair path

    # assert limits of config values
    assert os.path.exists(conf['MazeList']) and \
        os.path.isfile(conf['MazeList']), f"unable to find '{conf['MazeList']}'"
    assert conf['Repeats'] > 0
    assert conf['Duration'] > 0
    assert len(conf['Seeds']) > 0
    assert conf['Workers'] > 0
    assert os.path.exists(conf['MazeDir']) and \
        os.path.isdir(conf['MazeDir']), f"unable to find '{conf['MazeDir']}'"
    for tool in conf['Tools']:
        assert tool in TOOLS

    return conf

def get_targets(conf):
    targets = []

    with open(conf['MazeList']) as f:
        for line in f.readlines():
            tokens = line.strip().split(',')
            algo, width, height, seed, num, cycle, gen = tokens[0], tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6]
            for tool in conf['Tools']:
                for epoch in range(conf['Repeats']):
                    seeds = conf['Seeds']
                    rnd_seed = seeds[epoch % len(seeds)]
                    target = algo, width, height, seed, num, cycle, gen, tool, epoch, rnd_seed
                    targets.append(target)
    return targets

def fetch_works(targets, conf):
    works = []
    for i in range(conf['Workers']):
        if len(targets) <= 0:
            break
        works.append(targets.pop(0))
    return works

def spawn_containers(conf, works):
    for i in range(len(works)):
        algo, width, height, seed, num, cycle, gen, tool, epoch, rnd_seed = works[i]
        image = f"maze-{tool}"
        container = f"{algo}-{width}x{height}-{seed}-{num}-{cycle}-{gen}-{tool}-{epoch}-{rnd_seed}"
        # Spawn a container
        cmd = SPAWN_CMD % (i, container, image)
        run_cmd(cmd)

        src_dir = Path(conf['MazeDir']) / "src"
        file_path_local = src_dir / get_filename(algo, width, height, seed, num, cycle, gen, tool)
        assert file_path_local.is_file(), f"unable to find contract for {file_path_local}"

        cmd = CP_MAZE_CMD % (str(file_path_local), container)
        run_cmd(cmd)

def get_filename(algo, width, height, seed, num, cycle, gen, tool):
    basename = f"{algo}_{width}x{height}_{seed}_{num}_{cycle}_{gen}"
    if tool == "foundry":
        filename = basename + '.foundry.sol'
    else:
        filename = basename + '.sol'
    return filename

def get_container_src_path(algo, width, height, seed, num, cycle, gen, tool):
    path_basename = "/home/maze/maze/"
    return path_basename + get_filename(algo, width, height, seed, num, cycle, gen, tool)

def get_bin_path(algo, width, height, seed, num, cycle, gen):
    bin_path = f"/home/maze/maze/bin/{algo}_{width}x{height}_{seed}_{num}_{cycle}_{gen}.bin"
    return bin_path

def run_tools(conf, works):
    assert len(works) > 0, "empty worker list for 'run_tools'"
    duration = 0
    for i in range(len(works)):
        algo, width, height, seed, num, cycle, gen, tool, epoch, rnd_seed = works[i]
        container = f"{algo}-{width}x{height}-{seed}-{num}-{cycle}-{gen}-{tool}-{epoch}-{rnd_seed}"
        script = f"/home/maze/tools/run_{tool}.sh"
        src_path = get_container_src_path(algo, width, height, seed, num, cycle, gen, tool)
        duration = int(conf['Duration'])
        cmd = f"{script} {src_path} {duration} {rnd_seed}"
        run_cmd_in_docker(container, cmd)

    time.sleep(duration*60 + 60) # sleep timeout + extra 1 min.

def store_outputs(conf, out_dir, works):
    # First, collect testcases in /home/maze/outputs
    for i in range(len(works)):
        algo, width, height, seed, num, cycle, gen, tool, epoch, rnd_seed = works[i]
        container = f"{algo}-{width}x{height}-{seed}-{num}-{cycle}-{gen}-{tool}-{epoch}-{rnd_seed}"
        cmd = 'python3 /home/maze/tools/get_tcs.py /home/maze/outputs'
        run_cmd_in_docker(container, cmd)

    time.sleep(60)

    # Next, store outputs to host filesystem
    for i in range(len(works)):
        algo, width, height, seed, num, cycle, gen, tool, epoch, rnd_seed = works[i]
        container = f"{algo}-{width}x{height}-{seed}-{num}-{cycle}-{gen}-{tool}-{epoch}-{rnd_seed}"
        maze = f"{algo}-{width}x{height}-{seed}-{num}-{cycle}-{gen}"
        out_path = os.path.join(out_dir, maze, f"{tool}-{epoch}-{rnd_seed}")
        os.system('mkdir -p %s' % out_path)
        cmd = CP_CMD % (container, out_path)
        run_cmd(cmd)

    time.sleep(60)

def kill_containers(works):
    for i in range(len(works)):
        algo, width, height, seed, num, cycle, gen, tool, epoch, rnd_seed = works[i]
        container = f"{algo}-{width}x{height}-{seed}-{num}-{cycle}-{gen}-{tool}-{epoch}-{rnd_seed}"
        cmd = KILL_CMD % container
        run_cmd(cmd)

def main(conf_path, out_dir):
    os.system('mkdir -p %s' % out_dir)

    conf = load_config(conf_path)
    targets = get_targets(conf)

    while len(targets) > 0:
        works = fetch_works(targets, conf)
        spawn_containers(conf, works)
        run_tools(conf, works)
        store_outputs(conf, out_dir, works)
        kill_containers(works)

if __name__ == '__main__':
    conf_path = sys.argv[1]
    out_dir = sys.argv[2]
    main(conf_path, out_dir)