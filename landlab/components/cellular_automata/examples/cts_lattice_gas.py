#!/usr/env/python
"""
cts_lattice_gas.py: continuous-time stochastic version of a lattice-gas cellular 
automaton model.

GT Sep 2014
"""

_DEBUG = False

import time
import random
from landlab import HexModelGrid
from numpy import where, logical_and, sqrt
from landlab.components.cellular_automata.landlab_ca import Transition, CAPlotter
from landlab.components.cellular_automata.oriented_hex_lca import OrientedHexLCA


def setup_transition_list():
    """
    Creates and returns a list of Transition() objects to represent state
    transitions for simple granular mechanics model.
    
    Parameters
    ----------
    (none)
    
    Returns
    -------
    xn_list : list of Transition objects
        List of objects that encode information about the link-state transitions.
    
    Notes
    -----
    The states and transitions are as follows:

    Pair state        Transition to       Process
    ==========        =============       =======
    
    """
    xn_list = []
    
    # Transitions for particle movement into an empty cell
    xn_list.append( Transition((1,0,0), (0,1,0), 1., 'motion') )
    xn_list.append( Transition((2,0,1), (0,2,1), 1., 'motion') )
    xn_list.append( Transition((3,0,2), (0,3,2), 1., 'motion') )
    xn_list.append( Transition((0,4,0), (4,0,0), 1., 'motion') )
    xn_list.append( Transition((0,5,1), (5,0,1), 1., 'motion') )
    xn_list.append( Transition((0,6,2), (6,0,2), 1., 'motion') )
    
    # Transitions for wall impact
    xn_list.append( Transition((1,8,0), (4,8,0), 1.0, 'wall rebound') )
    xn_list.append( Transition((2,8,1), (5,8,1), 1.0, 'wall rebound') )
    xn_list.append( Transition((3,8,2), (6,8,2), 1.0, 'wall rebound') )
    xn_list.append( Transition((8,4,0), (8,1,0), 1.0, 'wall rebound') )
    xn_list.append( Transition((8,5,1), (8,2,1), 1.0, 'wall rebound') )
    xn_list.append( Transition((8,6,2), (8,3,2), 1.0, 'wall rebound') )
    
    # Transitions for head-on collision
    xn_list.append( Transition((1,4,0), (3,6,0), 0.5, 'head-on collision') )
    xn_list.append( Transition((1,4,0), (5,2,0), 0.5, 'head-on collision') )
    xn_list.append( Transition((2,5,1), (4,1,1), 0.5, 'head-on collision') )
    xn_list.append( Transition((2,5,1), (6,3,1), 0.5, 'head-on collision') )
    xn_list.append( Transition((3,6,2), (1,4,2), 0.5, 'head-on collision') )
    xn_list.append( Transition((3,6,2), (5,2,2), 0.5, 'head-on collision') )
    
    # Transitions for glancing collision
    xn_list.append( Transition((1,3,0), (3,1,0), 1.0, 'glancing collision') )
    xn_list.append( Transition((1,5,0), (5,1,0), 1.0, 'glancing collision') )
    xn_list.append( Transition((2,4,0), (4,2,0), 1.0, 'glancing collision') )
    xn_list.append( Transition((6,4,0), (4,6,0), 1.0, 'glancing collision') )
    xn_list.append( Transition((2,4,1), (4,2,1), 1.0, 'glancing collision') )
    xn_list.append( Transition((2,6,1), (6,2,1), 1.0, 'glancing collision') )
    xn_list.append( Transition((1,5,1), (5,1,1), 1.0, 'glancing collision') )
    xn_list.append( Transition((3,5,1), (5,3,1), 1.0, 'glancing collision') )
    xn_list.append( Transition((3,1,2), (1,3,2), 1.0, 'glancing collision') )
    xn_list.append( Transition((3,5,2), (5,3,2), 1.0, 'glancing collision') )
    xn_list.append( Transition((2,6,2), (6,2,2), 1.0, 'glancing collision') )
    xn_list.append( Transition((4,6,2), (6,4,2), 1.0, 'glancing collision') )

    # Transitions for oblique-from-behind collisions
    xn_list.append( Transition((1,2,0), (2,1,0), 1.0, 'oblique') )
    xn_list.append( Transition((1,6,0), (6,1,0), 1.0, 'oblique') )
    xn_list.append( Transition((3,4,0), (4,3,0), 1.0, 'oblique') )
    xn_list.append( Transition((5,4,0), (4,5,0), 1.0, 'oblique') )
    xn_list.append( Transition((2,1,1), (1,2,1), 1.0, 'oblique') )
    xn_list.append( Transition((2,3,1), (3,2,1), 1.0, 'oblique') )
    xn_list.append( Transition((4,5,1), (5,4,1), 1.0, 'oblique') )
    xn_list.append( Transition((6,5,1), (5,6,1), 1.0, 'oblique') )
    xn_list.append( Transition((3,2,2), (2,3,2), 1.0, 'oblique') )
    xn_list.append( Transition((3,4,2), (4,3,2), 1.0, 'oblique') )
    xn_list.append( Transition((1,6,2), (6,1,2), 1.0, 'oblique') )
    xn_list.append( Transition((5,6,2), (6,5,2), 1.0, 'oblique') )
    
    # Transitions for direct-from-behind collisions
    
    # Transitions for collision with stationary particle
    
    if _DEBUG:
        print
        print 'setup_transition_list(): list has',len(xn_list),'transitions:'
        for t in xn_list:
            print '  From state',t.from_state,'to state',t.to_state,'at rate',t.rate,'called',t.name
        
    return xn_list
    
    
