#!/usr/bin/python

# Copyright 2017  Opalytics, Inc.
#

# Implement core functionality needed to achieve modularity.
# 1. Define the input data schema
# 2. Define the output data schema
# 3. Create a solve function that accepts a data set consistent with the input
#    schema and (if possible) returns a data set consistent with the output schema.
#
# Provides command line interface via ticdat.standard_main
# For example, typing
#   python fleethd.py -i input_data.xlsx -o solution_data.xlsx
# will read from a model stored in the file input_data.xlsx and write the solution
# to solution_data.xlsx.
#
# Note that file requires fleethd.lng to be in the same directory

from ticdat import TicDatFactory, standard_main, lingo_run

# ------------------------ define the input schema --------------------------------
input_schema = TicDatFactory (
    city = [["Name"],[]],
    load = [["Number"],[]],
    vehicles  = [["Vehicle Type"],["Fixed Cost", "Fixed Size"]],
    load_transit = [["Load", "Origin City", "Destination City",],["Departure Time"]],
    available = [["Vehicle Type", "City"],["Number Vehicles"]],
    travel = [["Vehicle Type", "Origin City", "Destination City"],
              ["Loaded Time", "Deadhead Time", "Deadhead Cost"]],
    # Deadhead Cost (aka CDHEAD) appears to be unused by fleethd.lng
    # skipping the following data for now (is X a variable, is PC a parameter constant
 # VXLXCXC( VTYPE, LXCXC):
 #  X,      ! Number vehicles used(0 or 1) by type, on this load;
 #  PC;     ! Profit contribution by type, Load;
    )
# only setting foreign keys for now, since LINGO actually does need those

input_schema.add_foreign_key("load_transit", "load", ["Load", "Number"])
input_schema.add_foreign_key("load_transit", "city", ["Origin City", "Name"])
input_schema.add_foreign_key("load_transit", "city", ["Destination City", "Name"])
input_schema.add_foreign_key("available", "vehicles", ["Vehicle Type", "Vehicle Type"])
input_schema.add_foreign_key("available", "city", ["City", "Name"])
input_schema.add_foreign_key("travel", "vehicles", ["Vehicle Type", "Vehicle Type"])
input_schema.add_foreign_key("travel", "city", ["Origin City", "Name"])
input_schema.add_foreign_key("travel", "city", ["Destination City", "Name"])

input_schema.lingo_prepend = "inp_"
# ---------------------------------------------------------------------------------

# ------------------------ define the output schema -------------------------------
# Leaving solution empty, just trying to get a solve to happen
solution_schema = TicDatFactory()
# ---------------------------------------------------------------------------------

# ------------------------ create a solve function --------------------------------
def solve(dat):
    """
    core solving routine
    :param dat: a good ticdat for the input_schema
    :return: a good ticdat for the solution_schema, or None
    """
    assert input_schema.good_tic_dat_object(dat)
    assert not input_schema.find_foreign_key_failures(dat)
    assert not input_schema.find_data_type_failures(dat)
    assert not input_schema.find_data_row_failures(dat)

    solution_variables = TicDatFactory()

    sln = lingo_run("fleethd.lng", input_schema, dat, solution_variables)
    if sln:
        rtn = solution_schema.TicDat()
        return rtn
# ---------------------------------------------------------------------------------

# ------------------------ provide stand-alone functionality ----------------------
# when run from the command line, will read/write xls/csv/db/sql/mdb files
if __name__ == "__main__":
    standard_main(input_schema, solution_schema, solve)
# ---------------------------------------------------------------------------------