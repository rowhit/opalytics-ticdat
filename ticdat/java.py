from ticdat.utils import verify
import os, subprocess, inspect

def java_run(java_file, input_tdf, input_dat, soln_tdf):
    """
    solve an optimization problem using an OPL .mod file
    :param java_file: A .java file that reads/writes json data in verbose
                      ticdat JSON format
    :param input_tdf: A TicDatFactory defining the input schema
    :param input_dat: A TicDat object consistent with input_tdf
    :param soln_tdf: A TicDatFactory defining the solution schema
    :return: a TicDat object consistent with soln_tdf, or None if no solution found
    """
    verify(os.path.isfile(java_file), "mod_file %s is not a valid file."%java_file)
    msg  = []
    verify(input_tdf.good_tic_dat_object(input_dat, msg.append),
           "tic_dat not a good object for the input_tdf factory : %s"%"\n".join(msg))
    assert not input_tdf.find_data_type_failures(input_dat), "input data type failures found"
    assert not input_tdf.find_data_row_failures(input_dat), "input data row failures found"
    assert not input_tdf.find_foreign_key_failures(input_dat), "input foreign key failures found"

    input_tdf.json.write_file(input_dat, "input_dat.json", allow_overwrite=True, verbose = True)
    # need to run java_file, pointed out input_dat.json, with java_file creating solution_dat.json
    if os.path.exists("solution_dat.json"):
        os.remove("solution_dat.json")
    verify(False, """UNDER CONSTRUCTION""")

    if os.path.isfile("solution_dat.json"):
        assert not soln_tdf.json.find_duplicates("solution_dat.json"), "solution row duplicates found"
        rtn = soln_tdf.json.create_tic_dat("solution_dat.json")
        assert not soln_tdf.find_data_type_failures(rtn), "solution data type failures found"
        assert not soln_tdf.find_data_row_failures(rtn), "solution data row failures found"
        assert not soln_tdf.find_foreign_key_failures(rtn), "solution foreign key failures found"
        return rtn





