# /usr/bin/python3
import re
import pandas as pd
import numpy as np
from .constants import (
    LpSolutionOptimal,
    LpSolutionIntegerFeasible,
    LpSolutionNoSolutionFound,
    solver_to_solution,
)


class LogFile(object):
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
        self.numberSearch = r"({})".format(self.number)
        self.wordSearch = r"([\w, -]+)"

        self.solver_status_map = {}
        self.version_regex = ""
        self.progress_filter = ""
        self.progress_names = []
        self.options = options

    def apply_regex(
        self, regex, content_type=None, first=True, pos=None, num=None, **kwargs
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
            if content_type in func:
                return func[content_type](value)
            else:
                return possible_tuple[pos]
        if content_type is None:
            return possible_tuple
        if type(content_type) is not list:
            return [func[content_type](val) for val in possible_tuple]
        else:
            # each one has its own type.
            # by default, we use strings
            ct = ["str" for r in possible_tuple]
            for i, _c in enumerate(content_type):
                if _c in func:
                    ct[i] = _c
            return [func[ct[i]](val) for i, val in enumerate(possible_tuple)]

    def get_first_relax(self, progress) -> float | None:
        """
        scans the progress table for the initial relaxed solution
        :return: relaxation
        """
        bestBounds = progress.CutsBestBound[~progress.CutsBestBound.isna()]

        df_filter = bestBounds.apply(
            lambda x: re.search(r"^\s*{}$".format(self.number), x) is not None
        )
        if len(df_filter) > 0 and any(df_filter):
            return float(bestBounds[df_filter].iloc[0])
        return None

    def get_first_solution(self, progress):
        """
        scans the progress table for the initial integer solution
        :param progress: table with progress
        :return: dictionary with information on the moment of finding integer solution
        """
        vars_extract = ["Node", "NodesLeft", "BestInteger", "CutsBestBound"]
        df_filter = progress.BestInteger.fillna("").str.match(
            r"^\s*{}$".format(self.number)
        )
        # HACK: take out CBCs magic number (1e+50 for no integer solution found)
        df_filter_1e50 = progress.BestInteger.fillna("").str.match(r"^\s*1e\+50$")
        df_filter = np.all([df_filter, ~df_filter_1e50], axis=0)
        if len(df_filter) > 0 and any(df_filter):
            for col in vars_extract:
                floatSearch = r"[+-]?[\d]+(\.[\d]+)?([Ee][+-]?[\d]+)?"
                regex = "^({}).*$".format(floatSearch)
                progress[col] = progress[col].str.extract(regex)[[0]]
                # progress[col] = progress[col].str.replace('(?!{})'.format(self.number), '')
            return pd.to_numeric(progress[vars_extract][df_filter].iloc[0]).to_dict()
        return None

    @staticmethod
    def get_results_after_cuts(progress):
        """
        gets relaxed and integer solutions after the cuts phase has ended.
        :return: tuple of length two
        """
        df_filter = np.all(
            (
                progress.Node.str.match(r"^\*?H?\s*0"),
                progress.NodesLeft.str.match(r"^\+?H?\s*[012]"),
            ),
            axis=0,
        )

        # in case we have some progress after the cuts, we get those values
        # if not, we return None to later fill with best_solution and best_bound
        if not np.any(df_filter):
            return None, None
        sol_value = progress.BestInteger[df_filter].iloc[-1]
        relax_value = progress.CutsBestBound[df_filter].iloc[-1]

        # finally, we return the found values
        if sol_value and re.search(r"^\s*-?\d", sol_value):
            sol_value = float(sol_value)
        if relax_value and re.search(r"^\s*-?\d", relax_value):
            relax_value = float(relax_value)
        else:
            relax_value = None

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
            progress = pd.DataFrame()
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

    def get_cuts_dict(self, progress, best_bound, best_solution) -> dict:
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

    def get_matrix_dict(self, post=False) -> dict:
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

    def get_status_codes(self, status, obj) -> tuple[int, int]:
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

    def get_root_time(self) -> float:
        return None

    def process_line(self, line):
        return None

    def get_progress(self) -> pd.DataFrame:
        """
        :return: pandas dataframe with 8 columns
        """
        lines = self.apply_regex(self.progress_filter, first=False, flags=re.MULTILINE)
        processed = [self.process_line(line) for line in lines]
        processed_clean = [p for p in processed if p is not None]
        progress = pd.DataFrame(processed_clean)
        if len(progress):
            progress.columns = self.progress_names
        return progress


if __name__ == "__main__":
    pass
