# /usr/bin/python3
import re
from collections.abc import Sequence
from dataclasses import dataclass

from .constants import (
    LpSolutionIntegerFeasible,
    LpSolutionNoSolutionFound,
    LpSolutionOptimal,
    solver_to_solution,
)


@dataclass
class MIPProgressRow:
    """
    One row of a MIP solver's branch-and-bound progress table.
    Shared by CBC (used directly), and by GUROBI/CPLEX/CPSAT (subclassed
    with extra solver-specific columns).
    """

    Node: int | None = None
    NodesLeft: int | None = None
    BestInteger: float | None = None
    CutsBestBound: float | str | None = None
    Time: float | None = None


_LEADING_NUMBER = re.compile(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
_INT_FIELDS = {"Node", "NodesLeft", "Depth", "IInf", "ItpNode"}
_FLOAT_FIELDS = {"BestInteger", "Gap", "Time"}
_FLOAT_OR_TEXT_FIELDS = {"Objective", "CutsBestBound"}


def _cast_progress_field(name: str, value: str | None):
    """
    Best-effort cast of a raw regex-captured progress cell.
    Numeric-only fields fall back to None when unparseable (never a guess);
    Objective/CutsBestBound keep the raw text when it's genuinely descriptive
    (e.g. "infeasible", "Cuts: 5") instead of losing it.
    """
    if value is None or value == "":
        # some solver regexes capture an intentionally-empty group (rather
        # than leaving the group unmatched) when a column has no value on a
        # given row — that's "nothing captured", not descriptive text.
        return None
    match = _LEADING_NUMBER.match(value)
    try:
        if name in _INT_FIELDS:
            return int(float(match.group(1))) if match else None
        if name in _FLOAT_FIELDS:
            return float(match.group(1)) if match else None
        if name in _FLOAT_OR_TEXT_FIELDS:
            return float(match.group(1)) if match else value
    except (TypeError, ValueError):
        return None
    return value


class LogFile:
    """
    This represents the log files that solvers return.
    We implement functions to get different information
    """

    name = None

    def __init__(self, path, **options):

        if options.get("content", False):
            content = path
        else:
            with open(path, "r") as f:
                content = f.read()

        self.path = path
        self.content = content
        self.number = r"-?[\de\.\+]+"
        self.numberSearch = rf"({self.number})"
        self.wordSearch = r"([\w, -]+)"

        self.solver_status_map = {}
        self.version_regex = ""
        self.progress_filter = ""
        self.progress_names = []
        self.progress_row_cls = MIPProgressRow
        self.options = options

    def apply_regex(
        self,
        regex,
        content_type: str | list[str] | None = None,
        first=True,
        pos=None,
        num=None,
        **kwargs,
    ):
        """
        regex is the regular expression to apply to the file contents.
        content_type are optional type casting for the results (int, float, str)
        if first is false, we take the raw output from the re.findall. Useful for progress table.
        num means, if there are multiple matches in re.findall, num tells which position to take out.
        if num=-1, we take the last one
        pos means the group we want to take out from all the groups of the relevant match.
        kwargs are additional parameters to the re.findall function
        :return: a list, a tuple or a single value with type "content_type"
        """
        solution = re.findall(regex, self.content, **kwargs)
        if solution is None:
            return None
        if not first:
            return solution
        if len(solution) == 0:
            return None
        if num is None:
            num = 0
        possible_tuple = solution[num]
        if type(possible_tuple) is str:
            # we force a tuple to deal with one string lists
            possible_tuple = (possible_tuple,)
            pos = 0
        func = {"float": float, "int": int, "str": str}
        if pos is not None:
            value = possible_tuple[pos]
            if isinstance(content_type, str) and content_type in func:
                return func[content_type](value)
            else:
                return possible_tuple[pos]
        if content_type is None:
            return possible_tuple
        if isinstance(content_type, list):
            # each one has its own type.
            # by default, we use strings
            ct = ["str" for r in possible_tuple]
            for i, _c in enumerate(content_type):
                if _c in func:
                    ct[i] = _c
            return [func[ct[i]](val) for i, val in enumerate(possible_tuple)]
        return [func[content_type](val) for val in possible_tuple]

    def get_first_relax(self, progress: Sequence[MIPProgressRow]) -> float | None:
        """
        scans the progress table for the initial relaxed solution
        :return: relaxation
        """
        for row in progress:
            if isinstance(row.CutsBestBound, float):
                return row.CutsBestBound
        return None

    def get_first_solution(self, progress: Sequence[MIPProgressRow]) -> dict | None:
        """
        scans the progress table for the initial integer solution
        :param progress: table with progress
        :return: dictionary with information on the moment of finding integer solution
        """
        for row in progress:
            # HACK: take out CBCs magic number (1e+50 for no integer solution found)
            if isinstance(row.BestInteger, float) and row.BestInteger != 1e50:
                return {
                    "Node": row.Node,
                    "NodesLeft": row.NodesLeft,
                    "BestInteger": row.BestInteger,
                    "CutsBestBound": (
                        row.CutsBestBound
                        if isinstance(row.CutsBestBound, float)
                        else None
                    ),
                }
        return None

    @staticmethod
    def get_results_after_cuts(progress: Sequence[MIPProgressRow]):
        """
        gets relaxed and integer solutions after the cuts phase has ended.
        :return: tuple of length two
        """
        matches = [
            row for row in progress if row.Node == 0 and row.NodesLeft in (0, 1, 2)
        ]

        # in case we have some progress after the cuts, we get those values
        # if not, we return None to later fill with best_solution and best_bound
        if not matches:
            return None, None
        last = matches[-1]
        sol_value = last.BestInteger
        relax_value = (
            last.CutsBestBound if isinstance(last.CutsBestBound, float) else None
        )

        return relax_value, sol_value

    def get_log_info(self) -> dict:
        """
        Main function that builds the general output for every solver
        :return: a dictionary
        """
        version = self.get_version()
        matrix = self.get_matrix_dict()
        matrix_post = self.get_matrix_dict(post=True)
        status, objective, bound, gap_rel = self.get_stats()
        solver_status, solution_status = self.get_status_codes(status, objective)
        if bound is None and solution_status == LpSolutionOptimal:
            bound = objective
        if solution_status == LpSolutionOptimal:
            gap_rel = 0
        presolve = self.get_lp_presolve()
        time_out = self.get_time()
        nodes = self.get_nodes()
        root_time = self.get_root_time()
        if self.options.get("get_progress", True):
            progress = self.get_progress()
        else:
            progress = []
        first_relax = first_solution = None
        cut_info = self.get_cuts_dict(progress, bound, objective)

        if len(progress):
            first_relax = self.get_first_relax(progress)
            if solution_status in [LpSolutionIntegerFeasible, LpSolutionOptimal]:
                first_solution = self.get_first_solution(progress)

        return {
            "version": version,
            "solver": self.name,
            "status": status,
            "best_bound": bound,
            "best_solution": objective,
            "gap": gap_rel,
            "time": time_out,
            "matrix_post": matrix_post,
            "matrix": matrix,
            "cut_info": cut_info,
            "rootTime": root_time,
            "presolve": presolve,
            "first_relaxed": first_relax,
            "progress": progress,
            "first_solution": first_solution,
            "status_code": solver_status,
            "sol_code": solution_status,
            "nodes": nodes,
        }

    def get_cuts_dict(
        self, progress: Sequence[MIPProgressRow], best_bound, best_solution
    ) -> dict | None:
        """
        builds a dictionary with all information regarding to the applied cuts
        :return: a dictionary
        """
        if not len(progress):
            return None
        cuts = self.get_cuts()
        if not cuts:
            # if no cuts were found, no cuts statistics are produced
            return {}
        cutsTime = self.get_cuts_time()
        after_cuts, sol_after_cuts = self.get_results_after_cuts(progress)
        if after_cuts is None:
            after_cuts = best_bound

        return {
            "time": cutsTime,
            "cuts": cuts,
            "best_bound": after_cuts,
            "best_solution": sol_after_cuts,
        }

    def get_matrix_dict(self, post=False) -> dict | None:
        """
        wrapper to both matrix parsers (before and after preprocess)
        :return: a dictionary with three elements or None
        """
        if post:
            matrix = self.get_matrix_post()
        else:
            matrix = self.get_matrix()

        if matrix is None:
            return None

        order = ["constraints", "variables", "nonzeros"]
        return {k: matrix[p] for p, k in enumerate(order)}

    def get_version(self) -> str:
        """
        gets the solver's version
        """
        return self.apply_regex(self.version_regex)

    def get_matrix(self) -> dict | None:
        return None

    def get_matrix_post(self) -> dict | None:
        return None

    def get_stats(self):
        return None, None, None, None

    def get_status_codes(self, status, obj) -> tuple[int | None, int | None]:
        """
        converts the status string into a solver code and a solution code
        to standardize the output among solvers
        :return: tuple of length 2
        """

        solver_status = self.solver_status_map.get(status)
        solution_status = solver_to_solution.get(solver_status)

        if obj is not None and solution_status == LpSolutionNoSolutionFound:
            solution_status = LpSolutionIntegerFeasible

        return solver_status, solution_status

    def get_cuts(self):
        return None

    def get_cuts_time(self) -> float | None:
        return None

    def get_lp_presolve(self) -> float | None:
        return None

    def get_time(self) -> float | None:
        return None

    def get_nodes(self) -> int | None:
        return None

    def get_root_time(self) -> float | None:
        return None

    def process_line(self, line):
        return None

    def get_progress(self) -> Sequence[MIPProgressRow]:
        """
        Parses the solver's branch-and-bound progress table into a list of
        typed row objects (see MIPProgressRow and its per-solver subclasses).
        Numeric columns are cast to int/float; a value that can't be trusted
        as a real number becomes None rather than a guess. Objective and
        CutsBestBound may instead hold a short descriptive string (e.g.
        "infeasible", "Cuts: 5") when the solver printed an annotation
        instead of a number on that row.
        :return: list of MIPProgressRow (or solver-specific subclass) instances
        """
        lines = self.apply_regex(self.progress_filter, first=False, flags=re.MULTILINE)
        processed = [self.process_line(line) for line in lines]
        processed_clean = [p for p in processed if p is not None]
        rows = []
        for p in processed_clean:
            kwargs = {
                name: _cast_progress_field(name, val)
                for name, val in zip(self.progress_names, p)
            }
            try:
                rows.append(self.progress_row_cls(**kwargs))
            except TypeError:
                # a line matched process_line's regex but produced a group
                # count/shape the row class doesn't expect (e.g. future solver
                # log format drift) — skip just this row rather than losing
                # the whole file's progress table.
                continue
        return rows


if __name__ == "__main__":
    pass
