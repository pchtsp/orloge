## Orloge

## What and why

The idea of this project is to permit a fast and easy parsing of the log files from different solvers, specifically 'operations research' (OR) logs.

There exist bigger, and more robust libraries. In particular, [IPET](https://github.com/GregorCH/ipet/). The trouble I had was that it deals with too many benchmarking and GUI things and I wanted something simple I could modify and build on top.

In any case, a lot of the ideas and parsing strings were obtained or adapted from IPET, to whom I am graceful.

The supported solvers for the time being are: GUROBI, CPLEX and CBC. Specially the two first ones.

## How

The basic idea is just to provide a unique interface function like the following:

    import orloge as ol
    ol.get_info_log_solver(path_to_solver_log, solver_name)

This returns a python dictionary with a lot of information from the log (see *Examples* below).

## Installation

    pip install git+https://github.com/pchtsp/

## Testing

Run the command 
    
    python -m unittest test

 if the output says OK, all tests were passed.

## Reference

### Main parameters

The most common parameters to extract are: `best_bound`, `best_solution` and `time`. These three parameters are obtained at the end of the solving process and summarize the best relaxed objective value obtained, the best integer objective value obtained and the time it took to do the solving.

### Cuts

The cuts information can be accessed by the `cuts_info` key. It offers the best known bound after the cut phase has ended, the best solution (if any) after the cuts and the number of cuts made of each type.

### Matrix

There are two matrices that are provided. The `matrix` key returns the number of variables, constraints and non-zero values before the pre-processing of the solver. The `matrix_post` key returns these same values after the pre-processing has been done.

### Progress

The `progress` key returns a raw pandas Dataframe with the all the progress information the solver gives. Including the times, the gap, the best bound, the best solution, the iterations, nodes, among other. This table can vary in number of columns between solvers but the names of the columns are normalized so as to have the same name for the same information.

### Status

The status is given in several ways. First, a raw string extraction is returned in `status`. Then, a normalized one using codes is given via `sol_code` and `status_code` keys. `sol_code` gives information about the quality of the solution obtained. `status_code` gives details about the status of the solver after finishing (mainly, the reason it stopped).

### Other

There is also information about the pre-solving phase, the first bound and the first solution. Also, there's information about the time it took to solve the root node.

## Examples

    import orloge as ol
    ol.get_info_log_solver('tests/data/cbc298-app1-2.out', 'CBC')

Would produce the following:

    {'best_bound': -96.111283,
     'best_solution': None,
     'cut_info': {'best_bound': -210.09571,
                  'best_solution': 1e+50,
                  'cuts': None,
                  'time': None},
     'first_relaxed': -210.09571,
     'first_solution': 1e+50,
     'gap': None,
     'matrix': {'constraints': 53467, 'nonzeros': 199175, 'variables': 26871},
     'matrix_post': {'constraints': 26555, 'nonzeros': 195875, 'variables': 13265},
     'nodes': 31867,
     'presolve': None,
     'progress':       
     Node NodesLeft BestInteger CutsBestBound     Time
    0        0         1       1e+50    -210.09571    32.83
    1      100        11       1e+50    -210.09571   124.49
    ..     ...       ...         ...           ...      ...
    [319 rows x 5 columns],
     'rootTime': None,
     'sol_code': 0,
     'solver': 'CBC',
     'status': 'Stopped on time limit',
     'status_code': -4,
     'time': 7132.49,
     'version': '2.9.8'}

And another example, this time using GUROBI:

    import orloge as ol
    ol.get_info_log_solver('tests/data/gurobi700-app1-2.out', 'GUROBI')

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
     'first_solution': -41.0,
     'gap': 0.0,
     'matrix': {'constraints': 53467, 'nonzeros': 199175, 'variables': 26871},
     'matrix_post': {'constraints': 35616, 'nonzeros': 149085, 'variables': 22010},
     'nodes': 526.0,
     'presolve': {'cols': 4861, 'rows': 17851, 'time': 3.4},
     'progress':    
     Node NodesLeft   Objective Depth ...  CutsBestBound    Gap ItpNode Time
    0     0         0  -178.94318     0 ...     -178.94318   336%    None   4s
    1     0         0  -171.91701     0 ...     -171.91701   319%    None  15s
    2     0         0  -170.97660     0 ...     -170.97660   317%    None  15s
    [26 rows x 10 columns],
     'rootTime': 0.7,
     'sol_code': 1,
     'solver': 'GUROBI',
     'status': 'Optimal solution found',
     'status_code': 1,
     'time': 46.67,
     'version': '7.0.0'}

Parsing the complete progress table helps anyone who later wants to analyze the raw solution process. I've tried to use the status codes and solution codes present in [PuLP](https://github.com/coin-or/pulp).
