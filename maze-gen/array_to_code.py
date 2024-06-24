import sys, os, shutil, re
import random
import importlib
from textwrap import dedent
from collections import defaultdict

def get_maze(maze_file):
    """Parses a generated maze and returns it in a 2-dimensional matrix.

    The maze is passed as a .txt file containing a matrix with '0' and '1' character entries,
    representing paths and walls in the maze respectively.
    """

    f = open(maze_file + ".txt", "r+")
    txt = f.read().replace(' ', '').replace('[', '').replace(']', '')
    f.seek(0)
    f.write(txt)
    f.truncate()
    f.seek(0)
    matrix = []
    for i in range(height*2+1):
        row = []
        for j in range(width*2+2):
            c = f.read(1)
            if (c == '1' or c == '0'):
                row.append(c)
        matrix.append(row)
    f.close()
    return matrix

def get_solution(maze_file):
    """Parses a file containing solution for a given maze file.

    Takes the name of the maze file and parses its corresponding solution from a txt file.
    The solution file contains the correct sequence of steps through the maze,
    where each line corresponds to one cell in the maze to step to next.
    Returns a list of steps to take to successfully traverse the maze.
    """

    with open(maze_file + "_solution.txt", 'r') as f_sln:
        sln = f_sln.readlines()
    for i in range(len(sln)):
        sln[i] = int(sln[i].strip("\n"))
    return sln

def get_exit(sln):
    """Returns the exit cell of a maze.

    Takes a maze solution as a list of cells in a maze and returns the last cell,
    i.e. the maze's exit.
    """

    return sln[len(sln) - 1]

