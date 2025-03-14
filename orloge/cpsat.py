from cpsat_log_parser.blocks import SearchProgressBlock, SolverBlock, ResponseBlock
from .base import LogFile
import cpsat_log_parser as cpsatlog
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
        progress_block = self.my_parser.get_block_of_type_or_none(SearchProgressBlock)
        return progress_block.get_table()

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
