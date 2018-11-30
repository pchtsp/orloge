# /usr/bin/python3
import re
import pandas as pd
import io
import numpy as np
import orloge.constants as c
import os


# TODO: get version of solver

def get_info_log_solver(path, solver):

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

    def get_progress_general(self, names, regex_filter):
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
        if len(table):
            table.columns = names
        return table

    def get_first_results(self, progress):
        first_solution = first_relax = None
        df_filter = progress.CutsBestBound.apply(lambda x: re.search(r"^\s*{}$".format(self.number), x) is not None)
        if len(df_filter) > 0 and any(df_filter):
            first_relax = float(progress.CutsBestBound[df_filter].iloc[0])

        df_filter = progress.BestInteger.str.match(r"^\s*{}$".format(self.number))
        if len(df_filter) > 0 and any(df_filter):
            first_solution = float(progress.BestInteger[df_filter].iloc[0])
        return first_relax, first_solution

    @staticmethod
    def get_results_after_cuts(progress):
        df_filter = np.all((progress.Node.str.match(r"^\*?H?\s*0"),
                            progress.NodesLeft.str.match(r"^\+?H?\s*[12]")),
                           axis=0)
        sol_value = relax_value = None
        if len(progress.BestInteger) > 0:
            sol_value = progress.BestInteger.iloc[-1]
        if len(progress.CutsBestBound) > 0:
            relax_value = progress.CutsBestBound.iloc[-1]

        sol_after_cuts = relax_after_cuts = None
        if np.any(df_filter):
            sol_value = progress.BestInteger[df_filter].iloc[0]
            relax_value = progress.CutsBestBound[df_filter].iloc[0]
        if sol_value and re.search(r'\s*\d', sol_value):
            sol_after_cuts = float(sol_value)
        if relax_value and re.search(r'\s*\d', relax_value):
            relax_after_cuts = float(relax_value)
        return relax_after_cuts, sol_after_cuts

    def get_log_info(self):
        cons, vars, nonzeroes = self.get_matrix()
        # cons, vars, nonzeroes = self.get_matrix_post()
        objective, bound, gap_rel = self.get_objective()
        status, sol_status = self.get_status()
        # bound, gap_abs, gap_rel = self.get_gap()
        if bound is None:
            bound = objective
        cuts = self.get_cuts()
        cutsTime = self.get_cuts_time()
        presolve = self.get_lp_presolve()
        time_out = self.get_time()
        rootTime = self.get_root_time()
        progress = self.get_progress()
        after_cuts = sol_after_cuts = None
        first_relax = first_solution = None
        if len(progress):
            after_cuts, sol_after_cuts = self.get_results_after_cuts(progress)
            first_relax, first_solution = self.get_first_results(progress)

        return {
            'status': status,
            'bound_out': bound,
            'objective_out': objective,
            'gap_out': gap_rel,
            'time_out': time_out,
            'cons': cons,
            'vars': vars,
            'nonzeros': nonzeroes,
            'cuts': cuts,
            'rootTime': rootTime,
            'cutsTime': cutsTime,
            'presolve': presolve,
            'first_relaxed': first_relax,
            'after_cuts': after_cuts,
            'progress': progress,
            'first_solution': first_solution,
            'sol_after_cuts': sol_after_cuts
        }

    @staticmethod
    def status_is_infeasible(status):
        return re.search('infeasible', status) is not None

    def get_matrix(self):
        return None, None, None

    def get_matrix_post(self):
        return None, None, None

    def get_objective(self):
        return None, None, None

    def get_status(self):
        return None, None

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

    def __init__(self, path):
        super().__init__(path)
        self.name = 'CPLEX'

    def get_objective(self):
        objective = self.get_best_solution()
        bound, gap_abs, gap_rel = self.get_gap()
        return objective, bound, gap_rel

    # Reference:
    # https://www.ibm.com/support/knowledgecenter/SSSA5P_12.6.3/ilog.odms.cplex.help/CPLEX/UsrMan/topics/discr_optim/mip/para/52_node_log.html
    def get_best_solution(self):
        """
        :return: tuple of length 2
        """

        regex = r'MIP\s+-\s+{1}(.*:\s+Objective\s+=\s+{0}\n)?'.format(self.numberSearch, self.wordSearch)
        result = self.apply_regex(regex, flags=re.MULTILINE)
        obj = None
        if result is not None:
            if result[2] != '':
                obj = float(result[2])
        return obj

    def get_status(self):
        # TODO: this
        solverstatusmap = {"MIP - Integer optimal": c.LpStatusSolved,
                           "MIP - Integer infeasible\.": c.LpStatusSolved,
                           "MIP - Time limit exceeded": c.LpStatusTimeLimit,
                           "MIP - Integer unbounded": c.LpStatusUnbounded,
                           "MIP - Integer infeasible or unbounded.": c.LpStatusInfeasible,
                           "CPLEX Error  1001: Out of memory\.": c.LpStatusMemoryLimit,
                           "No file read\.": c.LpStatusNotSolved,

                           #                       "" : Key.SolverStatusCodes.NodeLimit,
                           #                       "" : Key.SolverStatusCodes.Interrupted
                           }
        return None, None

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

        if line[0] in ['*']:
            args['obj'] = '(integral)'
            args['iinf'] = '()'

        if re.search(r'\*\s*\d+\+', line):
            args['obj'] = '()'
            args['ItCnt'] = '()'

        if re.search(r'Cuts: \d+', line):
            args['b_bound'] = r'(Cuts: \d+)'

        get = re.search(r'\*?\s*\d+\+?\s*\d+\s*(infeasible|cutoff|integral)', line)
        if get is not None:
            args['obj'] = '({})'.format(get.group(1))

        find = re.search(r'\s+{n}\s+{n_left}\s+{obj}\s+{iinf}?\s+{b_int}?\s+{b_bound}\s+{ItCnt}\s+{gap}?'. \
                         format(**args), line)
        if not find:
            #
            return None
        return find.groups()

    def get_progress(self):
        name_width = [('Node', 7), ('NodesLeft', 6), ('Objective', 14), ('IInf', 4), ('BestInteger', 11),
                      ('CutsBestBound', 11), ('Gap', 7), ('ItpNode', 6)]
        names = [k[0] for k in name_width]
        return self.get_progress_general(names, regex_filter = r'(^[\*H]?\s+\d.*$)')


