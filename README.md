The idea of this project is to permit a fast and easy parsing of the log files from different solvers, specifically 'operations research' (OR) logs (the reason for the name).

There exist bigger, probably more robust libraries (IPET is the one that comes to mind) but it deals with too many things and I found it kind of hard to use to build something on top.

The idea is just to provide a function like the following:

  import orloge as ol
  statistics = ol.get_info_log_solver(path, solver)
  print(statistics)

That returns some standard dictionary with the relevant information. For example:

<!-- TODO -->

# Installation

    pip install git+https://github.com/pchtsp/

## Testing

Run the command 
    
    python -m unittest test

 if the output says OK, all tests were passed.
