"""One-shot MAPF on 4-connected grids: our own PIBT and the tools around it.

Reference: Okumura et al., "Priority Inheritance with Backtracking for
Iterative Multi-agent Path Finding", arXiv 1901.11282v5, Algorithm 1.

Conventions used by every module:
    Coord    = (row, col), i.e. (y, x). Row 0 is the top line of the .map file.
    Config   = list of Coord, one per agent, for one timestep.
    Solution = list of Config; solution[t][i] is agent i's cell at timestep t,
               and solution[0] is the start configuration.
"""
