# /usr/bin/python3
import re
import pandas as pd
import numpy as np
import orloge.constants as c

def get_info_solver(path, solver):

    if solver=='CPLEX':
        log = CPLEX(path)
    elif solver=='GUROBI':
        log = GUROBI(path)
    elif solver=='CBC':
        log = CBC(path)
    else:
        raise ValueError('solver {} is not recognized'.format(solver))
    return log.get_log_info()


class LogFile(object):
    """
    This represents the log files that solvers return.
    We implement functions to get different information
    """

    def __init__(self, path):
        with open(path, 'r') as f:
            content = f.read()

        self.content = content
        self.number = r'-?[\de\.\+]+'
        self.numberSearch = r'({})'.format(self.number)
        self.wordSearch = r'([\w, ]+)'
        self.name = None
        self.solver_status_map = {}
        self.version_regex = ''

    def apply_regex(self, regex, content_type=None, first=True, pos=None, num=None, **kwargs):
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
            for i, c in enumerate(content_type):
                if c in func:
                    ct[i] = c
            return [func[ct[i]](val) for i, val in enumerate(possible_tuple)]

    def get_progress_general(self, regex_filter):
        """
        :return: pandas dataframe with 8 columns
        """
        # before we clean the rest of lines:
        # names, widths = zip(*name_width)
        # length_start = sum(widths)

        lines = self.apply_regex(regex_filter, first=False, flags=re.MULTILINE)
        processed = [self.process_line(line) for line in lines]
        processed_clean = [p for p in processed if p is not None]
        table = pd.DataFrame(processed_clean)
        return table

    def get_first_results(self, progress):
        first_solution = first_relax = None
        df_filter = progress.CutsBestBound.apply(lambda x: re.search(r"^\s*{}$".format(self.number), x) is not None)
        if len(df_filter) > 0 and any(df_filter):
            first_relax = float(progress.CutsBestBound[df_filter].iloc[0])

        df_filter = progress.BestInteger.fillna('').str.match(r"^\s*{}$".format(self.number))
        if len(df_filter) > 0 and any(df_filter):
            first_solution = float(progress.BestInteger[df_filter].iloc[0])
        return first_relax, first_solution

    @staticmethod
    def get_results_after_cuts(progress):
        df_filter = np.all((progress.Node.str.match(r"^\*?H?\s*0"),
                            progress.NodesLeft.str.match(r"^\+?H?\s*[12]")),
                           axis=0)
        sol_value = relax_value = None

        # we initialize with the last values:
        if len(progress.BestInteger) > 0:
            sol_value = progress.BestInteger.iloc[-1]
        if len(progress.CutsBestBound) > 0:
            relax_value = progress.CutsBestBound.iloc[-1]

        # in case we have progress after cuts, we replace those defaults
        if np.any(df_filter):
            sol_value = progress.BestInteger[df_filter].iloc[0]
            relax_value = progress.CutsBestBound[df_filter].iloc[0]

        # finally, in either case, we return the found values
        if sol_value and re.search(r'^\s*-?\d', sol_value):
            sol_value = float(sol_value)
        if relax_value and re.search(r'^\s*-?\d', relax_value):
            relax_value = float(relax_value)

        return relax_value, sol_value

    def get_log_info(self):
        version = self.get_version()
        matrix = self.get_matrix_dict()
        matrix_post = self.get_matrix_dict(post=True)
        status, objective, bound, gap_rel = self.get_stats()
        solver_status, solution_status = self.get_status_codes(status, objective)
        if bound is None:
            bound = objective
        presolve = self.get_lp_presolve()
        time_out = self.get_time()
        rootTime = self.get_root_time()
        progress = self.get_progress()
        first_relax = first_solution = None
        cut_info = self.get_cuts_dict(progress)
        if len(progress):
            first_relax, first_solution = self.get_first_results(progress)

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
            'rootTime': rootTime,
            'presolve': presolve,
            'first_relaxed': first_relax,
            'progress': progress,
            'first_solution': first_solution,
            'status_code': solver_status,
            'sol_code': solution_status
        }

    def get_cuts_dict(self, progress):
        if not len(progress):
            return None
        cutsTime = self.get_cuts_time()
        cuts = self.get_cuts()
        after_cuts = sol_after_cuts = None
        if len(progress):
            after_cuts, sol_after_cuts = self.get_results_after_cuts(progress)
        return {'time': cutsTime,
                'cuts': cuts,
                'relax': after_cuts,
                'solution': sol_after_cuts
                }

    def get_matrix_dict(self, post=False):
        if post:
            cons, vars, nonzeroes = self.get_matrix_post()
        else:
            cons, vars, nonzeroes = self.get_matrix()
        return {'constraints': cons,
                'variables': vars,
                'nonzeros': nonzeroes}


    def get_version(self):
        return self.apply_regex(self.version_regex)

    def get_matrix(self):
        return None, None, None

    def get_matrix_post(self):
        return None, None, None

    def get_stats(self):
        return None, None, None, None

    def get_status_codes(self, status, obj):

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

    def get_root_time(self):
        return None

    def process_line(self, line):
        return None

    def get_progress(self):
        return pd.DataFrame()


