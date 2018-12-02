import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import orloge as ol
import orloge.constants as c

DATADIR = os.path.join(os.path.dirname(__file__), "data")
ALMOST_KEYS = ['best_solution', 'best_bound']

class SolverTest(unittest.TestCase):

    fileinfo = {
                "cbc298-app1-2": {
                    'solver': "CBC",
                    'version': '2.9.8',
                    'time': 7132.49,
                    'nodes': 31867,
                    'status_code': c.LpStatusTimeLimit,
                    'sol_code': c.LpSolutionNoSolutionFound,
                    'best_solution': None,
                    'best_bound': -96.111},
                "cbc298-ash608gpia-3col": {
                    'solver': "CBC",
                    'time': 224.71,
                    'nodes': 0,
                    'status_code': c.LpStatusInfeasible,
                    'sol_code': c.LpSolutionInfeasible,
                    'matrix': {
                        'constraints': 24748,
                        'variables': 3651,
                        'nonzeros': 74244
                    },
                    'matrix_post': {
                        'constraints': 18352,
                        'variables': 3651,
                        'nonzeros': 58254
                    },
                    'best_solution': None,
                    'best_bound': None},
                "cbc298-bab5": {
                    'solver': "CBC",
                    'time': 7194.79,
                    'nodes': 162253,
                    'status_code': c.LpStatusTimeLimit,
                    'sol_code': c.LpSolutionIntegerFeasible,
                    'best_solution':-104286.921,
                    'best_bound':-111273.306},
                "cbc298-dfn-gwin-UUM": {
                    'solver': "CBC",
                    'time': 725.37,
                    'nodes': 378472,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': 38752,
                    'best_bound': 38752},
                "cbc298-enlight14": {
                    'solver': "CBC",
                    'time': 7131.16,
                    'nodes': 762406,
                    'status_code': c.LpStatusTimeLimit,
                    'sol_code': c.LpSolutionNoSolutionFound,
                    'best_solution': None,
                    'best_bound': 36.768},
                "cbc298-satellites1-25": {
                    'solver': "CBC",
                    'time': 4511.76,
                    'nodes': 51033,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution':-5,
                    'best_bound':-5},
                "cplex1271-app1-2": {
                    'solver': "CPLEX",
                    'version': '12.7.1.0',
                    'nodes': 1415,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution':-41,
                    'best_bound':-41},
                "cplex1271-bab5": {
                    'solver': "CPLEX",
                    'nodes': 101234,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution':-106411.84,
                    'best_bound':-106411.84},
                "cplex1271-dfn-gwin-UUM": {
                    'solver': "CPLEX",
                    'nodes': 16132,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': 38752,
                    'best_bound': 38752},
                "cplex1271-enlight14": {
                    'solver': "CPLEX",
                    'nodes': 0,
                    'status_code': c.LpStatusInfeasible,
                    'best_solution': None,
                    'best_bound': None},
                "cplex1271-satellites1-25": {
                    'solver': "CPLEX",
                    'nodes': 2942,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution':-5,
                    'best_bound':-5},
                "cplex1280-bab5": {
                    'solver': "CPLEX",
                    'time': 1551.53,
                    'nodes': 51737,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': -1.0641184010e+05,
                    'best_bound': -1.0641184010e+05},
                "cplex1280-enlight13": {
                    'solver': "CPLEX",
                    'time': 0.00,
                    'nodes': 0,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': 7.1000000000e+01,
                    'best_bound': 7.1000000000e+01},
                "cplex1280-enlight14": {
                    'solver': "CPLEX",
                    'time': 0.00,
                    'nodes': 0,
                    'status_code': c.LpStatusInfeasible,
                    'best_solution': None,
                    'best_bound': None},
                "cplex1280-mine-90-10": {
                    'solver': "CPLEX",
                    'time': 924.71,
                    'nodes': 388227,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': -7.8430233763e+08,
                    'best_bound': -7.8430233763e+08},
                "cplex1280-rmine6": {
                    'solver': "CPLEX",
                    'time': 1437.13,
                    'nodes': 540816,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution':-4.5718614000e+02,
                    'best_bound':-4.5718614070e+02 },
                "cplex1280-satellites1-25": {
                    'solver': "CPLEX",
                    'time': 216.80,
                    'nodes': 3896,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'matrix': {
                        'constraints': 4658,
                        'variables': 7759,
                        'nonzeros': 50343
                    },
                    'matrix_post': {
                        'constraints': 4214,
                        'variables': 7088,
                        'nonzeros': 45547
                    },
                    'cut_info': {
                        'cuts': {
                            'GUB cover': 2
                            , 'Clique': 7
                            , 'Cover': 5
                            , 'Implied bound': 21
                            , 'Flow': 5
                            , 'Mixed integer rounding': 19
                            , 'Zero-half': 18
                            , 'Gomory fractional': 2
                        },
                        'time': 4.42,
                        'best_bound': -20,
                        'best_solution': 45
                    },
                    'best_solution': -5.0000000000e+00,
                    'best_bound': -5.0000000000e+00},
                "cplex1280-tanglegram2": {
                    'solver': "CPLEX",
                    'time': 0.98,
                    'nodes': 3,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': 4.4300000000e+02,
                    'best_bound': 4.4300000000e+02},
                "gurobi700-app1-2": {
                    'solver': "GUROBI",
                    'time': 46.67,
                    'nodes': 526,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'matrix': {
                        'constraints': 53467,
                        'variables': 26871,
                        'nonzeros': 199175
                    },
                    'matrix_post': {
                        'constraints': 35616,
                        'variables': 22010,
                        'nonzeros': 149085
                    },
                    'best_solution':-41,
                    'best_bound':-41},
                "gurobi700-bab5": {
                    'solver': "GUROBI",
                    'time': 65.35,
                    'nodes': 534,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution':-106411.84,
                    'best_bound':-106411.84},
                "gurobi700-dfn-gwin-UUM": {
                    'solver': "GUROBI",
                    'time': 388.98,
                    'nodes': 170061,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': 38752,
                    'best_bound': 38752},
                "gurobi700-enlight14": {
                    'solver': "GUROBI",
                    'time': 0.00,
                    'nodes': 0,
                    'status_code': c.LpStatusInfeasible,
                    'best_solution': None,
                    'best_bound': None},
                "gurobi700-satellites1-25": {
                    'solver': "GUROBI",
                    'time': 59.70,
                    'nodes': 1170,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution':-5,
                    'best_bound':-5},
                "gurobi800-bab5": {
                    'solver': "GUROBI",
                    'time': 25.52,
                    'nodes': 1,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': -1.064118401000e+05,
                    'best_bound': -1.064118401000e+05},
                "gurobi800-enlight13": {
                    'solver': "GUROBI",
                    'time': 0.00,
                    'nodes': 0,
                    'status_code': c.LpStatusSolved,
                    'sol_code': c.LpSolutionOptimal,
                    'best_solution': 7.100000000000e+01,
                    'best_bound': 7.100000000000e+01},
                "gurobi800-enlight14": {
                    'solver': "GUROBI",
                    'time': 0.00,
                    'nodes': 0,
                    'status_code': c.LpStatusInfeasible,
                    'best_solution': None,
                    'best_bound': None},
                "gurobi800-mine-90-10": {
                    'solver': "GUROBI",
                    'time': 769.45,
                    'nodes': 1181932,
                    'status_code': c.LpStatusSolved,
                    'best_solution': -7.843023376332e+08,
                    'best_bound': -7.843023376332e+08},
                "gurobi800-satellites1-25": {
                    'solver': "GUROBI",
                    'time': 40.86,
                    'nodes': 380,
                    'status_code': c.LpStatusSolved,
                    'best_solution': -5.000000000000e+00,
                    'best_bound': -5.000000000000e+00},
                "gurobi800-tanglegram2": {
                    'solver': "GUROBI",
                    'time': 0.57,
                    'nodes': 1,
                    'status_code': c.LpStatusSolved,
                    'matrix': {
                        'constraints': 8980,
                        'variables': 4714,
                        'nonzeros': 26940
                    },
                    'matrix_post': {
                        'constraints': 7976,
                        'variables': 4058,
                        'nonzeros': 23928
                    },
                    'cut_info': {
                        'cuts': {'Zero half': 5},
                        'time': 0,
                        'best_bound': 443,
                        'best_solution': 443
                    },
                    'best_solution': 4.430000000000e+02,
                    'best_bound': 4.430000000000e+02},
                # "xpress300103-app1-2": {
                #     'solver': "XPRESS",
                #     'time': 29,
                #     'nodes': 265,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':-41,
                #     'best_bound':-41},
                # "xpress300103-bab5": {
                #     'solver': "XPRESS",
                #     'time': 7200,
                #     'nodes': 71853,
                #     'status_code': c.LpStatusTimeLimit,
                #     'best_solution':-106411.84,
                #     'best_bound':-106701.8161},
                # "xpress300103-dfn-gwin-UUM": {
                #     'solver': "XPRESS",
                #     'time':181,
                #     'nodes': 158849,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': 38752,
                #     'best_bound': 38748},
                # "xpress300103-enlight14": {
                #     'solver': "XPRESS",
                #     'time': 0,
                #     'nodes': 0,
                #     'status_code': c.LpStatusInfeasible,
                #     'best_solution': 1e+40,
                #     'best_bound': 1e+40},
                # "xpress300103-satellites1-25": {
                #     'solver': "XPRESS",
                #     'time': 228,
                #     'nodes': 5937,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':-5,
                #     'best_bound':-5},
                # "xpress330103-bab5": {
                #     'solver': "XPRESS",
                #     'time': 7200,
                #     'nodes': 24575,
                #     'status_code': c.LpStatusTimeLimit,
                #     'best_solution': -106361.339104,
                #     'best_bound': -106600.8564439218171173707},
                # "xpress330103-enlight13": {
                #     'solver': "XPRESS",
                #     'time': 0,
                #     'nodes': 0,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': 71,
                #     'best_bound': 71},
                # "xpress330103-enlight14": {
                #     'solver': "XPRESS",
                #     'time': 84,
                #     'nodes': 1,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': 52200,
                #     'best_bound': 52200.00000000001455191523},
                # "xpress330103-mine-90-10": {
                #     'solver': "XPRESS",
                #     'time': 5,
                #     'nodes': 505,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': -566395707.871,
                #     'best_bound': -566395707.8708435297012329},
                # "xpress330103-satellites1-25": {
                #     'solver': "XPRESS",
                #     'time': 99,
                #     'nodes': 7917,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': -5.00000000001,
                #     'best_bound': -5.000000000005489830812166},
                # "xpress330103-tanglegram2": {
                #     'solver': "XPRESS",
                #     'time': 0,
                #     'nodes': 5,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': 443,
                #     'best_bound': 443},
                # "mipcl131-app1-2": {
                #     'solver': "MIPCL",
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':-41,
                #     'best_bound':-41},
                # "mipcl131-bab5": {
                #     'solver': "MIPCL",
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':-106411.84,
                #     'best_bound':-106411.84},
                # "mipcl131-dfn-gwin-UUM": {
                #     'solver': "MIPCL",
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': 38752,
                #     'best_bound': 38752},
                # "mipcl131-enlight14": {
                #     'solver': "MIPCL",
                #     'status_code': c.LpStatusInfeasible,
                #     'best_solution': None,
                #     'best_bound': None},
                # "mipcl131-satellites1-25": {
                #     'solver': "MIPCL",
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':-5,
                #     'best_bound':-5},
                # "mipcl152-bab5": {
                #     'solver': "MIPCL",
                #     'time': 514.635,
                #     'nodes': 264,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': -106411.8401,
                #     'best_bound': -106411.8401},
                # "mipcl152-bnatt350": {
                #     'solver': "MIPCL",
                #     'time': 7199.330,
                #     'nodes': 117400,
                #     'status_code': c.LpStatusTimeLimit,
                #     'best_solution': None,
                #     'best_bound': -0.0000},
                # "mipcl152-enlight13": {
                #     'solver': "MIPCL",
                #     'time': 70.477,
                #     'nodes': 280,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': 71.0000,
                #     'best_bound': 71.0000},
                # "mipcl152-enlight14": {
                #     'solver': "MIPCL",
                #     'time': 280.405,
                #     'nodes': 1025,
                #     'status_code': c.LpStatusInfeasible,
                #     'best_solution': None,
                #     'best_bound': None},
                # "mipcl152-mine-90-10": {
                #     'solver': "MIPCL",
                #     'time': 7.370,
                #     'nodes': 1930,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': -566395707.8708,
                #     'best_bound': -566395707.8708},
                # "mipcl152-satellites1-25": {
                #     'solver': "MIPCL",
                #     'time': 2999.199,
                #     'nodes': 14031,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': -5.0000,
                #     'best_bound': -5.0000},
                # "mipcl152-tanglegram2": {
                #     'solver': "MIPCL",
                #     'time': 35.829,
                #     'nodes': 1,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution': 443.0000,
                #     'best_bound': 443.0000},
                # "scip400-infeasible": {
                #     'solver': "SCIP",
                #     'nodes': 1,
                #     'time': 0.02,
                #     Key.GitHash: "ea0b6dd",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "3.0.0",
                #     "SpxGitHash": "b0cccbd",
                #     'status_code': c.LpStatusInfeasible,
                #     'best_solution':+1.00000000000000e+20,
                #     'best_bound':+1.00000000000000e+20},
                # "scip400-memorylimit": {
                #     'solver': "SCIP",
                #     'nodes': 1778883,
                #     'time': 6807.85,
                #     Key.GitHash: "ea0b6dd",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "3.0.0",
                #     "SpxGitHash": "b0cccbd",
                #     'status_code': c.LpStatusMemoryLimit,
                #     'best_solution':+1.49321500000000e+06,
                #     'best_bound':+1.49059347656250e+06},
                # "scip400-optimal": {
                #     'solver': "SCIP",
                #     'nodes': 126,
                #     'time': 0.79,
                #     Key.GitHash: "dd19a7b",
                #     "mode": "optimized",
                #     "LPSolver": "CPLEX",
                #     "LPSolverVersion": "12.6.0.0",
                #     "SpxGitHash": None,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':+3.36000000000000e+03,
                #     'best_bound':+3.36000000000000e+03},
                # "scip400-timelimit": {
                #     'solver': "SCIP",
                #     'nodes': 101678,
                #     'time': 600.00,
                #     Key.GitHash: "dd19a7b",
                #     "mode": "optimized",
                #     "LPSolver": "CPLEX",
                #     "LPSolverVersion": "12.6.0.0",
                #     "SpxGitHash": None,
                #     'status_code': c.LpStatusTimeLimit,
                #     'best_solution':+1.16800000000000e+03,
                #     'best_bound':+1.13970859166290e+03},
                # "scip400-crashed": {
                #     'solver': "SCIP",
                #     'nodes': None,
                #     'time': None,
                #     Key.GitHash: "dd19a7b",
                #     "mode": "optimized",
                #     "LPSolver": "CPLEX",
                #     "LPSolverVersion": "12.6.0.0",
                #     "SpxGitHash": None,
                #     'status_code': Key.SolverStatusCodes.Crashed,
                #     'best_solution': None,
                #     'best_bound': None},
                # "scip500-bab5": {
                #     'solver': "SCIP",
                #     'time': 7200.00,
                #     'nodes': 120255,
                #     Key.GitHash: "3bbd232",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "3.1.0",
                #     "SpxGitHash": "5147d37",
                #     'status_code': c.LpStatusTimeLimit,
                #     'best_solution':-1.06411840100000e+05,
                #     'best_bound':-1.06736016607273e+05},
                # "scip500-enlight13": {
                #     'solver': "SCIP",
                #     'time': 0.01,
                #     'nodes': 1,
                #     Key.GitHash: "3bbd232",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "3.1.0",
                #     "SpxGitHash": "5147d37",
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':+7.10000000000000e+01,
                #     'best_bound':+7.10000000000000e+01},
                # "scip500-enlight14": {
                #     'solver': "SCIP",
                #     'time': 0.01,
                #     'nodes': 1,
                #     Key.GitHash: "3bbd232",
                #     "mode": "optimized",
                #     "LPSolver": "CPLEX",
                #     "LPSolverVersion": "12.8.0.0",
                #     "SpxGitHash": None,
                #     'status_code': c.LpStatusInfeasible,
                #     'best_solution':+1.00000000000000e+20,
                #     'best_bound':+1.00000000000000e+20},
                # "scip500-mine-90-10": {
                #     'solver': "SCIP",
                #     'time': 45.86,
                #     'nodes': 1483,
                #     Key.GitHash: "3bbd232",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "3.1.0",
                #     "SpxGitHash": "5147d37",
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':-5.66395707870830e+08,
                #     'best_bound':-5.66395707870830e+08},
                # "scip500-satellites1-25": {
                #     'solver': "SCIP",
                #     'time': 454.56,
                #     'nodes': 424,
                #     Key.GitHash: "3bbd232",
                #     "mode": "optimized",
                #     "LPSolver": "CPLEX",
                #     "LPSolverVersion": "12.8.0.0",
                #     "SpxGitHash": None,
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':-4.99999999999994e+00,
                #     'best_bound':-4.99999999999994e+00},
                # "scip500-tanglegram2": {
                #     'solver': "SCIP",
                #     'time': 5.82,
                #     'nodes': 3,
                #     Key.GitHash: "3bbd232",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "3.1.0",
                #     "SpxGitHash": "5147d37",
                #     'status_code': c.LpStatusSolved,
                #     'best_solution':+4.43000000000000e+02,
                #     'best_bound':+4.43000000000000e+02},
                # "scip501-in-memlim": {
                #     'solver': "SCIP",
                #     'time': 63.27,
                #     'nodes': 0,
                #     Key.GitHash: "b1c222a",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "3.1.1",
                #     "SpxGitHash": "ab921a5",
                #     'status_code': c.LpStatusMemoryLimit,
                #     'best_solution': 1e+20,
                #     'best_bound': None},
                # "scip600-in-memlim": {
                #     'solver': "SCIP",
                #     'time': 70.67,
                #     'nodes': 1,
                #     Key.GitHash: "ce154f0",
                #     "mode": "optimized",
                #     "LPSolver": "SoPlex",
                #     "LPSolverVersion": "4.0.0",
                #     "SpxGitHash": "e0d3842",
                #     'status_code': c.LpStatusMemoryLimit,
                #     'best_solution': 1e+20,
                #     'best_bound': 13.0},
                }

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testData(self):
        for filename, contents in self.fileinfo.items():
            file = self.getFileName(filename)
            solver = contents['solver']
            data = ol.logFiles.get_info_solver(file, solver)
            for key, value in contents.items():
                if key not in data:
                    print("not checking: {} in {}".format(key, filename))
                    continue
                msg = "{0} has {1} as {2}, should be {3}". format(filename, data[key], key, value)
                if key in ALMOST_KEYS:
                    self.assertAlmostEqual(data[key], value, delta = 1e-1, msg=msg)
                else:
                     self.assertEqual(data[key], value, msg=msg)

    def getFileName(self, basename):
        return os.path.join(DATADIR, "{}.{}".format(basename, "out"))

if __name__ == "__main__":
    unittest.main()

