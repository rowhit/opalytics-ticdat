#
# This example demonstrates a script that is capable of fully exploiting all the bells and
# whistles of the Opalytics Cloud Platform. It pre-diagnoses infeasibility conditions and
# records them in a log file. It also keeps track of the MIP progress, and allows for the user
# to terminate the solve prior to achieving the "a priori" goal for the optimization gap.
#
# Solve the Center of Gravity problem from _A Deep Dive into Strategic Network Design Programming_
# http://amzn.to/1Lbd6By
#
# Implement core functionality needed to achieve modularity.
# 1. Define the input data schema
# 2. Define the output data schema
# 3. Create a solve function that accepts a data set consistent with the input
#    schema and (if possible) returns a data set consistent with the output schema.
#
# Provides command line interface via ticdat.standard_main
# For example, typing
#   python cogmodel.py -i cog_sample_data.sql -o cog_solution.sql
# will read from a model stored in cog_sample_data.sql and
# write the solution to the cog_solution.sql directory.

# this version of the file uses Gurobi

import time
import datetime
import os
import gurobipy as gu
from ticdat import TicDatFactory, Progress, LogFile, Slicer, standard_main, gurobi_env

# ------------------------ define the input schema --------------------------------
# There are three input tables, with 4 primary key fields  and 4 data fields.
input_schema = TicDatFactory (
     sites      = [['name'],['demand', 'center_status']],
     distance   = [['source', 'destination'],['distance']],
     parameters = [["key"], ["value"]])

# add foreign key constraints
input_schema.add_foreign_key("distance", "sites", ['source', 'name'])
input_schema.add_foreign_key("distance", "sites", ['destination', 'name'])

# center_status is a flag field which can take one of two string values.
input_schema.set_data_type("sites", "center_status", number_allowed=False,
                          strings_allowed=["Can Be Center", "Pure Demand Point"])
# The default type of non infinite, non negative works for distance
input_schema.set_data_type("distance", "distance")

# There are three types of parameters
input_schema.set_data_type("parameters", "key", number_allowed=False,
                           strings_allowed=["Number of Centroids", "MIP Gap", "Formulation"])
input_schema.set_data_type("parameters", "value", number_allowed=True,
                           strings_allowed=["Weak", "Strong"])

def _good_parameter_key_value(key, value):
    if key == "Number of Centroids":
        return 0 < value < float("inf")
    if key == "MIP Gap":
        return 0 <= value < float("inf")
    if key == "Formulation":
        return value in ["Weak", "Strong"]
input_schema.add_data_row_predicate("parameters", predicate_name="Good Parameter Value for Key",
    predicate=lambda row : _good_parameter_key_value(row["Key"], row["Value"]))
# ---------------------------------------------------------------------------------


# ------------------------ define the output schema -------------------------------
# There are three solution tables, with 2 primary key fields and 3
# data fields amongst them.
solution_schema = TicDatFactory(
    openings    = [['site'],[]],
    assignments = [['site', 'assigned_to'],[]],
    parameters  = [["key"], ["value"]])
# ---------------------------------------------------------------------------------

