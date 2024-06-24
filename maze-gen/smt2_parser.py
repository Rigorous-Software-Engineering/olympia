from enum import StrEnum
import sys, random
from pysmt.operators import op_to_str
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from collections import defaultdict
from pysmt.shortcuts import get_model, is_sat, Not, And, Or
import pysmt as pysmt
from pysmt.solvers.solver import Model

class ErrorKind(StrEnum):
    UNRECOGNIZED_TYPE = "unrecognized type" # not expected and not implemented
    UNSUPPORTED_TYPE = "unsupported type"   # expected but not implemented

def error(flag: ErrorKind, node_type : int | tuple[int,int] ):
    print(f"ERROR: {flag}")
    match node_type:
        case int(single_node):
            print(f"  -> node type {op_to_str(single_node)}")
        case (l_node, r_node):
            print(f"  -> node types {op_to_str(l_node)} and {op_to_str(r_node)}")
        case _:
            raise NotImplementedError("")
    exit(1) # abort execution because of parsing error

def cast_expr_helper(expr: str, node: FNode, signed: bool) -> str:
    base = "int" if signed else "uint"
    width = node.bv_width()
    return f"{base}{width}({expr})"

def ext_helper(node: FNode, is_sext: bool) -> tuple[str, bool]:
    (value, ) = node.args()
    target_width = node.bv_width()
    (value_cons, value_signed) = convert(value)
    if not value_signed == is_sext:
        value_cons = cast_expr_helper(value_cons, value, is_sext)
    ext_base = "int" if is_sext else "uint"
    return f"{ext_base}{target_width}({value_cons})", is_sext

def bin_op_same_sign_helper(op: str, bin_op_node: FNode, forced_sign: bool | None = None) -> tuple[str, bool]:
    (l_node, r_node) = bin_op_node.args()
    l_cons, l_sign = convert(l_node)
    r_cons, r_sign = convert(r_node)

    if forced_sign == None:
        forced_sign = l_sign
    if not (forced_sign == l_sign):
        l_cons = cast_expr_helper(l_cons, l_node, forced_sign)
    if not (forced_sign == r_sign):
        r_cons = cast_expr_helper(r_cons, r_node, forced_sign)

    return f"({l_cons} {op} {r_cons})", forced_sign

def deflatten(args, op):
    x = args[0]
    for i in range(1,len(args)):
        y = args[i]
        x = op(x,y)
    return x

def convert(node: FNode) -> tuple[str, bool]:

    """
    Converts a SMT FNode into a solidity expression and tracks signed-ness, expression
    size and temporary variables used to reduce depth of a single expression.
    If a node is unknown, an error is thrown and the generation is exited.

    TODO: FIXME:
        - is_bv_concat, currently it always returns 'model_version'
        - is_select,    currently this always assumes the one allowed array on the LHS
        - is_symbol,    proper symbol handling
    """

    cons = None
    signed = False # always assume unsigned by default
    if node.is_iff():
            (l, r) = node.args()
            if l.is_false(): # TODO: FIXME: also check right-hand-side
                (r_cons, _) = convert(r)
                cons = f"(!{r_cons})"
            else:
                error(ErrorKind.UNSUPPORTED_TYPE, node.get_type())
    elif node.is_equals():
        cons, _ = bin_op_same_sign_helper("==", node)
    elif node.is_bv_sle():
        cons, _ = bin_op_same_sign_helper("<=", node, True)
    elif node.is_bv_ule():
        cons, _ = bin_op_same_sign_helper("<=", node, False)
    elif node.is_bv_slt():
        cons, _ = bin_op_same_sign_helper("<", node, True)
    elif node.is_bv_ult():
        cons, _ = bin_op_same_sign_helper("<", node, False)
    elif node.is_bv_add():
        cons, signed = bin_op_same_sign_helper("+", node)
    elif node.is_bv_sub():
        cons, signed = bin_op_same_sign_helper("-", node)
    elif node.is_bv_mul():
        cons, signed = bin_op_same_sign_helper("*", node)
    elif node.is_bv_udiv():
        cons, signed = bin_op_same_sign_helper("/", node, False)
    elif node.is_bv_sdiv():
        cons, signed = bin_op_same_sign_helper("/", node, True)
    elif node.is_bv_urem():
        cons, signed = bin_op_same_sign_helper("%", node, False)
    elif node.is_bv_srem():
        cons, signed = bin_op_same_sign_helper("%", node, True)
    ## sext -> signed extension -> pads the number with leading ones (twos-complement)
    elif node.is_bv_sext():
        cons, signed = ext_helper(node, True)
    ## zext -> zero extension -> pads the number with leading zeros
    elif node.is_bv_zext():
        cons, signed = ext_helper(node, False)
    elif node.is_bv_concat():
        cons = "model_version" # TODO: HACK: legacy limitation from fuzzle 
        signed = False
        size = 0
    elif node.is_bv_extract():
        ext_start = node.bv_extract_start()
        ext_end = node.bv_extract_end()
        (l, ) = node.args()
        start_width = l.bv_width()
        (l_cons, l_signed) = convert(l)
        if l_signed:
                l_cons = cast_expr_helper(l_cons, l, False)
        target_size : int = (ext_end - ext_start + 1)
        assert target_size > 0, "unrealistic target size for extraction"
        if ext_start == 0: # we can simply use cast to truncate
            cons = f"uint{target_size}({l_cons})"
        else: # apply general bit extraction with right left shifts
            shift_l = start_width - (ext_end + 1)
            shift_r = shift_l + ext_start
            cons = f"uint{target_size}(({l_cons} << {shift_l}) >> {shift_r})"
    elif node.is_and():
        node = deflatten(node.args(),And)
        cons, _ = bin_op_same_sign_helper("&&", node)
    elif node.is_or():
        node = deflatten(node.args(),Or)
        cons, _ = bin_op_same_sign_helper("||", node)
    elif node.is_not():
        (b,) = node.args()
        (b_cons, _) = convert(b)
        cons = f"(!{b_cons})"
    elif node.is_bool_constant():
        cons = "true" if node.is_bool_constant(True) else "false"
    elif node.is_select():
        (l, r) = node.args()
        if l.is_symbol() and r.is_bv_constant():
            cons = f"inp[{r.constant_value()}]"
            signed = True # set signed to true because the array is probably signed
        else:
            error(ErrorKind.UNSUPPORTED_TYPE, node.get_type())
    elif node.is_bv_constant():
        cons = f"uint{node.bv_width()}({node.constant_value()})"
    # elif node.is_symbol():
    #   pass
    else:
        error(ErrorKind.UNRECOGNIZED_TYPE, node.get_type())

    assert cons, f"unable to generate a solidity expression for {op_to_str(node.get_type())}"
    return (cons, signed)


