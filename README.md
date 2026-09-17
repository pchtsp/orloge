## Orloge
[![PyPI version](https://badge.fury.io/py/orloge.svg)](https://badge.fury.io/py/orloge)
![Repo Size](https://img.shields.io/github/repo-size/pchtsp/orloge)
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)
[![Repo Status](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


## What and why

The idea of this project is to permit a fast and easy parsing of the log files from different solvers, specifically 'operations research' (OR) logs.

There exist bigger, and more robust libraries. In particular, [IPET](https://github.com/GregorCH/ipet/). The trouble I had was that it deals with too many benchmarking and GUI things and I wanted something simple I could modify and build on top.

In any case, a lot of the ideas and parsing strings were obtained or adapted from IPET, to whom I am graceful.

The supported solvers for the time being are: GUROBI, CPLEX and CBC. Specially the two first ones.

## How

The basic idea is just to provide a unique interface function like the following:

    import orloge as ol
    ol.get_info_solver(path_to_solver_log, solver_name)

This returns a python dictionary with a lot of information from the log (see *Examples* below).

## Installation

    pip install orloge

or, for the development version:

    pip install https://github.com/pchtsp/orloge/archive/master.zip

## Testing

Run the command 
    
     python3 -m unittest tests.SolverTest

 if the output says OK, all tests were passed.

## Reference

### Main parameters

The most common parameters to extract are: `best_bound`, `best_solution` and `time`. These three parameters are obtained at the end of the solving process and summarize the best relaxed objective value obtained, the best integer objective value obtained and the time it took to do the solving.

### Cuts

The cuts information can be accessed by the `cuts_info` key. It offers the best known bound after the cut phase has ended, the best solution (if any) after the cuts and the number of cuts made of each type.

### Matrix

There are two matrices that are provided. The `matrix` key returns the number of variables, constraints and non-zero values before the pre-processing of the solver. The `matrix_post` key returns these same values after the pre-processing has been done.

### Progress

The `progress` key returns a list of dataclass instances, one per row of the progress table the solver printed while solving. Each row carries the time, gap, best bound, best solution, iterations, nodes, among other columns. The set of columns can vary between solvers, but the names are normalized so the same name always means the same thing: CBC rows are `MIPProgressRow`, GUROBI rows are `GUROBIProgressRow`, and CPLEX rows are `CPLEXProgressRow` (both subclass `MIPProgressRow`, adding their own extra columns); CPSAT rows are the unrelated `CPSATProgressRow`. Numeric columns are parsed to `int`/`float` and become `None` when a value can't be trusted as a real number — except `Objective` and `CutsBestBound`, which can instead hold a short status string (e.g. `"infeasible"`, `"cutoff"`, `"Cuts: 5"`) when the solver printed an annotation instead of a number on that row.

### Status

The status is given in several ways. First, a raw string extraction is returned in `status`. Then, a normalized one using codes is given via `sol_code` and `status_code` keys. `sol_code` gives information about the quality of the solution obtained. `status_code` gives details about the status of the solver after finishing (mainly, the reason it stopped).

### Other

There is also information about the pre-solving phase, the first bound and the first solution. Also, there's information about the time it took to solve the root node.

## Examples

    import orloge as ol
    ol.get_info_solver('tests/data/cbc298-app1-2.out', 'CBC')

Would produce the following:

    {'best_bound': -96.111283,
     'best_solution': None,
     'cut_info': {},
     'first_relaxed': -210.09571,
     'first_solution': None,
     'gap': None,
     'matrix': {'constraints': 53467, 'nonzeros': 199175, 'variables': 26871},
     'matrix_post': {'constraints': 26555, 'nonzeros': 195875, 'variables': 13265},
     'nodes': 31867,
     'presolve': None,
     'progress': [MIPProgressRow(Node=0, NodesLeft=1, BestInteger=1e+50, CutsBestBound=-210.09571, Time=32.83),
                  MIPProgressRow(Node=100, NodesLeft=11, BestInteger=1e+50, CutsBestBound=-210.09571, Time=124.49),
                  ...
                  # 319 rows total
                  ],
     'rootTime': None,
     'sol_code': 0,
     'solver': 'CBC',
     'status': 'Stopped on time limit',
     'status_code': -4,
     'time': 7132.49,
     'version': '2.9.8'}

And another example, this time using GUROBI:

    import orloge as ol
    ol.get_info_solver('tests/data/gurobi700-app1-2.out', 'GUROBI')

Creates the following output:

    {'best_bound': -41.0,
     'best_solution': -41.0,
     'cut_info': {'best_bound': -167.97894,
                  'best_solution': -41.0,
                  'cuts': {'Clique': 1,
                           'Gomory': 16,
                           'Implied bound': 23,
                           'MIR': 22},
                  'time': 21.0},
     'first_relaxed': -178.94318,
     'first_solution': {'Node': 0, 'NodesLeft': 0, 'BestInteger': -41.0, 'CutsBestBound': -178.94318},
     'gap': 0,
     'matrix': {'constraints': 53467, 'nonzeros': 199175, 'variables': 26871},
     'matrix_post': {'constraints': 35616, 'nonzeros': 149085, 'variables': 22010},
     'nodes': 526.0,
     'presolve': {'cols': 4861, 'rows': 17851, 'time': 3.4},
     'progress': [GUROBIProgressRow(Node=0, NodesLeft=0, BestInteger=-41.0, CutsBestBound=-178.94318, Time=4.0,
                                     Objective=-178.94318, Depth=0, IInf=282, Gap=336.0, ItpNode=None),
                  GUROBIProgressRow(Node=0, NodesLeft=0, BestInteger=-41.0, CutsBestBound=-171.91701, Time=15.0,
                                     Objective=-171.91701, Depth=0, IInf=268, Gap=319.0, ItpNode=None),
                  ...
                  # 26 rows total
                  ],
     'rootTime': 0.7,
     'sol_code': 1,
     'solver': 'GUROBI',
     'status': 'Optimal solution found',
     'status_code': 1,
     'time': 46.67,
     'version': '7.0.0'}

Parsing the complete progress table helps anyone who later wants to analyze the raw solution process. I've tried to use the status codes and solution codes present in [PuLP](https://github.com/coin-or/pulp).
