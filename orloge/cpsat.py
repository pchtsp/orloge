from cpsat_logutils.blocks import SearchProgressBlock, SolverBlock, ResponseBlock
from cpsat_logutils.blocks.search_progress import ModelEvent
from .base import LogFile
import cpsat_logutils as cpsatlog
import pandas as pd
from .constants import (
    LpStatusMemoryLimit,
    LpStatusSolved,
    LpStatusInfeasible,
    LpSolutionIntegerFeasible,
    LpStatusTimeLimit,
    LpStatusUnbounded,
    LpStatusNotSolved,
    LpSolutionOptimal,
    LpSolutionInfeasible,
    LpSolutionNoSolutionFound,
)


class CPSAT(LogFile):
    my_parser: cpsatlog.LogParser
    name = "CPSAT"

    def __init__(self, path, **options):
        super().__init__(path, **options)

        self.my_parser = cpsatlog.LogParser(self.content)

    def get_progress(self):
        """
        Builds a pandas DataFrame with the search progress.
        It assumes events are sorted by time.
        It fills with the previous result when no new information is available.
        The return DataFrame has the following columns:
        [the names of columns match the ones in the orloge library,
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
        progress_block = self.my_parser.get_block_of_type_or_none(SearchProgressBlock)
        events = progress_block.get_events()
        gap = obj = bound = None
        cons = new_cons = var = new_var = None
        my_table = []
        for e in events:
            if not isinstance(e, ModelEvent):
                bound = e.bound
                obj = e.obj
                gap = e.get_gap()
            else:
                var = e.vars
                new_var = e.vars_remaining
                cons = e.constr
                new_cons = e.constr_remaining
            my_table.append((e.time, bound, obj, gap, var, new_var, cons, new_cons))
        col_names = [
            "Time",
            "CutsBestBound",
            "BestInteger",
            "Gap",
            "NumVars",
            "RemVars",
            "NumCons",
            "RemCons",
        ]

        return pd.DataFrame.from_records(my_table, columns=col_names)

    def get_first_relax(self, progress):
        return None

    def get_nodes(self):
        return 0

    def get_time(self):
        my_block = self.my_parser.get_block_of_type_or_none(ResponseBlock)
        data = my_block.to_dict()
        return float(data["usertime"])

    def get_cuts(self):
        pass

    def get_version(self):
        my_block = self.my_parser.get_block_of_type_or_none(SolverBlock)
        return my_block.get_version()

    def get_cuts_dict(self, progress, bound, objective):
        return None

    def get_stats(self):
        # status, objective, bound, gap_rel
        my_block = self.my_parser.get_block_of_type_or_none(ResponseBlock)
        data = my_block.to_dict()
        gap = my_block.get_gap()
        return data["status"], float(data["objective"]), float(data["best_bound"]), gap

    def get_status_codes(self, status, obj):
        _map_status = dict(
            OPTIMAL=LpStatusSolved,
            FEASIBLE=LpStatusSolved,
            INFEASIBLE=LpStatusInfeasible,
            UNBOUNDED=LpStatusUnbounded,
            TIME_LIMIT=LpStatusTimeLimit,
            MEMORY_LIMIT=LpStatusMemoryLimit,
            UNKNOWN=LpStatusNotSolved,
        )
        _map_sol_status = dict(
            OPTIMAL=LpSolutionOptimal,
            FEASIBLE=LpSolutionIntegerFeasible,
            INFEASIBLE=LpSolutionInfeasible,
            UNKNOWN=LpSolutionNoSolutionFound,
        )
        return _map_status.get(status, LpStatusNotSolved), _map_sol_status.get(
            status, LpSolutionNoSolutionFound
        )

    def get_first_solution(self, progress):
        return None
