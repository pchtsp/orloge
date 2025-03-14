from .base import LogFile
from .constants import (
    LpStatusMemoryLimit,
    LpStatusSolved,
    LpStatusInfeasible,
    LpStatusTimeLimit,
    LpStatusUnbounded,
    LpStatusNotSolved,
)
import re


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

    def get_cuts(self):
        # TODO
        pass

    def get_matrix(self):
        regex = r"Problem .+ has {0} rows, {0} columns and {0} elements".format(
            self.numberSearch
        )
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = (
            r"Cgl0004I processed model has {0} rows, {0} columns \(\d+ integer "
            r"\(\d+ of which binary\)\) and {0} elements".format(self.numberSearch)
        )
        return self.apply_regex(regex, content_type="int")

    def get_stats(self):

        regex = "Result - {}".format(self.wordSearch)
        status = self.apply_regex(regex, pos=0)
        if status is None:
            # no solution found, I still want the status
            for k in self.solver_status_map.keys():
                if self.apply_regex(re.escape(k)):
                    return k, None, None, None
        else:
            status = status.strip()
        regex = r"best objective {0}( \(best possible {0}\))?, took {1} iterations and {1} nodes \({1} seconds\)".format(
            self.numberSearch, self.number
        )
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
        if objective is not None and objective != 0:
            gap_rel = abs(objective - bound) / abs(objective) * 100

        return status, objective, bound, gap_rel

    def get_cuts_time(self):
        # TODO
        return None

    def get_lp_presolve(self):
        # TODO
        return None

    def get_time(self):
        regex = r"Total time \(CPU seconds\):\s*{}".format(self.numberSearch)
        stats = self.apply_regex(regex, content_type="float", pos=0)
        return stats

    def get_nodes(self):
        regex = r"Enumerated nodes:\s*{}".format(self.numberSearch)
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
