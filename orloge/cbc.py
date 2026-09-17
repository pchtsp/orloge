import re

from .base import LogFile, MIPProgressRow
from .constants import (
    LpStatusInfeasible,
    LpStatusNotSolved,
    LpStatusSolved,
    LpStatusTimeLimit,
    LpStatusUnbounded,
)


class CBC(LogFile):
    def __init__(self, path, **options):
        super().__init__(path, **options)
        self.name = "CBC"
        self.solver_status_map = {
            "Optimal solution found": LpStatusSolved,
            "Problem is infeasible": LpStatusInfeasible,
            "Stopped on time limit": LpStatusTimeLimit,
            "Problem proven infeasible": LpStatusInfeasible,
            "Problem is unbounded": LpStatusUnbounded,
            "Pre-processing says infeasible or unbounded": LpStatusInfeasible,
            "** Current model not valid": LpStatusNotSolved,
        }
        self.version_regex = r"Version: (\S+)"
        self.progress_names = [
            "Node",
            "NodesLeft",
            "BestInteger",
            "CutsBestBound",
            "Time",
        ]
        self.progress_filter = r"(^Cbc0010I.*$)"
        self.progress_row_cls = MIPProgressRow

    def get_cuts(self):
        # TODO
        pass

    def get_matrix(self):
        regex = rf"Problem .+ has {self.numberSearch} rows, {self.numberSearch} columns and {self.numberSearch} elements"
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = (
            rf"Cgl0004I processed model has {self.numberSearch} rows, {self.numberSearch} columns \(\d+ integer "
            rf"\(\d+ of which binary\)\) and {self.numberSearch} elements"
        )
        return self.apply_regex(regex, content_type="int")

    def get_stats(self):

        regex = f"Result - {self.wordSearch}"
        status = self.apply_regex(regex, pos=0)
        if status is None:
            # no solution found, I still want the status
            for k in self.solver_status_map:
                if self.apply_regex(re.escape(k)):
                    return k, None, None, None
        else:
            status = status.strip()
        regex = rf"best objective {self.numberSearch}( \(best possible {self.numberSearch}\))?, took {self.number} iterations and {self.number} nodes \({self.number} seconds\)"
        solution = self.apply_regex(regex)

        if solution is None:
            return None, None, None, None

        # if solution[0] == '1e+050':
        if self.apply_regex("No feasible solution found"):
            objective = None
        else:
            objective = float(solution[0])

        if solution[2] is None or solution[2] == "":
            bound = objective
        else:
            bound = float(solution[2])

        gap_rel = None
        if objective is not None and objective != 0 and bound is not None:
            gap_rel = abs(objective - bound) / abs(objective) * 100

        return status, objective, bound, gap_rel

    def get_cuts_time(self):
        # TODO
        return None

    def get_lp_presolve(self):
        # TODO
        return None

    def get_time(self):
        regex = rf"Total time \(CPU seconds\):\s*{self.numberSearch}"
        stats = self.apply_regex(regex, content_type="float", pos=0)
        return stats

    def get_nodes(self):
        regex = rf"Enumerated nodes:\s*{self.numberSearch}"
        return self.apply_regex(regex, content_type="int", pos=0)

    def get_root_time(self):
        # TODO
        return None

    def process_line(self, line):

        keys = ["n", "n_left", "b_int", "b_bound", "time"]
        args = {k: self.numberSearch for k in keys}
        find = re.search(
            r"Cbc0010I After {n} nodes, {n_left} on tree, {b_int} best solution, "
            r"best possible {b_bound} \({time} seconds\)".format(**args),
            line,
        )
        if not find:
            return None
        return find.groups()
