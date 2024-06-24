from pathlib import Path

import solcx
from solcx.exceptions import SolcError

# install the 0.8.26 version of solidity
__SOLC_VERSION = "0.8.26"
__SOLC_VERSION_SINGLETON = None
def get_solc_version():
    global __SOLC_VERSION_SINGLETON
    if __SOLC_VERSION_SINGLETON == None:
        __SOLC_VERSION_SINGLETON = solcx.install_solc(version=__SOLC_VERSION)
    return __SOLC_VERSION_SINGLETON

def compile_solidity_source(source: str) -> tuple[list[dict], str]:
    """
    This function uses the solcx compiler to compile the given solidity source.
    The compiler is configured to target the ABI and binary.
    Finally the ABI and Binary objects are returned in form of a tuple.
    """

    # compile the sources and specify that we need the abi and binary
    compiled_solidity = solcx.compile_source(source, output_values=['abi', 'bin'], solc_version=get_solc_version(), via_ir=True, optimize_yul=True, optimize=True)

    # retrieve and return the abi and binary of the solidity contract 
    contract_id, contract_interface = compiled_solidity.popitem()
    bytecode = contract_interface['bin']
    abi = contract_interface['abi']

    return abi, bytecode

def compile_solidity_file(file: Path) -> tuple[list[dict], str]:
    """
    The function takes a solidity source file and returns the compiled
    ABI and binary as a tuple. It is a small helper function to deal with
    file handling. See the 'compile_solidity_source' function for more details.
    """
    assert file, f"unable to locate or open solidity file '{file}'"

    content = None
    with open(file, "r") as fp:
        content = fp.read()
    assert content, f"unable to read content of file {file}"
    return compile_solidity_source(content)

def is_compilable_solidity_file(file: Path):
    """
    Helper function to see if a contract file is compilable or not.
    This is used during benchmark generation to remove instances that
    would not occur in the wild.
    """
    assert file, f"unable to locate or open solidity file '{file}'"

    try:
        _ = compile_solidity_file(file)
    except SolcError:
        return False
    return True