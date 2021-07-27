LpStatusNotSolved = 0
LpStatusSolved = 1
LpStatusInfeasible = -1
LpStatusUnbounded = -2
LpStatusUndefined = -3
LpStatusTimeLimit = -4
LpStatusMemoryLimit = -5

LpSolutionNoSolutionFound = 0
LpSolutionOptimal = 1
LpSolutionIntegerFeasible = 2
LpSolutionInfeasible = -1
LpSolutionUnbounded = -2

solver_to_solution = {
    LpStatusNotSolved: LpSolutionNoSolutionFound,
    LpStatusSolved: LpSolutionOptimal,
    LpStatusInfeasible: LpSolutionInfeasible,
    LpStatusUnbounded: LpSolutionUnbounded,
    LpStatusUndefined: LpSolutionNoSolutionFound,
    LpStatusTimeLimit: LpSolutionNoSolutionFound,
    LpStatusMemoryLimit: LpSolutionNoSolutionFound,
}
