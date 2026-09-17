from collections.abc import Sequence
from dataclasses import dataclass

from cpsat_logutils import CpSatLog, parse_log
from cpsat_logutils.schema import SearchEvent

from .base import LogFile, MIPProgressRow
from .constants import (
    LpSolutionInfeasible,
    LpSolutionIntegerFeasible,
    LpSolutionNoSolutionFound,
    LpSolutionOptimal,
    LpStatusInfeasible,
    LpStatusMemoryLimit,
    LpStatusNotSolved,
    LpStatusSolved,
    LpStatusTimeLimit,
    LpStatusUnbounded,
)


@dataclass
class CPSATProgressRow(MIPProgressRow):
    Gap: float | None = None
    NumVars: int | None = None
    RemVars: int | None = None
    NumCons: int | None = None
    RemCons: int | None = None


def _has_objective(event: SearchEvent) -> bool:
    """True when the line carried a `best:` field (finite or infinite)."""
    return event.objective is not None or event.objective_infinite is not None


def _gap(obj: float | None, bound: float | None) -> float | None:
    """Relative gap in percent, as cp-sat defines it: |obj-bound| / max(1, |obj|)."""
    if obj is None or bound is None:
        return None
    return 100 * (abs(obj - bound) / max(1, abs(obj)))


class CPSAT(LogFile):
    my_parser: CpSatLog
    name = "CPSAT"

    def __init__(self, path, **options):
        super().__init__(path, **options)

        self.my_parser = parse_log(self.content)

    def get_progress(self) -> Sequence[CPSATProgressRow]:
        """
        Builds a list of CPSATProgressRow with the search progress.
        It assumes events are sorted by time.
        It fills with the previous result when no new information is available.
        Each row has the following fields:
        [the names match the columns used elsewhere in the orloge library,
        this may not be very relevant to cp-sat]
        - Time: The time of the event.
        - CutsBestBound: The best bound found at the time.
        - BestInteger: The best integer found at the time.
        - Gap: The gap between the best bound and the best integer.
        - NumVars: The number of variables before the event.
        - RemVars: The number of remaining variables after the event.
        - NumCons: The number of constraints before the event.
        - RemCons: The number of remaining constraints after the event.
        """
        search = self.my_parser.search
        if search is None:
            return []
        sense = search.objective_sense
        gap = obj = bound = None
        cons = new_cons = var = new_var = None
        my_table = []
        for e in search.events:
            if e.kind == "model":
                var = e.model_vars_total
                new_var = e.model_vars
                cons = e.model_constraints_total
                new_cons = e.model_constraints
            elif e.kind in ("solution", "bound") and _has_objective(e):
                obj = e.objective
                bound = e.bound(sense)
                if bound is None and obj is not None:
                    # `next:[]` means the search range is empty: the bound met the objective
                    bound = obj
                gap = _gap(obj, bound)
            else:
                # `#Done` and anything without a `best:` field (satisfaction
                # problems) carry no new information for the table
                continue
            my_table.append(
                CPSATProgressRow(
                    Time=e.time,
                    CutsBestBound=bound,
                    BestInteger=obj,
                    Gap=gap,
                    NumVars=var,
                    RemVars=new_var,
                    NumCons=cons,
                    RemCons=new_cons,
                )
            )

        return my_table

    def get_first_relax(self, progress):
        return None

    def get_nodes(self):
        return 0

    def get_time(self):
        response = self.my_parser.response
        if response is None or response.usertime is None:
            return None
        return response.usertime.value

    def get_cuts(self):
        pass

    def get_version(self):
        solver = self.my_parser.solver
        if solver is None or solver.version is None:
            return None
        # the parser strips the leading "v" of "Starting CP-SAT solver v9.3.10497"
        return solver.version.value

    def get_cuts_dict(self, progress, best_bound, best_solution):
        return None

    def get_stats(self):
        # status, objective, bound, gap_rel
        response = self.my_parser.response
        if response is None:
            return None, None, None, None
        status = response.status.value if response.status else None
        objective = response.objective.value if response.objective else None
        bound = response.best_bound.value if response.best_bound else None
        return status, objective, bound, response.gap

    def get_status_codes(self, status, obj):
        _map_status = {
            "OPTIMAL": LpStatusSolved,
            "FEASIBLE": LpStatusSolved,
            "INFEASIBLE": LpStatusInfeasible,
            "UNBOUNDED": LpStatusUnbounded,
            "TIME_LIMIT": LpStatusTimeLimit,
            "MEMORY_LIMIT": LpStatusMemoryLimit,
            "UNKNOWN": LpStatusNotSolved,
        }
        _map_sol_status = {
            "OPTIMAL": LpSolutionOptimal,
            "FEASIBLE": LpSolutionIntegerFeasible,
            "INFEASIBLE": LpSolutionInfeasible,
            "UNKNOWN": LpSolutionNoSolutionFound,
        }
        return _map_status.get(status, LpStatusNotSolved), _map_sol_status.get(
            status, LpSolutionNoSolutionFound
        )

    def get_first_solution(self, progress):
        return None
