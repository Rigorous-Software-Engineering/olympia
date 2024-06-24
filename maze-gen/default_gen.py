class Generator:
    def __init__(self, size, edges, sln, equality, smt_file):
        self.size = size
        self.edges = edges
        self.sln = sln
        self.equality = equality
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
        solution_values = \
            [ ["[ 0 ]"]
            , ["[ 0 ]"]
            , ["[ -1 ]", "[ 0 ]"]
            , ["[ -44 ]", "[ 41 ]", "[ 42 ]"]
            , ["[ -65 ]", "[ -1 ]", "[ 63 ]", "[ 64 ]"]
            ]
        for idx in range(self.size):
            self.cached_guard_solution[idx] = dict() # start a new solution
            numb_edges = len(self.edges[idx])
            assert numb_edges >= 0 and numb_edges < 5, f"unexpected number of edges: {numb_edges}"
            guard.append(default[numb_edges])
            for i in range(numb_edges):
                self.cached_guard_solution[idx][self.edges[idx][i]] = solution_values[numb_edges][i]
        return guard

    def get_solution_values(self) -> list[str]:
        values = []
        current_position = self.sln[0]
        for next_cell in self.sln[1:] + ['bug']:
            values.append(self.cached_guard_solution[current_position][next_cell])
            current_position = next_cell
        return values + ["[ ]"] # needs an extra step to actually call the bug function