class CPLEX(LogFile):
    # Reference:
    # https://www.ibm.com/support/knowledgecenter/SSSA5P_12.6.3/ilog.odms.cplex.help/CPLEX/UsrMan/topics/discr_optim/mip/para/52_node_log.html

    def __init__(self, path):
        super().__init__(path)
        self.name = 'CPLEX'
        self.solver_status_map = {
            "MIP - Integer optimal": c.LpStatusSolved,
            "MIP - Integer infeasible.": c.LpStatusInfeasible,
            "MIP - Time limit exceeded": c.LpStatusTimeLimit,
            "MIP - Integer unbounded": c.LpStatusUnbounded,
            "MIP - Integer infeasible or unbounded": c.LpStatusInfeasible,
            "CPLEX Error  1001: Out of memory": c.LpStatusMemoryLimit,
            "No file read": c.LpStatusNotSolved
        }

        self.version_regex = "^Welcome to IBM\(R\) ILOG\(R\) CPLEX\(R\) Interactive Optimizer (\S+)"

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
                # return status, None, None, None

    def get_objective(self):
        """
        :return: tuple of length 2
        """
        regex = r'Objective\s+=\s+{0}\n'.format(self.numberSearch)
        result = self.apply_regex(regex, flags=re.MULTILINE)
        if result is not None:
            result = float(result)
        return result

    def get_gap(self):
        """
        :return: tuple of length 3: bound, absolute gap, relative gap
        """
        regex = r'Current MIP best bound =  {0} \(gap = {0}, {0}%\)'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type='float')
        if result is None:
            return None, None, None
        return result

    def get_matrix(self):
        """
        :return: tuple of length 3
        """
        regex = r'Reduced MIP has {0} rows, {0} columns, and {0} nonzeros'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type="int", num=-1)
        if result is None:
            return None, None, None
        return result

    def get_matrix_post(self):
        """
        :return: tuple of length 3
        """
        regex = r'Reduced MIP has {0} rows, {0} columns, and {0} nonzeros'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type="int", num=-1)
        if result is None:
            return None, None, None
        return result

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

        if re.search('\*\s*\d+\+', line):
            args['obj'] = '()'
            args['ItCnt'] = '()'
            args['iinf'] = '()'

        if re.search('Cuts: \d+', line):
            args['b_bound'] = '(Cuts: \d+)'

        get = re.search('\*?\s*\d+\+?\s*\d+\s*(infeasible|cutoff)', line)
        if get is not None:
            args['obj'] = '({})'.format(get.group(1))
            args['iinf'] = '()'

        get = re.search('\*?\s*\d+\+?\s*\d+\s*(integral)', line)
        if get is not None:
            args['obj'] = '(integral)'
            args['iinf'] = '(0)'


        find = re.search('\s+{n}\s+{n_left}\s+{obj}\s+{iinf}?\s+{b_int}?\s+{b_bound}\s+{ItCnt}\s+{gap}?'. \
                         format(**args), line)
        if not find:
            return None
        return find.groups()

    def get_progress(self):
        name_width = [('Node', 7), ('NodesLeft', 6), ('Objective', 14), ('IInf', 4), ('BestInteger', 11),
                      ('CutsBestBound', 11), ('ItpNode', 6), ('Gap', 7)]
        names = [k[0] for k in name_width]
        progress = self.get_progress_general(regex_filter = r'(^[\*H]?\s+\d.*$)')
        if len(progress):
            progress.columns = names
        return progress