def conjunction_to_clauses(formula):
    """
    Transforms a chain of conjunctions into a list of sub-formulas.
    Example:
        sub_form1 && sub_form2 && ... ==> [sub_form1, sub_form2, ...]
    """
    if formula.is_and():
        clauses = set()
        for node in formula.args():
            clauses = clauses.union(conjunction_to_clauses(node))
    else:
        clauses = set([formula])
    return clauses

def parse_model_variables(model: Model, ignore_symbols: list[str] = []) -> dict[str, tuple[int, dict[int, int]]]:

    """
    This function takes a Z3 model and a list of variable symbols that should
    be ignored for the output. It parses the model and returns a dictionary
    containing the found symbol names and a tuple containing the value / default value
    and for arrays a dictionary for the specific indices.

    NOTE: currently the model ONLY works for array variables!
    """

    result = dict()

    for variable_assignment in model:
        symbol, value = variable_assignment
        assert symbol.is_symbol(), "unexpected model assignment structure"

        if str(symbol) in ignore_symbols:
            # if the symbol of the assignment is inside of the
            # ignore list, skip to the next one
            continue

        # Currently we expect the model to be one or more arrays!
        # Anything else is not supported for now.

        if value.node_type() in [60, 61]: # ARRAY_STORE | ARRAY_VALUE
            # The array store FNode inside of an assignment is a nested store
            # on an array value. To get all values we recursively go deeper into
            # the structure using the "array_value_default".

            # sanity check
            assert value.is_store() or value.is_array_value(), "unexpected fnode predicate for ARRAY_STORE or ARRAY_VALUE type!"

            final_assignment_map = {}
            temporary_base_array = value
            while temporary_base_array.is_store():
                # get assignments of current level and store them in a python dictionary
                assignment_map = temporary_base_array.array_value_assigned_values_map()
                for array_index in assignment_map:
                    array_value = assignment_map[array_index]
                    # for now we expect the arrays to be bit vector typed, (e.g. index: 32-bits and value: 8-bits)
                    assert array_index.is_bv_constant(), "index was not a BitVector Constant"
                    assert array_value.is_bv_constant(), "value was not a BitVector Constant"
                    final_assignment_map[array_index.constant_value()] = array_value.constant_value()

                # go one level deeper and repeat
                temporary_base_array = temporary_base_array.array_value_default()

            # after the while loop the array should be a normal array value
            assert temporary_base_array.is_array_value(), "unexpected node type for final base array!"

            # the default initialization of the array value should also be a bit vector constant
            initialization_value_fnode = temporary_base_array.array_value_default()
            assert initialization_value_fnode.is_bv_constant(), "init default value was not a BitVector Constant"
            initialization_value = initialization_value_fnode.constant_value()

            # Create an entry for the current symbol and pass the retrieved values as a tuple.
            # We sort the assignment keys for better processing and debugging.
            result[str(symbol)] = (initialization_value, dict(sorted(final_assignment_map.items())))
        else:
            # otherwise we do not have an implementation and we should not continue!
            raise NotImplementedError(f"Unexpected value node type ({op_to_str(value.node_type())})!")

    return result

