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
import numpy as np


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

    def get_cuts(self):
        regex = r"Cutting planes:([\n\s\-\w:]+)Explored"
        result = self.apply_regex(regex, flags=re.MULTILINE)
        if not result:
            # if no cuts found, return empty dictionary
            return {}
        cuts = [r for r in result.split("\n") if r != ""]
        regex = r"\s*{}: {}".format(self.wordSearch, self.numberSearch)
        searches = [re.search(regex, v) for v in cuts]
        return {
            s.group(1): int(s.group(2))
            for s in searches
            if s is not None and s.lastindex >= 2
        }

    def get_matrix(self):
        regex = r"Optimize a model with {0} rows, {0} columns and {0} nonzeros".format(
            self.numberSearch
        )
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = r"Presolved: {0} rows, {0} columns, {0} nonzeros".format(
            self.numberSearch
        )
        return self.apply_regex(regex, content_type="int")

    def get_stats(self):
        regex = r"{1}( \(.*\))?\n(Warning:.*\n)?Best objective ({0}|-), best bound ({0}|-), gap ({0}|-)".format(
            self.numberSearch, self.wordSearch
        )
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
        if not len(progress):
            return None
        df_filter = np.all(
            (
                progress.Node.str.match(r"^\*?H?\s*0"),
                progress.NodesLeft.str.match(r"^\+?H?\s*2"),
            ),
            axis=0,
        )

        cell = progress.Time.iloc[0]
        if len(df_filter) and any(df_filter):
            # we finished the cuts phase
            cell = progress.Time[df_filter].iloc[0]

        number = re.search(self.numberSearch, cell).group(1)
        return float(number)

    def get_lp_presolve(self):
        """
        :return: tuple  of length 3
        """
        regex = r"Presolve time: {0}s".format(self.numberSearch)
        time = self.apply_regex(regex, pos=0, content_type="float")
        if time is None:
            time = None
        regex = r"Presolve removed {0} rows and {0} columns".format(self.numberSearch)
        result = self.apply_regex(regex, content_type="int")
        if result is None:
            result = None, None
        return {"time": time, "rows": result[0], "cols": result[1]}

    def get_time(self):
        regex = r"Explored {0} nodes \({0} simplex iterations\) in {0} seconds".format(
            self.numberSearch
        )
        return self.apply_regex(regex, content_type="float", pos=2)

    def get_nodes(self):
        regex = r"Explored {0} nodes \({0} simplex iterations\) in {0} seconds".format(
            self.numberSearch
        )
        return self.apply_regex(regex, content_type="float", pos=0)

    def get_root_time(self):
        regex = r"Root relaxation: objective {0}, {0} iterations, {0} seconds".format(
            self.numberSearch
        )
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
        args["gap"] = "({}%)".format(self.number)
        args["time"] = "({}s)".format(self.number)

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
            args["obj"] = "({})".format(state)
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