class GUROBI(LogFile):

    def __init__(self, path):
        super().__init__(path)
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
        self.version_regex = "Gurobi Optimizer version (\S+)"

    def get_cuts(self):
        regex = r'Cutting planes:([\n\s\w:]+)Explored'  # gurobi
        result = self.apply_regex(regex, flags=re.MULTILINE)
        cuts = [r for r in result.split('\n') if r != '']
        regex = r'\s*{}: {}'.format(self.wordSearch, self.numberSearch)
        searches = [re.search(regex, v) for v in cuts]
        return {s.group(1): s.group(2) for s in searches if s is not None and s.lastindex >= 2}

    def get_progress(self):
        name_width = [('Node', 7), ('NodesLeft', 6), ('Objective', 14), ('Depth', 2), ('IInf', 4), ('BestInteger', 11),
                      ('CutsBestBound', 11), ('Gap', 7), ('ItpNode', 6), ('Time', 6)]
        names = [k[0] for k in name_width]
        progress = self.get_progress_general(regex_filter = r'(^[\*H]?\s+\d.*$)')
        if len(progress):
            progress.columns = names
        return progress

    def get_matrix(self):
        regex = r'Optimize a model with {0} rows, {0} columns and {0} nonzeros'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = r'Presolved: {0} rows, {0} columns, {0} nonzeros'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type="int")
        if result is None:
            return (None for i in range(3))
        return result

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
        df_filter = np.all((progress.Node.str.match(r"^\*?H?\s*0"),
                            progress.NodesLeft.str.match(r"^\+?H?\s*2")),
                           axis=0)
        if not len(df_filter) or not any(df_filter):
            return None

        content = progress.Time[df_filter].iloc[0]
        number = re.search(self.numberSearch, content).group(1)
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
        stats = re.findall(regex, self.content)
        time_out = None
        if stats:
            time_out = float(stats[0][2])
        return time_out

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
            args['obj'] = '({})'.format(get.group(1))

        find = re.search(r'\s+{n}\s+{n_left}\s+{obj}\s+{depth}\s+{iinf}?\s+{b_int}?-?'
                         r'\s+{b_bound}\s+{gap}?-?\s+{ItCnt}?-?\s+{time}'. \
                         format(**args), line)
        if not find:
            return None
        return find.groups()


class CBC(LogFile):

    def __init__(self, path):
        super().__init__(path)
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
        self.version_regex = "^Version: (\S+)"

    def get_cuts(self):
        # TODO
        pass

    def get_progress(self):
        names = ['Node', 'NodesLeft', 'BestInteger', 'CutsBestBound', 'Time']
        progress = self.get_progress_general(regex_filter=r'(^Cbc0010I.*$)')
        if len(progress):
            progress.columns = names
        return progress

    def get_matrix(self):
        regex = r'Problem .+ has {0} rows, {0} columns and {0} elements'.format(self.numberSearch)
        result = self.apply_regex(regex, content_type="int")
        if result is None:
            return (None for i in range(3))
        return result

    def get_matrix_post(self):
        regex = r'Cgl0004I processed model has {0} rows, {0} columns \(\d+ integer ' \
                r'\(\d+ of which binary\)\) and {0} elements'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_version(self):
        pass
        # version_expr = re.compile("^Version: (\S+)")

    def get_stats(self):

        regex = 'Result - {}'.format(self.wordSearch)
        status = self.apply_regex(regex, pos=0)
        if status is None:
            # no solution found, I still want the status
            for k in self.solver_status_map.keys():
                search_string = re.escape(k)
                if self.apply_regex(search_string):
                    status = search_string
                    return status, None, None, None
        regex = 'best objective {0}( \(best possible {0}\))?, took {1} iterations and {1} nodes \({1} seconds\)'.\
            format(self.numberSearch, self.number)
        solution = self.apply_regex(regex)

        if solution is None:
            return None, None, None, None

        if solution[0] == '1e+50':
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

    def get_root_time(self):
        # TODO
        return None

    def process_line(self, line):

        keys = ['n', 'n_left', 'b_int', 'b_bound', 'time']
        args = {k: self.numberSearch for k in keys}
        find = re.search(r'Cbc0010I After {n} nodes, {n_left} on tree, {b_int} best solution, '
                         r'best possible {b_bound} \({time} seconds\)'. \
                         format(**args), line)
        if not find:
            return None
        return find.groups()


if __name__ == "__main__":

    pass