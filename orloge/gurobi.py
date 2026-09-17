import re
from dataclasses import dataclass

from .base import LogFile, MIPProgressRow
from .constants import (
    LpStatusInfeasible,
    LpStatusMemoryLimit,
    LpStatusNotSolved,
    LpStatusSolved,
    LpStatusTimeLimit,
    LpStatusUnbounded,
)


@dataclass
class GUROBIProgressRow(MIPProgressRow):
    Objective: float | str | None = None
    Depth: int | None = None
    IInf: int | None = None
    Gap: float | None = None
    ItpNode: int | None = None


class GUROBI(LogFile):
    name = "GUROBI"

    def __init__(self, path, **options):
        super().__init__(path, **options)
        self.solver_status_map = {
            "Optimal solution found": LpStatusSolved,
            "Solved with barrier": LpStatusSolved,
            "Model is infeasible": LpStatusInfeasible,
            "Model is infeasible or unbounded": LpStatusInfeasible,
            "Time limit reached": LpStatusTimeLimit,
            "Out of memory": LpStatusMemoryLimit,
            "ERROR 10001": LpStatusMemoryLimit,
            "ERROR 10003": LpStatusNotSolved,
            "^Model is unbounded": LpStatusUnbounded,
        }
        self.version_regex = r"Gurobi Optimizer version (\S+)"
        self.progress_names = [
            "Node",
            "NodesLeft",
            "Objective",
            "Depth",
            "IInf",
            "BestInteger",
            "CutsBestBound",
            "Gap",
            "ItpNode",
            "Time",
        ]
        self.progress_filter = r"(^[\*H]?\s+\d.*$)"
        self.progress_row_cls = GUROBIProgressRow

    def get_cuts(self):
        regex = r"Cutting planes:([\n\s\-\w:]+)Explored"
        result = self.apply_regex(regex, flags=re.MULTILINE)
        if not result:
            # if no cuts found, return empty dictionary
            return {}
        cuts = [r for r in result.split("\n") if r != ""]
        regex = rf"\s*{self.wordSearch}: {self.numberSearch}"
        searches = [re.search(regex, v) for v in cuts]
        return {
            s.group(1): int(s.group(2))
            for s in searches
            if s is not None and s.lastindex is not None and s.lastindex >= 2
        }

    def get_matrix(self):
        regex = rf"Optimize a model with {self.numberSearch} rows, {self.numberSearch} columns and {self.numberSearch} nonzeros"
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = rf"Presolved: {self.numberSearch} rows, {self.numberSearch} columns, {self.numberSearch} nonzeros"
        return self.apply_regex(regex, content_type="int")

    def get_stats(self):
        regex = rf"{self.wordSearch}( \(.*\))?\n(Warning:.*\n)?Best objective ({self.numberSearch}|-), best bound ({self.numberSearch}|-), gap ({self.numberSearch}|-)"
        # content_type = ['', '', 'float', 'float', 'float']
        solution = self.apply_regex(regex)
        if solution is None:
            return None, None, None, None

        status = solution[0]
        objective, bound, gap_rel = [
            float(solution[pos]) if solution[pos] != "-" else None for pos in [3, 5, 7]
        ]
        return status, objective, bound, gap_rel

    def get_cuts_time(self):
        progress = self.get_progress()
        if not progress:
            return None
        matches = [row for row in progress if row.Node == 0 and row.NodesLeft == 2]
        if matches:
            # we finished the cuts phase
            return matches[0].Time
        return progress[0].Time

    def get_lp_presolve(self):
        """
        :return: tuple  of length 3
        """
        regex = rf"Presolve time: {self.numberSearch}s"
        time = self.apply_regex(regex, pos=0, content_type="float")
        if time is None:
            time = None
        regex = rf"Presolve removed {self.numberSearch} rows and {self.numberSearch} columns"
        result = self.apply_regex(regex, content_type="int")
        if result is None:
            result = None, None
        return {"time": time, "rows": result[0], "cols": result[1]}

    def get_time(self):
        regex = rf"Explored {self.numberSearch} nodes \({self.numberSearch} simplex iterations\) in {self.numberSearch} seconds"
        return self.apply_regex(regex, content_type="float", pos=2)

    def get_nodes(self):
        regex = rf"Explored {self.numberSearch} nodes \({self.numberSearch} simplex iterations\) in {self.numberSearch} seconds"
        return self.apply_regex(regex, content_type="float", pos=0)

    def get_root_time(self):
        regex = rf"Root relaxation: objective {self.numberSearch}, {self.numberSearch} iterations, {self.numberSearch} seconds"
        return self.apply_regex(regex, pos=2, content_type="float")

    def process_line(self, line):
        keys = [
            "n",
            "n_left",
            "obj",
            "iinf",
            "b_int",
            "b_bound",
            "ItCnt",
            "gap",
            "depth",
            "time",
        ]
        args = {k: self.numberSearch for k in keys}
        args["gap"] = f"({self.number}%)"
        args["time"] = f"({self.number}s)"

        if line[0] in ["*", "H"]:
            args["obj"] = "()"
            args["iinf"] = "()"
            args["depth"] = "()"

        if re.search(r"\*\s*\d+\+", line):
            args["obj"] = "()"
            args["ItCnt"] = "()"

        if re.search(r"Cuts: \d+", line):
            args["b_bound"] = r"(Cuts: \d+)"

        get = re.search(r"\*?\s*\d+\+?\s*\d+\s*(infeasible|cutoff|integral)", line)
        if get is not None:
            state = get.group(1)
            args["obj"] = f"({state})"
            if state in ["integral"]:
                pass
            else:
                args["iinf"] = "()"

        find = re.search(
            r"\s+{n}\s+{n_left}\s+{obj}\s+{depth}\s+{iinf}?\s+{b_int}?-?"
            r"\s+{b_bound}\s+{gap}?-?\s+{ItCnt}?-?\s+{time}".format(**args),
            line,
        )
        if not find:
            return None
        return find.groups()
