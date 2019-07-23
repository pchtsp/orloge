# /usr/bin/python3
import re
import pandas as pd
import numpy as np
import orloge.constants as c

def get_info_solver(path, solver, **options):

    if solver == 'CPLEX':
        log = CPLEX(path, **options)
    elif solver == 'GUROBI':
        log = GUROBI(path, **options)
    elif solver == 'CBC':
        log = CBC(path, **options)
    else:
        raise ValueError('solver {} is not recognized'.format(solver))
    return log.get_log_info()


class LogFile(object):
    """
    This represents the log files that solvers return.
    We implement functions to get different information
    """

    def __init__(self, path, **options):
        with open(path, 'r') as f:
            content = f.read()

        self.path  = path
        self.content = content
        self.number = r'-?[\de\.\+]+'
        self.numberSearch = r'({})'.format(self.number)
        self.wordSearch = r'([\w, -]+)'
        self.name = None
        self.solver_status_map = {}
        self.version_regex = ''
        self.progress_filter = ''
        self.progress_names = []
        self.options = options

    def apply_regex(self, regex, content_type=None, first=True, pos=None, num=None, **kwargs):
        """
        regex is the regular expression to apply to the file contents.
        content_type are optional type casting for the results (int, float, str)
        if first is false, we take the raw output from the re.findall. Useful for progress table.
        num means, if there are multiple matches in re.findall, num tells which position to take out.
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
            possible_tuple = (possible_tuple, )
            pos = 0
        func = {
            'float': float,
            'int': int,
            'str': str
        }
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
            # by default we use strings
            ct = ['str' for r in possible_tuple]
            for i, _c in enumerate(content_type):
                if _c in func:
                    ct[i] = _c
            return [func[ct[i]](val) for i, val in enumerate(possible_tuple)]

    def get_first_relax(self, progress):
        """
        scans the progress table for the initial relaxed solution
        :return: relaxation
        """
        df_filter = progress.CutsBestBound.apply(lambda x: re.search(r"^\s*{}$".format(self.number), x) is not None)
        if len(df_filter) > 0 and any(df_filter):
            return float(progress.CutsBestBound[df_filter].iloc[0])
        return None

    def get_first_solution(self, progress):
        """
        scans the progress table for the initial integer solution
        :param progress: table with progress
        :return: dictionary with information on the moment of finding integer solution
        """
        vars_extract = ['Node', 'NodesLeft', 'BestInteger', 'CutsBestBound']
        df_filter = progress.BestInteger.fillna('').str.match(r"^\s*{}$".format(self.number))
        # HACK: take out CBCs magic number (1e+50 for no integer solution found)
        df_filter_1e50 = progress.BestInteger.fillna('').str.match(r"^\s*1e\+50$")
        df_filter = np.all([df_filter, ~df_filter_1e50], axis=0)
        if len(df_filter) > 0 and any(df_filter):
            for col in vars_extract:
                progress[col] = progress[col].str.replace(r'\D', '')
            return pd.to_numeric(progress[vars_extract][df_filter].iloc[0]).to_dict()
        return None

    @staticmethod
    def get_results_after_cuts(progress):
        """
        gets relaxed and integer solutions after the cuts phase has ended.
        :return: tuple of length two
        """
        # we initialize with the last values in the progress table:
        # sol_value = progress.BestInteger.iloc[-1]
        # relax_value = progress.CutsBestBound.iloc[-1]
        df_filter = np.all((progress.Node.str.match(r"^\*?H?\s*0"),
                            progress.NodesLeft.str.match(r"^\+?H?\s*[12]")),
                           axis=0)

        # in case we have some progress after the cuts, we get those values
        # if not, we return None to later fill with best_solution and best_bound
        if not np.any(df_filter):
            return None, None
        sol_value = progress.BestInteger[df_filter].iloc[0]
        relax_value = progress.CutsBestBound[df_filter].iloc[0]

        # finally, we return the found values
        if sol_value and re.search(r'^\s*-?\d', sol_value):
            sol_value = float(sol_value)
        if relax_value and re.search(r'^\s*-?\d', relax_value):
            relax_value = float(relax_value)

        return relax_value, sol_value

    def get_log_info(self):
        """
        Main function that builds the general output for every solver
        :return: a dictionary
        """
        version = self.get_version()
        matrix = self.get_matrix_dict()
        matrix_post = self.get_matrix_dict(post=True)
        status, objective, bound, gap_rel = self.get_stats()
        solver_status, solution_status = self.get_status_codes(status, objective)
        if bound is None:
            bound = objective
        if solution_status == c.LpSolutionOptimal:
            gap_rel = 0
        presolve = self.get_lp_presolve()
        time_out = self.get_time()
        nodes = self.get_nodes()
        root_time = self.get_root_time()
        if self.options.get('get_progress', True):
            progress = self.get_progress()
        else:
            progress = pd.DataFrame()
        first_relax = first_solution = None
        cut_info = self.get_cuts_dict(progress, bound, objective)

        if len(progress):
            first_relax = self.get_first_relax(progress)
            if solution_status in [c.LpSolutionIntegerFeasible, c.LpSolutionOptimal]:
                first_solution = self.get_first_solution(progress)

        return {
            'version': version,
            'solver': self.name,
            'status': status,
            'best_bound': bound,
            'best_solution': objective,
            'gap': gap_rel,
            'time': time_out,
            'matrix_post': matrix_post,
            'matrix': matrix,
            'cut_info': cut_info,
            'rootTime': root_time,
            'presolve': presolve,
            'first_relaxed': first_relax,
            'progress': progress,
            'first_solution': first_solution,
            'status_code': solver_status,
            'sol_code': solution_status,
            'nodes': nodes
        }

    def get_cuts_dict(self, progress, best_bound, best_solution):
        """
        builds a dictionary with all information regarding to the applied cuts
        :return: a dictionary
        """
        if not len(progress):
            return None
        cutsTime = self.get_cuts_time()
        cuts = self.get_cuts()
        after_cuts, sol_after_cuts = self.get_results_after_cuts(progress)
        if after_cuts is None:
            after_cuts = best_bound
        if sol_after_cuts is None:
            sol_after_cuts = best_solution

        return {'time': cutsTime,
                'cuts': cuts,
                'best_bound': after_cuts,
                'best_solution': sol_after_cuts
                }

    def get_matrix_dict(self, post=False):
        """
        wrapper to both matrix parsers (before and after the preprocess)
        :return: a dictionary with three elements or None
        """
        if post:
            matrix = self.get_matrix_post()
        else:
            matrix = self.get_matrix()

        if matrix is None:
            return None

        order = ['constraints', 'variables', 'nonzeros']
        return {k: matrix[p] for p, k in enumerate(order)}

    def get_version(self):
        """
        gets the solver's version
        """
        return self.apply_regex(self.version_regex)

    def get_matrix(self):
        return None

    def get_matrix_post(self):
        return None

    def get_stats(self):
        return None, None, None, None

    def get_status_codes(self, status, obj):
        """
        converts the status string into a solver code and a solution code
        to standardize the output among solvers
        :return: tuple of length 2
        """

        solver_status = self.solver_status_map.get(status)
        solution_status = c.solver_to_solution.get(solver_status)

        if obj is not None and solution_status == c.LpSolutionNoSolutionFound:
            solution_status = c.LpSolutionIntegerFeasible

        return solver_status, solution_status

    def get_cuts(self):
        return None

    def get_cuts_time(self):
        return None

    def get_lp_presolve(self):
        return None

    def get_time(self):
        return None

    def get_nodes(self):
        return None

    def get_root_time(self):
        return None

    def process_line(self, line):
        return None

    def get_progress(self):
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


class CPLEX(LogFile):
    # Reference:
    # https://www.ibm.com/support/knowledgecenter/SSSA5P_12.6.3/ilog.odms.cplex.help/CPLEX/UsrMan/topics/discr_optim/mip/para/52_node_log.html

    def __init__(self, path, **options):
        super().__init__(path, **options)
        self.name = 'CPLEX'
        self.solver_status_map = {
            'MIP - Memory limit exceeded': c.LpStatusMemoryLimit,
            "MIP - Integer optimal": c.LpStatusSolved,
            "MIP - Integer infeasible.": c.LpStatusInfeasible,
            "MIP - Time limit exceeded": c.LpStatusTimeLimit,
            "MIP - Integer unbounded": c.LpStatusUnbounded,
            "MIP - Integer infeasible or unbounded": c.LpStatusInfeasible,
            "CPLEX Error  1001: Out of memory": c.LpStatusMemoryLimit,
            "No file read": c.LpStatusNotSolved
        }

        self.version_regex = r"Welcome to IBM\(R\) ILOG\(R\) CPLEX\(R\) Interactive Optimizer (\S+)"
        self.progress_names = ['Node', 'NodesLeft', 'Objective', 'IInf',
                               'BestInteger', 'CutsBestBound', 'ItpNode', 'Gap']
        self.progress_filter = r'(^[\*H]?\s+\d.*$)'

    def get_stats(self):
        status = self.get_status()
        objective = self.get_objective()
        bound, gap_abs, gap_rel = self.get_gap()
        return status, objective, bound, gap_rel

    def get_status(self):
        for k in self.solver_status_map.keys():
            search_string = re.escape(k)
            if self.apply_regex(search_string):
                return k

    def get_objective(self):
        """
        :return: tuple of length 2
        """
        regex = r'Objective\s+=\s+{0}\s*\n'.format(self.numberSearch)
        result = self.apply_regex(regex, flags=re.MULTILINE)
        if result is not None:
            result = float(result)
        return result

    def get_gap(self):
        """
        :return: tuple of length 3: bound, absolute gap, relative gap
        """
        regex = r'Current MIP best bound =\s+{0} \(gap = {0}, {0}%\)'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type='float')
        if result is None:
            return None, None, None
        return result

    def get_matrix(self):
        """
        :return: tuple of length 3
        """
        # TODO: this is not correctly calculated: we need to sum the change to the initial to get
        # the original.
        regex = r'Reduced MIP has {0} rows, {0} columns, and {0} nonzeros'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int", num=0)

    def get_matrix_post(self):
        """
        :return: tuple of length 3
        """
        regex = r'Reduced MIP has {0} rows, {0} columns, and {0} nonzeros'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int", num=-1)

    def get_cuts(self):
        """
        :return: dictionary of cuts
        """
        regex = r'{1} cuts applied:  {0}'.format(self.numberSearch, self.wordSearch)
        result = self.apply_regex(regex, first=False)
        if result is None:
            return None
        return {k[0]: int(k[1]) for k in result}

    def get_lp_presolve(self):
        """
        :return: tuple  of length 3
        """
        # TODO: this is not correctly calculated:
        # we need to sum the two? preprocessings in my cases
        regex = r'Presolve time = {0} sec. \({0} ticks\)'.format(self.numberSearch)
        time = self.apply_regex(regex, pos=0, content_type="float")

        regex = r'LP Presolve eliminated {0} rows and {0} columns'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type="int")
        if result is None:
            result = None, None
        return {'time': time, 'rows': result[0], 'cols': result[1]}

    def get_time(self):
        regex = r'Solution time =\s+{0} sec\.\s+Iterations = {0}\s+Nodes = {0}'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="float", pos=0)

    def get_nodes(self):
        regex = r'Solution time =\s+{0} sec\.\s+Iterations = {0}\s+Nodes = {0}'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="float", pos=2)

    def get_root_time(self):
        regex = r'Root relaxation solution time = {0} sec\. \({0} ticks\)'.format(self.numberSearch)
        return self.apply_regex(regex, pos=0, content_type="float")

    def get_cuts_time(self):
        regex = r'Elapsed time = {0} sec\. \({0} ticks, tree = {0} MB, solutions = {0}\)'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="float", pos=0)

    def process_line(self, line):
        keys = ['n', 'n_left', 'obj', 'iinf', 'b_int', 'b_bound', 'ItCnt', 'gap']
        args = {k: self.numberSearch for k in keys}
        args['gap'] = '({}%)'.format(self.number)

        if re.search(r'\*\s*\d+\+', line):
            args['obj'] = '()'
            args['ItCnt'] = '()'
            args['iinf'] = '()'

        if re.search(r'Cuts: \d+', line):
            args['b_bound'] = r'(Cuts: \d+)'

        get = re.search(r'\*?\s*\d+\+?\s*\d+\s*(infeasible|cutoff|integral)', line)
        if get is not None:
            state = get.group(1)
            args['obj'] = '({})'.format(state)
            if state in ['integral']:
                args['iinf'] = '(0)'
            else:
                args['iinf'] = '()'

        find = re.search(r'\s+{n}\s+{n_left}\s+{obj}\s+{iinf}?\s+{b_int}?\s+{b_bound}\s+{ItCnt}\s+{gap}?'.
                         format(**args), line)
        if not find:
            return None
        return find.groups()


class GUROBI(LogFile):

    def __init__(self, path, **options):
        super().__init__(path, **options)
        self.name = 'GUROBI'
        self.solver_status_map =  \
            {"Optimal solution found": c.LpStatusSolved,
             'Solved with barrier': c.LpStatusSolved,
             "Model is infeasible": c.LpStatusInfeasible,
             "Model is infeasible or unbounded": c.LpStatusInfeasible,
             "Time limit reached": c.LpStatusTimeLimit,
             "Out of memory": c.LpStatusMemoryLimit,
             'ERROR 10001': c.LpStatusMemoryLimit,
             "ERROR 10003": c.LpStatusNotSolved,
             "^Model is unbounded": c.LpStatusUnbounded,
             }
        self.version_regex = r"Gurobi Optimizer version (\S+)"
        self.progress_names = ['Node', 'NodesLeft', 'Objective', 'Depth', 'IInf',
                               'BestInteger', 'CutsBestBound', 'Gap', 'ItpNode', 'Time']
        self.progress_filter = r'(^[\*H]?\s+\d.*$)'

    def get_cuts(self):
        regex = r'Cutting planes:([\n\s\-\w:]+)Explored'
        result = self.apply_regex(regex, flags=re.MULTILINE)
        cuts = [r for r in result.split('\n') if r != '']
        regex = r'\s*{}: {}'.format(self.wordSearch, self.numberSearch)
        searches = [re.search(regex, v) for v in cuts]
        return {s.group(1): int(s.group(2)) for s in searches if s is not None and s.lastindex >= 2}

    def get_matrix(self):
        regex = r'Optimize a model with {0} rows, {0} columns and {0} nonzeros'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = r'Presolved: {0} rows, {0} columns, {0} nonzeros'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_stats(self):
        regex = r'{1}( \(.*\))?\nBest objective ({0}|-), best bound ({0}|-), gap ({0}|-)'.\
            format(self.numberSearch,self.wordSearch)
        # content_type = ['', '', 'float', 'float', 'float']
        solution = self.apply_regex(regex)
        if solution is None:
            return None, None, None, None

        status = solution[0]
        objective, bound, gap_rel = \
            [float(solution[pos]) if solution[pos] != '-' else None for pos in [2, 4, 6]]
        return status, objective, bound, gap_rel

    def get_cuts_time(self):
        progress = self.get_progress()
        if not len(progress):
            return None
        df_filter = np.all((progress.Node.str.match(r"^\*?H?\s*0"),
                            progress.NodesLeft.str.match(r"^\+?H?\s*2")),
                           axis=0)

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
        regex = r'Presolve time: {0}s'.format(self.numberSearch)
        time = self.apply_regex(regex, pos=0, content_type="float")
        if time is None:
            time = None
        regex = r'Presolve removed {0} rows and {0} columns'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type="int")
        if result is None:
            result = None, None
        return {'time': time, 'rows': result[0], 'cols': result[1]}

    def get_time(self):
        regex = r"Explored {0} nodes \({0} simplex iterations\) in {0} seconds".format(self.numberSearch)
        return self.apply_regex(regex, content_type='float', pos=2)

    def get_nodes(self):
        regex = r"Explored {0} nodes \({0} simplex iterations\) in {0} seconds".format(self.numberSearch)
        return self.apply_regex(regex, content_type="float", pos=0)

    def get_root_time(self):
        regex = r'Root relaxation: objective {0}, {0} iterations, {0} seconds'.format(self.numberSearch)
        return self.apply_regex(regex, pos=2, content_type="float")

    def process_line(self, line):
        keys = ['n', 'n_left', 'obj', 'iinf', 'b_int', 'b_bound', 'ItCnt', 'gap', 'depth', 'time']
        args = {k: self.numberSearch for k in keys}
        args['gap'] = '({}%)'.format(self.number)
        args['time'] = '({}s)'.format(self.number)

        if line[0] in ['*', 'H']:
            args['obj'] = '()'
            args['iinf'] = '()'
            args['depth'] = '()'

        if re.search(r'\*\s*\d+\+', line):
            args['obj'] = '()'
            args['ItCnt'] = '()'

        if re.search(r'Cuts: \d+', line):
            args['b_bound'] = r'(Cuts: \d+)'

        get = re.search(r'\*?\s*\d+\+?\s*\d+\s*(infeasible|cutoff|integral)', line)
        if get is not None:
            state = get.group(1)
            args['obj'] = '({})'.format(state)
            if state in ['integral']:
                pass
            else:
                args['iinf'] = '()'

        find = re.search(r'\s+{n}\s+{n_left}\s+{obj}\s+{depth}\s+{iinf}?\s+{b_int}?-?'
                         r'\s+{b_bound}\s+{gap}?-?\s+{ItCnt}?-?\s+{time}'.
                         format(**args), line)
        if not find:
            return None
        return find.groups()


class CBC(LogFile):

    def __init__(self, path, **options):
        super().__init__(path, **options)
        self.name = 'CBC'
        self.solver_status_map = {
            "Optimal solution found": c.LpStatusSolved,
            'Problem is infeasible': c.LpStatusInfeasible,
            "Stopped on time limit": c.LpStatusTimeLimit,
            "Problem proven infeasible": c.LpStatusInfeasible,
            "Problem is unbounded": c.LpStatusUnbounded,
            "Pre-processing says infeasible or unbounded": c.LpStatusInfeasible,
            "** Current model not valid": c.LpStatusNotSolved
        }
        self.version_regex = r"Version: (\S+)"
        self.progress_names = ['Node', 'NodesLeft', 'BestInteger', 'CutsBestBound', 'Time']
        self.progress_filter = r'(^Cbc0010I.*$)'

    def get_cuts(self):
        # TODO
        pass

    def get_matrix(self):
        regex = r'Problem .+ has {0} rows, {0} columns and {0} elements'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = r'Cgl0004I processed model has {0} rows, {0} columns \(\d+ integer ' \
                r'\(\d+ of which binary\)\) and {0} elements'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_stats(self):

        regex = 'Result - {}'.format(self.wordSearch)
        status = self.apply_regex(regex, pos=0)
        if status is None:
            # no solution found, I still want the status
            for k in self.solver_status_map.keys():
                if self.apply_regex(re.escape(k)):
                    return k, None, None, None
        else:
            status = status.strip()
        regex = r'best objective {0}( \(best possible {0}\))?, took {1} iterations and {1} nodes \({1} seconds\)'.\
            format(self.numberSearch, self.number)
        solution = self.apply_regex(regex)

        if solution is None:
            return None, None, None, None

        # if solution[0] == '1e+050':
        if self.apply_regex('No feasible solution found'):
            objective = None
        else:
            objective = float(solution[0])

        if solution[2] is None or solution[2] == '':
            bound = objective
        else:
            bound = float(solution[2])

        gap_rel = None
        if objective is not None:
            gap_rel = abs(objective - bound) / objective * 100

        return status, objective, bound, gap_rel

    def get_cuts_time(self):
        # TODO
        return None

    def get_lp_presolve(self):
        # TODO
        return None

    def get_time(self):
        regex = r'Total time \(CPU seconds\):\s*{}'.format(self.numberSearch)
        stats = self.apply_regex(regex, content_type='float', pos=0)
        return stats

    def get_nodes(self):
        regex = r"Enumerated nodes:\s*{}".format(self.numberSearch)
        return self.apply_regex(regex, content_type="int", pos=0)

    def get_root_time(self):
        # TODO
        return None

    def process_line(self, line):

        keys = ['n', 'n_left', 'b_int', 'b_bound', 'time']
        args = {k: self.numberSearch for k in keys}
        find = re.search(r'Cbc0010I After {n} nodes, {n_left} on tree, {b_int} best solution, '
                         r'best possible {b_bound} \({time} seconds\)'.
                         format(**args), line)
        if not find:
            return None
        return find.groups()


if __name__ == "__main__":

    pass
