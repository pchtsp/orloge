__all__ = ["LogFile", "CPLEX", "GUROBI", "CBC", "CPSAT"]

from .cplex import CPLEX
from .gurobi import GUROBI
from .cbc import CBC
from .cpsat import CPSAT
from .base import LogFile

__map = dict(CPLEX=CPLEX, GUROBI=GUROBI, CBC=CBC, CPSAT=CPSAT)


def get_info_solver(path, solver, **options):
    my_solver = get_solver(solver)
    if my_solver is None:
        raise ValueError(f"solver {solver} is not recognized")
    log = my_solver(path, **options)
    return log.get_log_info()


def get_solver(solver):
    my_solver = __map.get(solver)
    if my_solver is None:
        raise ValueError(f"solver {solver} is not recognized")
    return my_solver
