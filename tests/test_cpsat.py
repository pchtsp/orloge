import unittest
import os
import sys
from cpsat_log_parser.tests.test_examples import EXAMPLE_DIR
import orloge.constants as c
from test_mips import SolverTest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class CPSAT_Test(SolverTest):

    fileinfo = {
        "93_01": {
            "solver": "CPSAT",
            "version": "v9.3.10497",
            "time": 3.5908,
            "nodes": 0,
            "status_code": c.LpStatusSolved,
            "sol_code": c.LpSolutionOptimal,
            "best_solution": 15,
            "best_bound": 15,
            "status": "OPTIMAL",
        }
    }

    @staticmethod
    def getFileName(basename):
        return os.path.join(EXAMPLE_DIR, "{}.{}".format(basename, "txt"))


if __name__ == "__main__":
    unittest.main()
