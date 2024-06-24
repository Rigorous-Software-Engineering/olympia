import random

class Generator:
    def __init__(self, size, edges, sln, equality, smt_file):
        self.size = size
        self.edges = edges
        self.sln = sln
        self.equality = float(equality) / 100
        self.cached_guard_solution : dict[int, dict[int, str]] = dict()

    # Since the fuzzed input is passed via arguments, no additional code is needed.
    def get_logic_sol(self):
        # In default generation, no additional arguments or constraint declarations are needed.
        logic_sol = {"buggy_constraints":[""]*self.size, "func_inputs":[""]*self.size}
        return logic_sol

    def get_guard(self):
        guard = list()
        default = \
            [ ["false"]
            , ["true"]
            , ["inp[0] < 0", "inp[0] >= 0"]
            , ["inp[0] < -43", "inp[0] < 42", "inp[0] >= 42"]
            , ["inp[0] < -64", "inp[0] < 0", "inp[0] < 64", "inp[0] >= 64"]
            ]
        solution_default_values = \
            [ ["[ 0 ]"]
            , ["[ 0 ]"]
            , ["[ -1 ]", "[ 0 ]"]
            , ["[ -44 ]", "[ 41 ]", "[ 42 ]"]
            , ["[ -65 ]", "[ -1 ]", "[ 63 ]", "[ 64 ]"]
            ]
        equality = \
            [ ["false"]
            , ["inp[0] == 1"]
            , ["inp[0] == -64", "inp[0] == 64"]
            , ["inp[0] == -85", "inp[0] == 1", "inp[0] == 87"]
            , ["inp[0] == -96", "inp[0] == -32", "inp[0] == 32", "inp[0] == 96"]
            ]
        solution_equality_values = \
            [ ["[ 0 ]"]
            , ["[ 1 ]"]
            , ["[ -64 ]", "[ 64 ]"]
            , ["[ -85 ]", "[ 1 ]", "[ 87 ]"]
            , ["[ -96 ]", "[ -32 ]", "[ 32 ]", "[ 96 ]"]
            ]
        proportion_eq, total_edges = self.equality, 0
        for idx in range(self.size):
            total_edges = total_edges + len(self.edges[idx])
        eq_edges = int(total_edges*proportion_eq)
        eq_nodes = set()
        random.seed(0)
        while eq_edges > 0:
            idx = random.randrange(0, self.size)
            if not idx in eq_nodes:
                eq_nodes.add(idx)
                eq_edges = eq_edges - len(self.edges[idx])
        for idx in range(self.size):
            self.cached_guard_solution[idx] = dict() # start a new solution
            numb_edges = len(self.edges[idx])
            if idx in eq_nodes:
                guard.append(equality[numb_edges])
                for i in range(numb_edges):
                    self.cached_guard_solution[idx][self.edges[idx][i]] = solution_equality_values[numb_edges][i]
            else:
                guard.append(default[numb_edges])
                for i in range(numb_edges):
                    self.cached_guard_solution[idx][self.edges[idx][i]] = solution_default_values[numb_edges][i]
        return guard

    def get_solution_values(self) -> list[str]:
        values = []
        current_position = self.sln[0]
        for next_cell in self.sln[1:] + ['bug']:
            values.append(self.cached_guard_solution[current_position][next_cell])
            current_position = next_cell
        return values + ["[ ]"] # needs an extra step to actually call the bug function