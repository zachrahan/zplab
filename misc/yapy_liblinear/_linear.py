import ctypes
import elegans.utility.ctypes_util as ctypes_util
import os
import _fast_linear_classify
import numpy

POLY2 = False
extra = [('coef0', ctypes.c_double), ('gamma', ctypes.c_double)] if POLY2 else []

double_p = ctypes.POINTER(ctypes.c_double)
int_p = ctypes.POINTER(ctypes.c_int)
class feature_node(ctypes.Structure):
  _fields_ = [('index', ctypes.c_int),
              ('value', ctypes.c_double)]

node_p = ctypes.POINTER(feature_node)
class problem(ctypes.Structure):
  _fields_ = [('l', ctypes.c_int),
              ('n', ctypes.c_int),
              ('y', int_p),
              ('x', ctypes.POINTER(node_p)),
              ('bias', ctypes.c_double)] + extra

class parameter(ctypes.Structure):
  _fields_ = [('solver_type', ctypes.c_int),
              ('eps', ctypes.c_double),
              ('C', ctypes.c_double),
              ('nr_weight', ctypes.c_int),
              ('weight_label', int_p),
              ('weight', double_p)] + extra

class model(ctypes.Structure):
	_fields_ = [('param', parameter),
	            ('nr_class', ctypes.c_int),
	            ('nr_feature', ctypes.c_int),
	            ('w', double_p),
              ('label', int_p),
              ('bias', ctypes.c_double)]


print_func_type = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
_API = {
  'train': (ctypes.POINTER(model), [ctypes.POINTER(problem), ctypes.POINTER(parameter)]),
  'cross_validation': (None, [ctypes.POINTER(problem), ctypes.POINTER(parameter), ctypes.c_int, int_p]),
   
  'save_model': (ctypes.c_int, [ctypes.c_char_p, ctypes.POINTER(model)]),
  'load_model': (ctypes.POINTER(model), [ctypes.c_char_p]),

  'get_nr_feature': (ctypes.c_int, [ctypes.POINTER(model)]),
  'get_nr_class': (ctypes.c_int, [ctypes.POINTER(model)]),
  'get_labels': (None, [ctypes.POINTER(model), int_p]),

  'predict_values': (ctypes.c_int, [ctypes.POINTER(model), node_p, double_p]),
  'predict': (ctypes.c_int, [ctypes.POINTER(model), node_p]),
  'predict_probability': (ctypes.c_int, [ctypes.POINTER(model), node_p, double_p]),

  'free_model_content': (None, [ctypes.POINTER(model)]),
  'free_and_destroy_model': (None, [ctypes.POINTER(ctypes.POINTER(model))]),
  'destroy_param': (None, [ctypes.POINTER(parameter)]),

  'check_parameter': (ctypes.c_char_p, [ctypes.POINTER(problem), ctypes.POINTER(parameter)]),
  'check_probability_model': (ctypes.c_int, [ctypes.POINTER(model)]),
  'set_print_string_function': (None, [print_func_type])
}

_lib = 'liblinear-poly2' if POLY2 else 'liblinear'
liblinear = ctypes_util.load_library((os.path.dirname(__file__),), _lib)
ctypes_util.register_api(liblinear, _API)
_quiet = print_func_type(lambda x:None)
liblinear.set_print_string_function(_quiet)

# Construct constants
SOLVER_TYPE = dict((v, k) for k, v in enumerate(['L2R_LR', 'L2R_L2LOSS_SVC_DUAL', 'L2R_L2LOSS_SVC', 'L2R_L1LOSS_SVC_DUAL', 'MCSVM_CS', 'L1R_L2LOSS_SVC', 'L1R_LR', 'L2R_LR_DUAL']))

def gen_problem(features, values):
  l, n = features.shape
  assert l == len(values)
  linear_problem = problem()
  linear_problem.l = l
  linear_problem.y = (ctypes.c_int * l)(*values)
  linear_problem.x = (node_p * l)()
  linear_problem._x = (feature_node * (n+1) * l)()
  linear_problem.n = n
  linear_problem.bias = 1
  print "filling"
  for i in xrange(l):
    xi = linear_problem._x[i]
    linear_problem.x[i] = xi
    xi[-1].index = -1
    for j in xrange(n):
      xi[j].index = j
      xi[j].value = features[i,j]
  print "full"
  return linear_problem


def default_params():
  params = parameter()
  params.solver_type = SOLVER_TYPE['L2R_L2LOSS_SVC_DUAL']
  params.eps = 0.1
  params.C = 1
  params.nr_weight = 0
  params.weight_label = None
  params.weight = None
  if POLY2:
    params.coef0 = 1
    params.gamma = 1
  return params

def classify_array(model, array):
  return _fast_linear_classify.classify(array, model, liblinear)

def classify_array_probability(model, array, decision_value=False):
  return _fast_linear_classify.classify_probability(array, model, liblinear, decision_value)
