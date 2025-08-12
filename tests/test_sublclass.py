import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import orloge as ol
import orloge.constants as c

DATADIR = os.path.join(os.path.dirname(__file__), "data")
ALMOST_KEYS = ["best_solution", "best_bound"]


class SolverTest(unittest.TestCase):
    def test_new_log(self):
        class MyLog(ol.LogFile):
            def __init__(self, path, **options):
                super().__init__(path, **options)
                self.name = "my_solver"

            def get_stats(self):
                # get status, objective, bound, gap_rel
                return None, None, None, None

            def get_status_codes(self, status, objective):
                # get status codes of the solver and solution
                return None, None

            def get_version(self):
                # implement some logic to parse the version
                return ""

            def get_progress(self):
                # implement some logic to parse the progress and return a pandas DataFrame
                import pandas as pd

                return pd.DataFrame()

        my_log = MyLog(path="PATH_TO_MY_LOG_FILE")
        my_log.get_log_info()


if __name__ == "__main__":
    unittest.main()