def main():
    
    # INITIALIZE
    
    # User-defined parameters
    nr = 21
    nc = 21
    plot_interval = 1.0
    run_duration = 20.0
    report_interval = 5.0  # report interval, in real-time seconds
    p_init = 0.1  # probability that a cell is occupied at start
    plot_every_transition = False
    
    # Remember the clock time, and calculate when we next want to report
    # progress.
    current_real_time = time.time()
    next_report = current_real_time + report_interval

    # Create a grid
    hmg = HexModelGrid(nr, nc, 1.0, orientation='vertical', reorient_links=True)
    
    # Close the grid boundaries
    #hmg.set_closed_nodes(hmg.open_boundary_nodes)
    
    # Set up the states and pair transitions.
    # Transition data here represent particles moving on a lattice: one state
    # per direction (for 6 directions), plus an empty state, a stationary
    # state, and a wall state.
    ns_dict = { 0 : 'empty', 
                1 : 'moving up',
                2 : 'moving right and up',
                3 : 'moving right and down',
                4 : 'moving down',
                5 : 'moving left and down',
                6 : 'moving left and up',
                7 : 'stationary',
                8 : 'wall'}
    xn_list = setup_transition_list()

    # Create data and initialize values.
    node_state_grid = hmg.add_zeros('node', 'node_state_grid')
    
    # Make the grid boundary all wall particles
    node_state_grid[hmg.boundary_nodes] = 8
    
    # Seed the grid interior with randomly oriented particles
    for i in hmg.core_nodes:
        if random.random()<p_init:
            node_state_grid[i] = random.randint(1, 6)
    
    # Create the CA model
    ca = OrientedHexLCA(hmg, ns_dict, xn_list, node_state_grid)
    
    # Create a CAPlotter object for handling screen display
    ca_plotter = CAPlotter(ca)
    
    # Plot the initial grid
    ca_plotter.update_plot()

    # RUN
    current_time = 0.0
    while current_time < run_duration:
        
        # Once in a while, print out simulation and real time to let the user
        # know that the sim is running ok
        current_real_time = time.time()
        if current_real_time >= next_report:
            print 'Current sim time',current_time,'(',100*current_time/run_duration,'%)'
            next_report = current_real_time + report_interval
        
        # Run the model forward in time until the next output step
        ca.run(current_time+plot_interval, ca.node_state, 
               plot_each_transition=plot_every_transition, plotter=ca_plotter)
        current_time += plot_interval
        
        # Plot the current grid
        ca_plotter.update_plot()


    # FINALIZE

    # Plot
    ca_plotter.finalize()


if __name__=='__main__':
    main()