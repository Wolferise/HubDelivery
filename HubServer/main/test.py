import ast

test = """{"Product_path": [{"HubID": 1, "Dep_time": 1624382421, "Dst_time": 1624382500}, {"HubID": 27, "Dep_time": 1624382502, "Dst_time": 1624382600}, {"HubID": 22, "Dep_time": 1624382608, "Dst_time": 1624382650}, {"HubID": 124, "Dep_time": 1624382660, "Dst_time": 1624383000}, {"HubID": 117, "Dep_time": 1624383007, "Dst_time": 1624383100}, {"HubID": 120, "Dep_time": 1624383105, "Dst_time": 0}]}"""
test_dict = dict(ast.literal_eval(test))
print(test_dict, type(test_dict))
