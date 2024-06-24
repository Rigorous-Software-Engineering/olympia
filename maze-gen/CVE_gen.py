import smt2_parser as smt2_parser

class Generator:
    def __init__(self, size, edges, sln, equality, smt_file):
        self.size = size
        self.edges = edges
        self.sln = sln
        self.constraints, self.vars_all, self.assignments = smt2_parser.parse(smt_file)
        self.groups, self.vars = smt2_parser.independent_formulas(self.constraints, self.vars_all)
        self.insert = list()
        self.cached_guard_solution : dict[int, dict[int, str]] = dict()
        for idx in range(self.size):
            self.insert.append(0)
        while sum(self.insert) < len(self.groups):
            for func in self.sln:
                self.insert[func] += 1
                if sum(self.insert) >= len(self.groups):
                    break

    def get_logic_sol(self):
        logic_sol = dict()
        logic_sol["buggy_constraints"] = list()
        logic_sol["func_inputs"] = list()
        group_idx = 0
        for idx in range(self.size):
            ## input parameters for the current function
            func_inputs = []
            ## additional needed input parameters for the current function
            buggy_constraints = ""
            if self.insert[idx] != 0:
                copy_idx, tab_cnt = 0, 0
                constraints, vars = set(), set()
                for cnt in range(self.insert[idx]):
                    constraints = constraints.union(self.groups[group_idx + cnt])
                    vars = vars.union(self.vars[group_idx + cnt])
                for var in sorted(vars):
                    func_inputs.append("int8 {}".format(var))
                buggy_constraints += "\t\tint32 flag = 0;\n"
                for constraint in sorted(constraints):
                    buggy_constraints += "\t"*tab_cnt + "\t\tif{}{{\n".format(constraint)
                    tab_cnt += 1
                buggy_constraints += "\t"*tab_cnt + "\tflag = 1;\n"
                for k in range(len(constraints)-1, -1, -1):
                    buggy_constraints += "\t"*k + "\t\t}\n"
                group_idx += self.insert[idx]
            logic_sol["func_inputs"].append(func_inputs)
            logic_sol["buggy_constraints"].append(buggy_constraints)
        return logic_sol

    def get_guard(self):
        guard = list()
        group_idx = 0
        conds_default = \
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
            if self.insert[idx] == 0:
                guard.append(conds_default[numb_edges])

                # default guard so we can use the predefined solution.
                for i in range(numb_edges):
                    self.cached_guard_solution[idx][self.edges[idx][i]] = solution_values[numb_edges][i]

            else:
                next, bug_edge, m = 0, 0, 0
                conds = []
                for i in range(len(self.sln)):
                    if self.sln[i] == idx:
                        if i == len(self.sln) - 1:
                            next = 'bug'
                        else:
                            next = self.sln[i+1]
                for n in range(numb_edges):
                    if self.edges[idx][n] == next:
                        bug_edge = n
                for n in range(numb_edges):
                    if n == bug_edge:
                        conds.append("flag == 1")
                    else:
                        conds.append(conds_default[numb_edges-1][m] + " && flag == 0")
                        m += 1
                group_idx += 1
                guard.append(conds)

                # this is some special handling using the CVE formulas!
                # What we can do here is simply use the assignment of the model.
                #
                # TODO: HACK: currently the whole assignment is passed this can be simplified!

                # limitation / sanity check
                assert len(self.assignments) == 1, "unexpected number of variables in assignment"
                smt_symbol, array_assignment = list(self.assignments.items())[0]
                default_value, special_values = array_assignment

                # TODO: FIXME: HACK: "100" is a strange limitation / magic constant but it
                #                    is also used in the parse file so we reuse it here.
                final_array_value = [ special_values.get(i, default_value) for i in range(100) ]
                for i in range(numb_edges):
                    self.cached_guard_solution[idx][self.edges[idx][i]] = str(final_array_value)

        return guard

    def get_solution_values(self) -> list[str]:
        values = []
        current_position = self.sln[0]
        for next_cell in self.sln[1:] + ['bug']:
            values.append(self.cached_guard_solution[current_position][next_cell])
            current_position = next_cell
        return values + ["[ ]"] # needs an extra step to actually call the bug function