def get_functions(width, height, maze_exit):
    """Assigns each cell in the maze a unique integer (function name).

    All cells get assigned an integer as a name apart from the "start" and "bug" (goal) cell.
    """

    xy_to_func = dict()
    functions = list(range(width*height))
    for i in range(width*height):
        # assigns the row and column the integer: i
        xy_to_func[(i // width, i % width)] = functions[i]
    xy_to_func[(-1, 0)] = 'start'
    if maze_exit == width*height - 1:
        xy_to_func[(height, width-1)] = 'bug'
    return xy_to_func

# Label each node by depth first search
class DirGraph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, node, neighbour):
        """Adds an edge between node and neighbour to the graph.
        """

        self.graph[node].append(neighbour)


    def count_edges(self):
        """Returns the total number of edges in the graph.
        """

        count = 0
        for idx in range(width*height):
            count = count + len(self.graph[idx])
        return count

    def count_backedges(self, labels):
        """Returns the number of total back edges in the graph

        Specifically it counts the edges where the source node was discovered later than the sink node.
        """

        count = 0
        for idx in range(width*height):
            for neighbour in self.graph[idx]:
                if labels[idx] >= labels[neighbour]:
                    count = count + 1
        return count

    def remove_backedges(self, labels, n, seed):
        """
        Removes exactly "n" backedges from the graph which are selected using the random "seed".
        """

        random.seed(seed)
        while n > 0:
            idx = random.randrange(0, width*height)
            for neighbour in self.graph[idx]:
                if labels[idx] >= labels[neighbour]:
                    self.graph[idx].remove(neighbour)
                    n = n -1

    def df_search_helper(self, node, visited, labels):
        visited.add(node)
        labels[node] = len(visited)
        for neighbour in self.graph[node]:
            if neighbour not in visited:
                self.df_search_helper(neighbour, visited, labels)
        return labels

    def df_search(self, node):
        """Returns a dictionary of nodes and their respective labels.

        A node's label corresponds to when it was discovered during the dfs traversal.
        """

        visited = set()
        labels = dict()
        return self.df_search_helper(node, visited, labels)

def generate_graph(width, height, maze_exit, maze_functions, matrix):
    """
    Returns a directed graph with nodes corresponding to cells in the maze represented by "matrix",
    indexed according to maze_functions.

    Only cells in the matrix (zeroes) are represented, and if cells are adjacent,
    there exists an edge between them.
    The graph nodes are indexed based on the "maze_functions" dictionary.
    """

    graph = DirGraph()
    functions = list(range(width*height))
    for idx in range(width*height):
        x, y = functions[idx] // width, functions[idx] % width
        node = maze_functions[(x, y)]
        if node == maze_exit and node != width*height - 1:
            graph.add_edge(node, 'bug')
        i, j = 2*x + 1, 2*y + 1
        if matrix[i-1][j] == '0':
            graph.add_edge(node, maze_functions[(x-1, y)])
        if matrix[i][j-1] == '0':
            graph.add_edge(node, maze_functions[(x, y-1)])
        if matrix[i+1][j] == '0':
            graph.add_edge(node, maze_functions[(x+1, y)])
        if matrix[i][j+1] == '0':
            graph.add_edge(node, maze_functions[(x, y+1)])
    return graph

def remove_cycle(graph, cycle, seed):
    """Removes cycles randomly using "seed" such that the percentage "cycle"
    of the existing cycles remains in the graph.
    """

    graph_labels = graph.df_search(0)
    numb_backedges = graph.count_backedges(graph_labels)
    proportion_rm = float(1 - (cycle/100))
    numb_to_remove = int(numb_backedges*proportion_rm)
    graph.remove_backedges(graph_labels, numb_to_remove, seed)

def render_program_solidity(sol_file, foundry_file, transaction_file, maze, width, height, generator, sln, equality, smt_file):
    """Writes a solidity program to "sol_file" containing functions according to the passed "maze"
    where the conditionals in the functions are chosen based on the passed "generator"

    """

    generator = generator.Generator(width*height, maze.graph, sln, equality, smt_file)
    logic_sol = generator.get_logic_sol()
    guard = generator.get_guard()
    step_transaction_values = generator.get_solution_values()

    with open(transaction_file, 'w') as fp:
        fp.write("\n".join(step_transaction_values))

    f = open(sol_file, 'w')

    f.writelines(["pragma solidity 0.8.26;\n", "contract Maze { \n"])

    f.write("\tbool public bug = false;\n")
    f.write("\tbool private stop = false;\n")

    # states whether the function with the corresponding integer may be entered
    # -2 for start and -1 for bug
    f.write("\tint64 next_cell = 0;\n")

    f.write("\tfunction func_start(int8[] memory inp) internal {}\n")
    f.write("\tfunction func_bug(int8[] memory inp) internal {\n\t\tbug = true;\n\t\treturn;\n\t}\n")

    function_begin_format = """\tfunction func_{}(int8[] memory inp) internal {{\n\tunchecked{{\n\t\trequire(inp.length >= {});\n{}"""

    function_format = """\t\t{} ({}) {{
\t\t\tnext_cell = {};
\t\t}}
"""

    else_stop = "\t\telse {\n\t\t\tstop = true;\n\t\t}"

    function_enter_condition_format = """\t\tif (next_cell == {}) {{\n\t\t\tfunc_{}(inp);\n\t\t\treturn;\n\t\t}}\n"""
    function_enter_conditions = []

    # each index represents a tile in the maze
    for idx in range(width*height):
        args_to_fuzz = 1
        if logic_sol["func_inputs"]:
            if logic_sol["func_inputs"][idx]:
                print(logic_sol["func_inputs"][idx])
                for func_inp in logic_sol["func_inputs"][idx]:
                    args_to_fuzz = max(args_to_fuzz, int(re.findall(r'\d+', func_inp)[-1]) + 1)
        buggies = logic_sol["buggy_constraints"][idx]
        func_begin = function_begin_format.format(idx, args_to_fuzz, buggies)
        function_enter_conditions.append(function_enter_condition_format.format(idx, idx))
        f.write(func_begin)
        valid_edges = len(maze.graph[idx])
        if valid_edges != 0:
            edge_counter = 0
            for neighbour in maze.graph[idx]:
                # replace 1 and 0 as if conditions as they are not valid in solidity
                guard_cond = guard[idx][edge_counter]
                if guard_cond == 1:
                    guard_cond = "true"
                elif guard_cond == 0:
                    guard_cond = "false"

                nb_int = neighbour if type(neighbour) == int else -1 if neighbour == "bug" else -2

                if edge_counter == 0:
                    f.write(function_format.format(
                        'if', guard_cond, nb_int))
                else:
                    f.write(function_format.format(
                        'else if', guard_cond, nb_int))
                edge_counter += 1
            f.write(else_stop) # add an else at the end of all possible paths
        f.write("\n\t}\n\t}\n")

    # outer function responsible for rerouting the caller to the currently visited cell
    f.writelines(["\tfunction step(int8[] calldata inp) external {\n\n"])

    # only take a step if we can move (!stop) and no bug is found (!bug).
    f.write('\t\trequire(!stop && !bug, "unable to take any further steps");\n\n')

    f.write("""\t\tif (next_cell == -2) {\n\t\t\tfunc_start(inp);\n\t\t\treturn;\n\t\t}\n""")

    f.write("\t\tif (next_cell == -1) {\n\t\t\tfunc_bug(inp);\n\t\t\treturn;\n\t\t}\n")

    for enter_cond in function_enter_conditions:
        f.write(enter_cond)
    # close step function brace
    f.write("\t}\n")
    f.close()
    shutil.copyfile(sol_file, foundry_file)
    with open(sol_file, "a") as f:
        f.writelines(["\tfunction echidna_noBug() external returns (bool) {", "return !bug;","}\n", "}\n"])
    with open(foundry_file, 'a') as f:
        f.write(dedent(
        """\
        }
        import "forge-std/Test.sol";
        contract TestMaze is Test {
            Maze m;
            function setUp() external {
                m = new Maze();
            }
            function invariant_no_bug() external {
                if (m.bug()) { fail(); }
            }
        }"""))


def main(maze_file, width, height, cycle, seed, generator, equality, smt_file, CVE_name):
    matrix = get_maze(maze_file)
    sln = get_solution(maze_file)
    maze_exit = get_exit(sln)
    maze_funcs = get_functions(width, height, maze_exit)
    graph = generate_graph(width, height, maze_exit, maze_funcs, matrix)
    remove_cycle(graph, cycle, seed)
    transaction_file = maze_file + "_" + str(cycle) + "percent_" + CVE_name + "_transactions.txt"
    sol_file = maze_file + "_" + str(cycle) + "percent_" + CVE_name + ".sol"
    foundry_file =  maze_file + "_" + str(cycle) + "percent_" + CVE_name + ".foundry.sol"
    render_program_solidity(sol_file, foundry_file, transaction_file, graph, width, height, generator, sln, equality, smt_file)

if __name__ == '__main__':
    maze_file = sys.argv[1]
    width, height = int(sys.argv[2]), int(sys.argv[3])
    cycle = int(sys.argv[4])
    seed = int(sys.argv[5])
    generator_file = sys.argv[6]
    equality = 0
    smt_file = ""
    CVE_name = generator_file
    if "CVE" in generator_file:
        smt_file = sys.argv[7]
        CVE_name = os.path.basename(smt_file)
        CVE_name = os.path.splitext(CVE_name)[0] + "_gen"
    if "equality" in generator_file:
        equality = int(generator_file.replace("equality", "").replace("_gen", ""))
        assert 0 <= equality and equality <= 100, f"unexpected percentage value {equality}"
        generator_file = "equality_gen"

    generator = importlib.import_module(generator_file)

    main(maze_file, width, height, cycle, seed, generator, equality, smt_file, CVE_name)