def parse(file_path):
    parser = SmtLibParser()
    script = parser.get_script_fname(file_path)

    # Gets the available "variables". Currently we expects the variable in the form
    # of arrays. Furthermore, there is a limitation to have only 1 array.
    decl_arr = list()
    decls = script.filter_by_command_name("declare-fun")
    for d in decls:
        for arg in d.args:
            if (str)(arg) != "model_version": # skip over the 'model_version'
                decl_arr.append(arg)

    # sanity check
    assert len(decl_arr) == 1, f"unexpected amount of array variables! Expects (1) but found ({len(decl_arr)})"

    # The method SmtLibScript.get_strict_formula() conjoins multiple assertions.
    # If this is not possible due to multiple SAT checks or push/pop, an exception
    # is thrown (should not be the case for the provided CVE files!)
    formula = script.get_strict_formula()
    # try to simplify the formula a little such that the produced conditions are of moderate size
    formula = formula.simplify()

    # For safety we can check if we are sat, but this takes a lot of time so it is commented out.
    # Further down we do this anyways with a "get_model" call
    # assert(is_sat(formula, solver_name="z3") == True)

    # returns a set of formulas representing clauses, i.e. it creates a set
    # from sub-formulas that all have to be satisfied.
    #
    # sub_form1 && sub_form2 && ... ==> [sub_form1, sub_form2, ...]
    #
    # These are used to represent the different if conditions for a transaction.
    #
    # TODO: add better explanation in the function what this is doing
    clauses = conjunction_to_clauses(formula)

    # the following part retrieves a model for the formula and parses the
    # variable array assignment.
    model = get_model(formula)
    assert model, "CVE formula was not SAT"
    variable_model_map = parse_model_variables(model, ["model_version"]) # TODO: use this value

    # overall used variable set
    variables = set()

    # set of parsed conditions
    parsed_cons = set()

    # iterate over the clauses
    for clause in clauses:

        # convert the current clause to a string containing the corresponding solidity condition
        (cons_in_sol, _) = convert(clause)

        if "model_version" in cons_in_sol:
            # again ignore all conditions with the 'model_version' variable
            continue

        parsed_cons.add(cons_in_sol)

        for declared in decl_arr:
            # TODO: FIXME: remove hardcoded array limitation 100 elements.
            for idx in range(0,100):
                var_idx = "inp[" + str(idx) + "]"
                # check wether the generated inp[*] value is inside the condition.
                # TODO: FIXME: check without trailing " " or ")"
                if var_idx + " " in cons_in_sol or var_idx + ")" in cons_in_sol:
                    variables.add("inp[" + str(idx) + "]") # if it is inside put it to the variable list
    return parsed_cons, variables, variable_model_map

def extract_vars(cond, variables):
    vars = set()
    #print(f"variables: {variables}")
    for var in variables:
        if var + " " in cond or var + ")" in cond:
            vars.add(var)
    return vars

class Graph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, node, neighbour):
        self.graph[node].append(neighbour)

    def get_edges(self, node):
        return self.graph[node]

    def separate_helper(self, node, visited, group):
        if node not in visited:
            group.add(node)
            visited.add(node)
        for neighbour in self.graph[node]:
            if neighbour not in visited:
                self.separate_helper(neighbour, visited, group)
        return group

    def separate(self):
        visited = set()
        groups = list()
        for node in self.graph:
            group = self.separate_helper(node, visited, set())
            if len(group) > 0:
                groups.append(group)
        return groups

def independent_formulas(conds, variables):
    # create a new graph
    formula = Graph()

    # Iterate n x n over the conditions and check if the variable-set
    # of the conditions intersect. If they do, create an edge between the
    # two conditions.
    for cond in conds:
        vars = extract_vars(cond, variables)
        for other in conds:
            if len(vars.intersection(extract_vars(other, variables))) > 0:
                # add an edge to the graph
                formula.add_edge(cond, other)

    # generate a list of all the connected groups
    # of the condition graph
    groups = formula.separate()
    vars_by_groups = list()

    # For each group gather the used variable and safe them in a separate list
    for group in groups:
        used_vars = set()
        for cond in group:
            used_vars = used_vars.union(extract_vars(cond, variables))
        vars_by_groups.append(sorted(used_vars))

    return groups, vars_by_groups

def main(file_path):
    conds, variables, assignments = parse(file_path)
    for cond in conds:
        vars = extract_vars(cond, variables)
        print(cond)
        print(vars, "\n")
    print("-"*100)
    groups, vars_by_groups = independent_formulas(conds, variables)
    for idx in range(len(groups)):
        print(vars_by_groups[idx], "\n")
        print("*"*100)

if __name__ == '__main__':
    file_path = sys.argv[1]
    main(file_path)