# ------------------------ create a solve function --------------------------------
def solve(dat, out, err, progress):
    assert isinstance(progress, Progress)
    assert isinstance(out, LogFile) and isinstance(err, LogFile)
    assert input_schema.good_tic_dat_object(dat)
    assert not input_schema.find_foreign_key_failures(dat)
    assert not input_schema.find_data_type_failures(dat)
    out.write("COG output log\n%s\n\n"%time_stamp())
    err.write("COG error log\n%s\n\n"%time_stamp())

    def get_distance(x,y):
        if (x,y) in dat.distance:
            return dat.distance[x,y]["distance"]
        if (y,x) in dat.distance:
            return dat.distance[y,x]["distance"]
        return float("inf")

    def can_assign(x, y):
        return dat.sites[y]["center_status"] == "Can Be Center" \
               and get_distance(x,y)<float("inf")


    unassignables = [n for n in dat.sites if not
                     any(can_assign(n,y) for y in dat.sites) and
                     dat.sites[n]["demand"] > 0]
    if unassignables:
        # Infeasibility detected. Generate an error table and return None
        err.write("The following sites have demand, but can't be " +
                  "assigned to anything.\n")
        err.log_table("Un-assignable Demand Points",
                      [["Site"]] + [[_] for _ in unassignables])
        return

    useless = [n for n in dat.sites if not any(can_assign(y,n) for y in dat.sites) and
                                             dat.sites[n]["demand"] == 0]
    if useless:
        # Log in the error table as a warning, but can still try optimization.
        err.write("The following sites have no demand, and can't serve as the " +
                  "center point for any assignments.\n")
        err.log_table("Useless Sites", [["Site"]] + [[_] for _ in useless])

    progress.numerical_progress("Feasibility Analysis" , 100)

    m = gu.Model("cog", env=gurobi_env())

    assign_vars = {(n, assigned_to) : m.addVar(vtype = gu.GRB.BINARY,
                                        name = "%s_%s"%(n,assigned_to),
                                        obj = get_distance(n,assigned_to) *
                                              dat.sites[n]["demand"])
                    for n in dat.sites for assigned_to in dat.sites
                    if can_assign(n, assigned_to)}
    open_vars = {n : m.addVar(vtype = gu.GRB.BINARY, name = "open_%s"%n)
                     for n in dat.sites
                     if dat.sites[n]["center_status"] == "Can Be Center"}
    if not open_vars:
        err.write("Nothing can be a center!\n") # Infeasibility detected.
        return

    m.update()

    progress.numerical_progress("Core Model Creation", 50)

    # using ticdat.Slicer instead of tuplelist simply as a matter of taste/vanity
    assign_slicer = Slicer(assign_vars)

    for n, r in dat.sites.items():
        if r["demand"] > 0:
            m.addConstr(gu.quicksum(assign_vars[n, assign_to]
                                    for _, assign_to in assign_slicer.slice(n, "*"))
                        == 1,
                        name = "must_assign_%s"%n)

    crippledfordemo = "Formulation" in dat.parameters and \
                      dat.parameters["Formulation"]["value"] == "Weak"
    for assigned_to, r in dat.sites.items():
        if r["center_status"] == "Can Be Center":
            _assign_vars = [assign_vars[n, assigned_to]
                            for n,_ in assign_slicer.slice("*", assigned_to)]
            if crippledfordemo:
                m.addConstr(gu.quicksum(_assign_vars) <=
                            len(_assign_vars) * open_vars[assigned_to],
                            name="weak_force_open%s"%assigned_to)
            else:
                for var in _assign_vars :
                    m.addConstr(var <= open_vars[assigned_to],
                                name = "strong_force_open_%s"%assigned_to)

    number_of_centroids = dat.parameters["Number of Centroids"]["value"] \
                          if "Number of Centroids" in dat.parameters else 1
    if number_of_centroids <= 0:
        err.write("Need to specify a positive number of centroids\n") # Infeasibility detected.
        return

    m.addConstr(gu.quicksum(v for v in open_vars.values()) == number_of_centroids,
                name= "numCentroids")

    if "MIP Gap" in dat.parameters:
        m.Params.MIPGap = dat.parameters["MIP Gap"]["value"]
    m.update()

    progress.numerical_progress("Core Model Creation", 100)

    m.optimize(progress.gurobi_call_back_factory("COG Optimization", m))

    progress.numerical_progress("Core Optimization", 100)

    if not hasattr(m, "status"):
        print "missing status - likely premature termination"
        return
    for failStr,grbKey in (("inf_or_unbd", gu.GRB.INF_OR_UNBD),
                           ("infeasible", gu.GRB.INFEASIBLE),
                           ("unbounded", gu.GRB.UNBOUNDED)):
         if m.status == grbKey:
            print "Optimization failed due to model status of %s"%failStr
            return

    if m.status == gu.GRB.INTERRUPTED:
        err.write("Solve process interrupted by user feedback\n")
        if not all(hasattr(var, "x") for var in open_vars.values()):
            err.write("No solution was found\n")
            return
    elif m.status != gu.GRB.OPTIMAL:
        err.write("unexpected status %s\n"%m.status)
        return

    sln = solution_schema.TicDat()
    sln.parameters["Lower Bound"] = getattr(m, "objBound", m.objVal)
    sln.parameters["Upper Bound"] = m.objVal
    out.write('Upper Bound: %g\n' % sln.parameters["Upper Bound"]["value"])
    out.write('Lower Bound: %g\n' % sln.parameters["Lower Bound"]["value"])

    def almostone(x) :
        return abs(x-1) < 0.0001

    for (n, assigned_to), var in assign_vars.items() :
        if almostone(var.x) :
            sln.assignments[n,assigned_to] = {}
    for n,var in open_vars.items() :
        if almostone(var.x) :
            sln.openings[n]={}
    out.write('Number Centroids: %s\n' % len(sln.openings))
    progress.numerical_progress("Full Cog Solve",  100)
    return sln

def time_stamp() :
    ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
# ---------------------------------------------------------------------------------

# ------------------------ provide stand-alone functionality ----------------------
def percent_error(lb, ub):
    assert lb<=ub
    return "%.2f"%(100.0 * (ub-lb) / ub) + "%"

# when run from the command line, will read/write json/xls/csv/db/mdb files
if __name__ == "__main__":
    if os.path.exists("cog.stop"):
        print "Removing the cog.stop file so that solve can proceed."
        print "Add cog.stop whenever you want to stop the optimization"
        os.remove("cog.stop")

    class CogStopProgress(Progress):
        def mip_progress(self, theme, lower_bound, upper_bound):
            super(CogStopProgress, self).mip_progress(theme, lower_bound, upper_bound)
            print "%s:%s:%s"%(theme.ljust(30), "Percent Error".ljust(20),
                              percent_error(lower_bound, upper_bound))
            # return False (to stop optimization) if the cog.stop file exists
            return not os.path.exists("cog.stop")

    # creating a single argument version of solve to pass to standard_main
    def _solve(dat):
        # create local text files for logging
        with LogFile("output.txt") as out :
            with LogFile("error.txt") as err :
                solution = solve(dat, out, err, CogStopProgress())
                if solution :
                    print('\n\nUpper Bound   : %g' % solution.parameters["Upper Bound"]["value"])
                    print('Lower Bound   : %g' % solution.parameters["Lower Bound"]["value"])
                    print('Percent Error : %s' % percent_error(solution.parameters["Lower Bound"]["value"],
                                                               solution.parameters["Upper Bound"]["value"]))
                    return solution
                else :
                    print('\nNo solution')

    standard_main(input_schema, solution_schema, _solve)
# ---------------------------------------------------------------------------------