class GUROBI(LogFile):

    def __init__(self, path):
        super().__init__(path)
        self.name = 'GUROBI'

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
        return self.get_progress_general(names, regex_filter = r'(^[\*H]?\s+\d.*$)')

    def get_matrix(self):
        regex = r'Optimize a model with {0} rows, {0} columns and {0} nonzeros'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = r'Presolved: {0} rows, {0} columns, {0} nonzeros'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_objective(self):
        regex = r'{1}( \(.*\))?\nBest objective ({0}|-), best bound ({0}|-), gap ({0}|-)'.\
            format(self.numberSearch,self.wordSearch)
        # content_type = ['', '', 'float', 'float', 'float']
        solution = self.apply_regex(regex)
        if solution is None:
            return None, None, None

        objective, bound, gap_rel = \
            [float(solution[pos]) if solution[pos] != '-' else None for pos in [2, 4, 6]]
        return objective, bound, gap_rel

    def get_status(self):
        # TODO: this
        solverstatusmap = {"(Optimal solution found|Solved with barrier)": c.LpStatusSolved,
                           "Model is infeasible$": c.LpStatusInfeasible,
                           "Model is infeasible or unbounded": c.LpStatusInfeasible,
                           "Time limit reached": c.LpStatusTimeLimit,
                           "^(ERROR 10001|Out of memory)": c.LpStatusMemoryLimit,
                           #                       "" : Key.SolverStatusCodes.NodeLimit,
                           #                       "" : Key.SolverStatusCodes.Interrupted
                           "^ERROR 10003": c.LpStatusNotSolved,
                           "^Model is unbounded": c.LpStatusUnbounded,
                           }
        return None, None

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

    def get_cuts(self):
        # TODO
        pass

    def get_progress(self):
        names = ['Node', 'NodesLeft', 'BestInteger', 'CutsBestBound', 'Time']
        return self.get_progress_general(names, regex_filter=r'(^Cbc0010I.*$)')

    def get_matrix(self):
        regex = r'Problem MODEL has {0} rows, {0} columns and {0} elements'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_matrix_post(self):
        regex = r'Cgl0004I processed model has {0} rows, {0} columns \(\d+ integer ' \
                r'\(\d+ of which binary\)\) and {0} elements'.format(self.numberSearch)
        return self.apply_regex(regex, content_type="int")

    def get_version(self):
        pass
        # version_expr = re.compile("^Version: (\S+)")

    def get_status(self):
        # TODO: this
        solverstatusmap = {"Result - Optimal solution found": c.LpStatusSolved,
                           'Problem is infeasible': c.LpStatusInfeasible,
                           "Result - Stopped on time limit": c.LpStatusTimeLimit,
                           "Result - Problem proven infeasible": c.LpStatusInfeasible,
                           "Problem is unbounded": c.LpStatusUnbounded,
                           "Pre-processing says infeasible or unbounded": c.LpStatusInfeasible,
                           "\*\* Current model not valid": c.LpStatusNotSolved
                           }
        regex = 'Result - {}'.format(self.wordSearch)
        status = self.apply_regex(regex, pos=0)
        if status is None:
            if self.apply_regex('Problem is infeasible'):
                status = 'Problem is infeasible'
                return status, None
        return None, None

    def get_objective(self):

        regex = r'best objective {0}( \(best possible {0}\))?, took {1} iterations and {1} nodes \({1} seconds\)'.\
            format(self.numberSearch, self.number)
        solution = self.apply_regex(regex)

        if solution is None:
            return None, None, None

        objective = float(solution[0])
        if solution[2] is None or solution[2] == '':
            bound = objective
        else:
            bound = float(solution[2])

        gap_rel = abs(objective - bound) / objective * 100

        return objective, bound, gap_rel

    def get_cuts_time(self):
        # TODO
        return None

    def get_lp_presolve(self):
        # TODO
        return None

    def get_time(self):
        regex = r'Time \(Wallclock seconds\):\s*{}'.format(self.numberSearch)
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
    import pprint as pp
    import package.params as pm
    route = '/home/pchtsp/Documents/projects/OPTIMA_documents/results/experiments/'
    # path = '/home/pchtsp/Documents/projects/OPTIMA_documents/results/experiments/201801102259/results.log'
    # path = '/home/pchtsp/Documents/projects/OPTIMA_documents/results/experiments/201801141334/results.log'
    # path = '/home/pchtsp/Documents/projects/OPTIMA_documents/results/experiments/201801131817/results.log'
    # path = "/home/pchtsp/Documents/projects/OPTIMA_documents/results/experiments/201801141331/results.log"
    exps = ['201801102259', '201801141334', '201801131817', '201801141331']

    exps = ['201801141705']
    # exps = ['201801102259']
    # for e in exps:
    #     path = os.path.join(route, e, 'results.log')
    #     log = LogFile(path)
    #     result = log.get_log_info_cplex()
    #     pp.pprint(result)
    #
    # re.search(r"\s*\d", result.CutsBestBound[1])
    # cplex tests
    path = pm.PATHS['results'] + 'hp_20181025/task_periods_minusage_pricerutend_respertask_1_90_0_0_15/201810252139/results.log'
    path = pm.PATHS['results'] + 'hp_20181025/task_periods_minusage_pricerutend_respertask_1_90_0_1_15/201810260322/results.log'
    path = pm.PATHS['results'] + 'clust1_20181024/task_periods_minusage_pricerutend_respertask_1_60_20_1_15/201810261129/results.log'
    # log = CPLEX(path)

    # gurobi tests
    path = pm.PATHS['results'] + 'clust1_20181112/base/201811140123/results.log'
    # path = pm.PATHS['results'] + 'clust1_20181112/maxusedtime_800/201811130631_1/results.log'
    # path = pm.PATHS['results'] + 'clust1_20181112/maxusedtime_800/201811130130/results.log'
    # log = GUROBI(path)

    # cbc tests
    path = pm.PATHS['results'] + 'hp_20181114/base/201811180430/results.log'
    # path = '/home/pchtsp/Dropbox/OPTIMA_results/hp_20181025/task_periods_minusage_pricerutend_respertask_1_90_0_0_15/201810252139_1/results.log'
    # info = log.get_log_info_cplex()
    log = CBC(path)

    info = log.get_log_info()
    info['status']
    # status, objective = log.get_objective()