import os
from ticdat.opl import create_opl_text, read_opl_text, pattern_finder, opl_run, create_opl_mod_text, _can_run_oplrun_tests
import sys
from ticdat.ticdatfactory import TicDatFactory, DataFrame
from ticdat.testing.ticdattestutils import dietData, dietSchema, addDietDataTypes
from ticdat.testing.ticdattestutils import netflowData, addNetflowDataTypes, nearlySame
from ticdat.testing.ticdattestutils import  netflowSchema, firesException, spacesData, spacesSchema
from ticdat.testing.ticdattestutils import sillyMeData, sillyMeSchema, fail_to_debugger, flagged_as_run_alone
from ticdat.testing.ticdattestutils import  makeCleanDir, addNetflowForeignKeys, clean_denormalization_errors
import unittest

#@fail_to_debugger
class TestOpl(unittest.TestCase):
    def testDiet_oplrunRequired(self):
        self.assertTrue(_can_run_oplrun_tests)
        in_tdf = TicDatFactory(**dietSchema())
        in_tdf.enable_foreign_key_links()
        addDietDataTypes(in_tdf)
        soln_tdf = TicDatFactory(
            parameters=[["parameter_name"], ["parameter_value"]],
            buy_food=[["food"], ["qty"]],consume_nutrition=[["category"], ["qty"]])
        soln_tdf.set_data_type("parameters","parameter_value")
        soln_tdf.set_data_type("buy_food", "qty")
        soln_tdf.set_data_type("consume_nutrition","qty")
        ticdat_mod = create_opl_mod_text(in_tdf, soln_tdf)
        with open("sample_diet_schema.mod", "w") as f:
            f.write(ticdat_mod)
        dat = in_tdf.TicDat(**{t:getattr(dietData(), t) for t in in_tdf.primary_key_fields})
        opl_soln = opl_run("sample_diet.mod", in_tdf, dat, soln_tdf)
        os.remove("sample_diet_schema.mod")
        self.assertTrue(nearlySame(opl_soln.parameters["total_cost"]["parameter_value"], 11.829, epsilon=0.0001))
        self.assertTrue(nearlySame(opl_soln.consume_nutrition["protein"]["qty"], 91, epsilon=0.0001))
    def testNetflow_oplrunRequired(self):
        self.assertTrue(_can_run_oplrun_tests)
        in_tdf = TicDatFactory(**netflowSchema())
        in_tdf.enable_foreign_key_links()
        addNetflowDataTypes(in_tdf)
        soln_tdf = TicDatFactory(flow=[["source", "destination", "commodity"], ["quantity"]])
        soln_tdf.set_data_type("flow","quantity")
        ticdat_mod = create_opl_mod_text(in_tdf, soln_tdf)
        with open("sample_netflow_schema.mod", "w") as f:
            f.write(ticdat_mod)
        dat = in_tdf.TicDat(**{t: getattr(netflowData(), t) for t in in_tdf.primary_key_fields})
        opl_soln = opl_run("sample_netflow.mod", in_tdf, dat, soln_tdf)
        os.remove("sample_netflow_schema.mod")
        self.assertTrue(nearlySame(opl_soln.flow["Detroit", "New York", "Pens"]["quantity"], 30))
    def testDiet(self):
        tdf = TicDatFactory(**dietSchema())
        tdf.enable_foreign_key_links()
        oldDat = tdf.TicDat(**{t:getattr(dietData(),t) for t in tdf.primary_key_fields})
        oldDatStr = create_opl_text(tdf, oldDat)
        newDat = read_opl_text(tdf, oldDatStr)
        self.assertFalse(tdf._same_data(oldDat, newDat))
        oldDat.categories["protein"]["maxNutrition"]=12 # Remove infinity from the data
        changedDatStr = create_opl_text(tdf, oldDat)
        with open("deb.out","w") as f:
            f.write(changedDatStr)
        changedDat = read_opl_text(tdf, changedDatStr)
        self.assertTrue(tdf._same_data(oldDat,changedDat))
    def testNetflow(self):
        tdf = TicDatFactory(**netflowSchema())
        tdf.enable_foreign_key_links()
        oldDat = tdf.freeze_me(tdf.TicDat(**{t:getattr(netflowData(),t) for t in tdf.primary_key_fields}))
        oldDatStr = create_opl_text(tdf, oldDat)
        newDat = read_opl_text(tdf, oldDatStr)
        self.assertTrue(tdf._same_data(oldDat, newDat))
    def testSilly(self):
        tdf = TicDatFactory(**sillyMeSchema())
        tdf.enable_foreign_key_links()
        oldDat = tdf.freeze_me(tdf.TicDat(**sillyMeData()))
        oldDatStr = create_opl_text(tdf, oldDat)
        newDat = read_opl_text(tdf, oldDatStr)
        self.assertTrue(tdf._same_data(oldDat, newDat))
    def testPatternFinder(self):
        testpattern = 'parameters={'
        test1 = 'be sk={ipped}=\tme.\nLP86\n parameters={<"test" 0001>}\n\n<<< post process\n\n\n<<< done\n\n'
        self.assertTrue(25 == pattern_finder(test1, testpattern))
        test2 = 'e sk={ipped}=\tme.\nLP86\n parameters=  {<"test" 0001>}\n\n<<< post process\n\n\n<<< done\n\n'
        self.assertTrue(24 == pattern_finder(test2, testpattern))
        test3 = 'parameters={'
        self.assertTrue(0 == pattern_finder(test3, testpattern))
        test4 = 'be sk={ipped}=\tme.\nLP  pa r      par              amete\nrs=  {      <"test" 0001>}\n\n<ss\done\n\n'
        self.assertTrue(33 == pattern_finder(test4, testpattern))

        testpattern = 'notfound'
        test5 = 'this text should just be sk={ipped}=\tme.\nLP86\npanot foudndrs=  {<"test" 0001>}\n\n<<< post proc'
        self.assertTrue(False == pattern_finder(test5, testpattern))
        test6 = 'found not'
        self.assertTrue(False == pattern_finder(test6, testpattern))
        test7 = 'dnuofton'
        self.assertTrue(False == pattern_finder(test7, testpattern))

        testpattern = '>}'
        test8 = 'be sk={ipped}=\tme.\nLP86\n parameters=  {<"test" 0001\n>      }\n\n<<< posprocess\n\n\n<<< done\n\n'
        self.assertTrue(59 == pattern_finder(test8, testpattern, True))
        test9 = '01>\n\t}\n\n<<< post process\n\n\n<<< done\n\n'
        self.assertTrue(5 == pattern_finder(test9, testpattern, True))
        test10 = '>}>}>}>}>}>}>}>}>}>}>}>}>}>}>}>}>}>}>         } >tadah!'
        self.assertTrue(46 == pattern_finder(test10, testpattern, True))
        test11 = '>}'
        self.assertTrue(1 == pattern_finder(test11, testpattern, True))
        # Run the tests.
if __name__ == "__main__":
    unittest.main()