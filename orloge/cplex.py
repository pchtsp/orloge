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
class CPLEXProgressRow(MIPProgressRow):
    Objective: float | str | None = None
    IInf: int | None = None
    ItpNode: int | None = None
    Gap: float | None = None
    # Time is inherited (default None) and filled in later by get_progress()


class CPLEX(LogFile):
    # Reference:
    # https://www.ibm.com/support/knowledgecenter/SSSA5P_12.6.3/ilog.odms.cplex.help/CPLEX/UsrMan/topics/discr_optim/mip/para/52_node_log.html
    name = "CPLEX"

    def __init__(self, path, **options):
        super().__init__(path, **options)
        self.solver_status_map = {
            "MIP - Memory limit exceeded": LpStatusMemoryLimit,
            "MIP - Integer optimal": LpStatusSolved,
            "MIP - Integer infeasible.": LpStatusInfeasible,
            "MIP - Time limit exceeded": LpStatusTimeLimit,
            "MIP - Integer unbounded": LpStatusUnbounded,
            "MIP - Integer infeasible or unbounded": LpStatusInfeasible,
            "CPLEX Error  1001: Out of memory": LpStatusMemoryLimit,
            "No file read": LpStatusNotSolved,
        }

        self.version_regex = [
            r"Welcome to IBM\(R\) ILOG\(R\) CPLEX\(R\) Interactive Optimizer (\S+)",
            r"Log started \((\S+)\)",
            r"Version identifier: (\S+)",
        ]
        self.header_log_start = ["Welcome to IBM", "Log started"]
        self.progress_names = [
            "Node",
            "NodesLeft",
            "Objective",
            "IInf",
            "BestInteger",
            "CutsBestBound",
            "ItpNode",
            "Gap",
        ]
        self.progress_filter = r"(^[\*H]?\s*\d.*$)"
        self.progress_row_cls = CPLEXProgressRow
        # in case of multiple logs in the same file,
        # we choose to get the last one.
        self.content = self.clean_before_last_log()

    def clean_before_last_log(self):
        options = self.header_log_start
        for opt in options:
            # this finds the last occurence of the string
            pos = self.content.rfind(opt)
            if pos != -1:
                return self.content[pos:]
        return self.content

    def get_version(self):
        result = None
        for reg in self.version_regex:
            result = self.apply_regex(reg)
            if result:
                return result
        return result

    def get_stats(self):
        status = self.get_status()
        objective = self.get_objective()
        bound, _gap_abs, gap_rel = self.get_gap()
        return status, objective, bound, gap_rel

    def get_status(self):
        for k in self.solver_status_map:
            search_string = re.escape(k)
            if self.apply_regex(search_string):
                return k

    def get_objective(self):
        """
        :return: tuple of length 2
        """
        regex = rf"Objective\s+=\s+{self.numberSearch}\s*\n"
        result = self.apply_regex(regex, flags=re.MULTILINE)
        if result is not None:
            result = float(result)
        return result

    def get_gap(self):
        """
        :return: tuple of length 3: bound, absolute gap, relative gap
        """
        regex = rf"Current MIP best bound =\s+{self.numberSearch} \(gap = {self.numberSearch}, {self.numberSearch}%\)"
        result = self.apply_regex(regex, content_type="float")
        if result is None:
            return None, None, None
        return result

    def get_matrix(self):
        """
        :return: tuple of length 3
        """
        # TODO: this is not correctly calculated: we need to sum the change to the initial to get
        #  the original.
        regex = rf"Reduced MIP has {self.numberSearch} rows, {self.numberSearch} columns, and {self.numberSearch} nonzeros"
        return self.apply_regex(regex, content_type="int", num=0)

    def get_matrix_post(self):
        """
        :return: tuple of length 3
        """
        regex = rf"Reduced MIP has {self.numberSearch} rows, {self.numberSearch} columns, and {self.numberSearch} nonzeros"
        return self.apply_regex(regex, content_type="int", num=-1)

    def get_cuts(self):
        """
        :return: dictionary of cuts
        """
        regex = rf"{self.wordSearch} cuts applied:  {self.numberSearch}"
        result = self.apply_regex(regex, first=False)
        if result is None:
            return None
        return {k[0]: int(k[1]) for k in result}

    def get_lp_presolve(self):
        """
        :return: tuple  of length 3
        """
        # TODO: this is not correctly calculated:
        #  we need to sum the two? preprocessings in my cases
        regex = (
            rf"Presolve time = {self.numberSearch} sec. \({self.numberSearch} ticks\)"
        )
        time = self.apply_regex(regex, pos=0, content_type="float")

        regex = rf"LP Presolve eliminated {self.numberSearch} rows and {self.numberSearch} columns"
        result = self.apply_regex(regex, content_type="int")
        if result is None:
            result = None, None
        return {"time": time, "rows": result[0], "cols": result[1]}

    def get_time(self):
        regex = rf"Solution time =\s+{self.numberSearch} sec\.\s+Iterations = {self.numberSearch}\s+Nodes = {self.numberSearch}"
        result = self.apply_regex(regex, content_type="float", pos=0)
        if result is not None:
            return result
        regex = rf"Total \(root\+branch&cut\) =\s+{self.numberSearch} sec\. \({self.numberSearch} ticks\)"
        return self.apply_regex(regex, content_type="float", pos=0)

    def get_nodes(self):
        regex = rf"Solution time =\s+{self.numberSearch} sec\.\s+Iterations = {self.numberSearch}\s+Nodes = {self.numberSearch}"
        return self.apply_regex(regex, content_type="float", pos=2)

    def get_root_time(self):
        regex = rf"Root relaxation solution time = {self.numberSearch} sec\. \({self.numberSearch} ticks\)"
        return self.apply_regex(regex, pos=0, content_type="float")

    def get_cuts_time(self):
        regex = rf"Elapsed time = {self.numberSearch} sec\. \({self.numberSearch} ticks, tree = {self.numberSearch} MB, solutions = {self.numberSearch}\)"
        return self.apply_regex(regex, content_type="float", pos=0)

    def process_line(self, line):
        keys = ["n", "n_left", "obj", "iinf", "b_int", "b_bound", "ItCnt", "gap"]
        args = {k: self.numberSearch for k in keys}
        args["gap"] = f"({self.number}%)"

        if re.search(r"\*\s*\d+\+", line):
            args["obj"] = "()"
            args["ItCnt"] = "()"
            args["iinf"] = "()"

        # TODO: maybe include explicit optioms: Impl Bds, Cuts, ZeroHalf, Flowcuts,
        if re.search(r"[a-zA-Z\s]+: \d+", line):
            args["b_bound"] = r"([a-zA-Z\s]+: \d+)"

        get = re.search(r"\*?\s*\d+\+?\s*\d+\s*(infeasible|cutoff|integral)", line)
        if get is not None:
            state = get.group(1)
            args["obj"] = f"({state})"
            if state in ["integral"]:
                args["iinf"] = "(0)"
            else:
                args["iinf"] = "()"
            if state in ["cutoff", "infeasible"]:
                args["b_bound"] += "?"

        find = re.search(
            r"\s*{n}\s*{n_left}\s+{obj}\s+{iinf}?\s+{b_int}?\s+{b_bound}\s+{ItCnt}\s*{gap}?".format(
                **args
            ),
            line,
        )
        if not find:
            return None
        return find.groups()

    def get_progress(self):
        progress = super().get_progress()
        if progress:
            try:
                times = self.get_time_column()
            except TypeError:
                times = [None] * len(progress)
            for row, t in zip(progress, times):
                row.Time = t
        return progress

    def get_time_column(self) -> list[float]:
        """
        :return: list of Time values, one per progress row.
        """
        regex1 = self.progress_filter
        args = [self.numberSearch for l in range(4)]
        regex = (
            r"Elapsed time = {} sec. \({} ticks, tree = {} MB, solutions = {}\)".format(
                *args
            )
        )
        end_time = self.get_time()
        table_start_rx = r"\s*Node"
        table_start = False
        i = 0
        time = [(i, 0)]
        for l in self.content.split("\n"):
            if re.search(table_start_rx, l):
                table_start = True
            if not table_start:
                continue
            if re.search(regex1, l):
                i += 1
                continue
            result = re.search(regex, l)
            if not result:
                continue
            data = result.groups()
            time.append((i, float(data[0])))
        time.append((i, end_time))
        x, y = zip(*time)
        query = range(1, x[-1] + 1)
        return [round(v, 2) for v in self._linear_interp(query, x, y)]

    @staticmethod
    def _linear_interp(query_xs, xs, ys) -> list[float]:
        """
        Pure-Python equivalent of numpy.interp for this use case: xs is
        non-decreasing and every query point falls within [xs[0], xs[-1]],
        so no extrapolation handling is needed.
        """
        result = []
        j = 0
        n = len(xs)
        for x in query_xs:
            while j < n - 2 and xs[j + 1] < x:
                j += 1
            x0, x1 = xs[j], xs[j + 1]
            y0, y1 = ys[j], ys[j + 1]
            if x1 == x0:
                result.append(y1)
            else:
                result.append(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
        return result
