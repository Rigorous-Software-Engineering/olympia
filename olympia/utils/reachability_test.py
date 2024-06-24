#!/bin/python

from typing import Any

import eth

# This hack is needed to deploy larger contracts
#
# HACK: FIXME: it might be a possibility to not allowing such contracts
# NOTE: if the internal VM fork is changed this has to be changed as well
eth.vm.forks.spurious_dragon.computation.EIP170_CODE_SIZE_LIMIT = 100000000
eth.vm.forks.shanghai.computation.MAX_INITCODE_SIZE = 100000000

from web3 import Web3, EthereumTesterProvider
from web3.contract.contract import Contract

from solcx.exceptions import SolcError
from pathlib import Path
import sys

from .compiler_helper import compile_solidity_file
from .custom_logging import logger

# most transactions require gas, since gas does not matter
# to us we can always use a fixed large amount.
DEFAULT_DEPLOY_GAS = 300000000

def deploy_contract(w3: Web3, abi: list, bytecode: str) -> Contract:
    """
    Deploys an ABI and binary on a given web3 context.
    The return value contains a deployed contract.
    """

    contract_deployer = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract_deployer.constructor().transact() # {'gas': DEFAULT_DEPLOY_GAS, 'gas_limit': DEFAULT_DEPLOY_GAS})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    deployed_address = tx_receipt["contractAddress"]

    # TODO: FIXME: throw this error instead of triggering an assertion
    assert deployed_address, "deployment did not provide a valid address!"
    contract_deployed = w3.eth.contract(address=deployed_address, abi=abi)
    return contract_deployed

def setup_web3() -> Web3:
    """
    Returns a default Web3 context with a mocked / test blockchain.
    """

    # instantiate the test provider
    w3 = Web3(EthereumTesterProvider())

    # assure the connection
    status = w3.is_connected()
    assert status, "unable to connect to test provider"

    # set the default account to some account in the mocked backend
    w3.eth.default_account = w3.eth.accounts[0]

    return w3

def parse_solution_file(file: Path) -> list[Any]:
    """
    This method reads the solution file and returns a list of values that
    should be passed to the deployed contracts 'step' function.
    """

    # solution files are simple files with an integer input in every line
    lines = []
    with open(file, "r") as fp:
        lines = fp.readlines()
    # remove any white spaces or trailing newlines
    stripped_lines = map(lambda x: x.replace("\n","").replace("\r", "").replace(" ", ""), lines)
    # transform all entries to ints

    # TODO: HACK: eval is not the safest choice here
    solution = [eval(x) for x in stripped_lines if x != ""]
    assert solution, f"unable to parse a solution list from {file}"
    return solution

def run_test(contract_file: Path, solution_file: Path) -> bool:

    # get a w3 context to deploy and test contracts
    w3 = setup_web3()
    logger.debug("-> successful setup of web3")

    # get the solution integers
    solution = parse_solution_file(solution_file)
    logger.debug(f"-> successful parsed solution {solution_file}")

    # compile source code
    try:
        abi, bytecode = compile_solidity_file(contract_file)
        logger.debug(f"-> successful compilation of {contract_file.as_posix()}")
    except SolcError as e:
        # something went wrong during compilation
        logger.error(e)
        return False

    # generate and deploy the contract on the test net
    contract_deployed = deploy_contract(w3, abi, bytecode)
    logger.debug(f"-> successful deployment of contract")

    logger.debug("------------- TEST START -------------")

    # get the deployed contract and call the bug function
    call_result = contract_deployed.functions.bug().call()
    logger.debug(f"Start test with initial 'bug' flag: {call_result}")
    assert call_result==False, "unexpected initial 'bug' flag state!"

    # do steps
    for step_val in solution:
        # calls the step function with the values provided in the solution. This can be anything
        # that is processable by the python 'eval' function.
        tx_hash = contract_deployed.functions.step(step_val).transact() # {'gas': DEFAULT_DEPLOY_GAS, 'gas_limit': DEFAULT_DEPLOY_GAS})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        # 'next_cell' is an 8 byte entry on the first slot (slot 0). Since it is packed together with
        # the 'bug' and 'stop' boolean, and possible other values we have to slice it out of the 32 byte slot.
        # SLOT_0 := [ unknown (22 bytes) | bug (1 byte) | next_cell (8 bytes) | stop (1 byte) ]
        next_cell_bytes = w3.eth.get_storage_at(contract_deployed.address, 0).lower()[23:-2]
        # finally we can sign extend it using the big-endian order.
        next_cell = int.from_bytes(next_cell_bytes, byteorder='big', signed=True)
        logger.debug(f"  - call step({step_val}) ==> status: {tx_receipt['status']} | next_cell: {next_cell}")
        # after every call we also check if the transaction was successful, and if not, we
        # throw an assertion error or simply stop testing
        if not tx_receipt['status'] == 1:
            logger.error("     ==> transaction failed! Abort testing ...")
            break # abort
        # assert tx_receipt['status'] == 1, "unable to perform transaction!"

    # finally check if bug was found
    call_result = contract_deployed.functions.bug().call()
    logger.debug(f"==> final 'bug' flag value: {call_result}")
    return call_result