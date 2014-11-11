import ctypes
import elegans.utility.ctypes_util as ctypes_util
import os
import _fast_svm_classify
import numpy

double_p = ctypes.POINTER(ctypes.c_double)
_DENSE = True
if _DENSE:
  class svm_node(ctypes.Structure):
    _fields_ = [('dim', ctypes.c_int),
                ('values', double_p)]
else:
  class svm_node(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int),
                ('value', ctypes.c_double)]

node_p = ctypes.POINTER(svm_node)
class svm_problem(ctypes.Structure):
  _fields_ = [('l', ctypes.c_int),
               ('y', double_p),
               ('x', node_p if _DENSE else ctypes.POINTER(node_p))]

class svm_parameter(ctypes.Structure):
  _fields_ = [('svm_type', ctypes.c_int),
              ('kernel_type', ctypes.c_int),
              ('degree', ctypes.c_int),
              ('gamma', ctypes.c_double),
              ('coef0', ctypes.c_double),
              ('cache_size', ctypes.c_double),
              ('eps', ctypes.c_double),
              ('C', ctypes.c_double),
              ('nr_weight', ctypes.c_int),
              ('weight_label', ctypes.POINTER(ctypes.c_int)),
              ('weight', double_p),
              ('nu', ctypes.c_double),
              ('p', ctypes.c_double),
              ('shrinking', ctypes.c_int),
              ('probability', ctypes.c_int)]

class svm_model(ctypes.Structure):
	_fields_ = [('param', svm_parameter),
	            ('nr_class', ctypes.c_int),
	            ('l', ctypes.c_int),
	            ('SV', node_p if _DENSE else ctypes.POINTER(node_p)),
	            ('sv_coef', ctypes.POINTER(double_p)),
	            ('rho', double_p),
	            ('probA', double_p),
              ('probB', double_p),
              ('label', ctypes.POINTER(ctypes.c_int)),
              ('nSV', ctypes.POINTER(ctypes.c_int)),
              ('free_sv', ctypes.c_int)]


print_func_type = ctypes.CFUNCTYPE(None, ctypes.c_char_p)

_API = {
  'svm_train': (ctypes.POINTER(svm_model), [ctypes.POINTER(svm_problem), ctypes.POINTER(svm_parameter)]),
  'svm_cross_validation': (None, [ctypes.POINTER(svm_problem), ctypes.POINTER(svm_parameter), ctypes.c_int, double_p]),

  'svm_save_model': (ctypes.c_int, [ctypes.c_char_p, ctypes.POINTER(svm_model)]),
  'svm_load_model': (ctypes.POINTER(svm_model), [ctypes.c_char_p]),

  'svm_get_svm_type': (ctypes.c_int, [ctypes.POINTER(svm_model)]),
  'svm_get_nr_class': (ctypes.c_int, [ctypes.POINTER(svm_model)]),
  'svm_get_labels': (None, [ctypes.POINTER(svm_model), ctypes.POINTER(ctypes.c_int)]),
  'svm_get_svr_probability': (ctypes.c_double, [ctypes.POINTER(svm_model)]),

  'svm_predict_values': (ctypes.c_double, [ctypes.POINTER(svm_model), node_p, double_p]),
  'svm_predict': (ctypes.c_double, [ctypes.POINTER(svm_model), node_p]),
  'svm_predict_probability': (ctypes.c_double, [ctypes.POINTER(svm_model), node_p, double_p]),

  'svm_free_model_content': (None, [ctypes.POINTER(svm_model)]),
  'svm_free_and_destroy_model': (None, [ctypes.POINTER(ctypes.POINTER(svm_model))]),
  'svm_destroy_param': (None, [ctypes.POINTER(svm_parameter)]),

  'svm_check_parameter': (ctypes.c_char_p, [ctypes.POINTER(svm_problem), ctypes.POINTER(svm_parameter)]),
  'svm_check_probability_model': (ctypes.c_int, [ctypes.POINTER(svm_model)]),
  'svm_set_print_string_function': (None, [print_func_type])
}

libsvm = ctypes_util.load_library((os.path.dirname(__file__),), 'libsvm')
ctypes_util.register_api(libsvm, _API)
_quiet = print_func_type(lambda x:None)
libsvm.svm_set_print_string_function(_quiet)

# Construct constants
SVM_TYPE = dict((v, k) for k, v in enumerate(['C_SVC', 'NU_SVC', 'ONE_CLASS', 'EPSILON_SVR', 'NU_SVR']))
KERNEL_TYPE = dict((v, k) for k, v in enumerate(['LINEAR', 'POLY', 'RBF', 'SIGMOID', 'PRECOMPUTED']))

if _DENSE:
  def gen_svm_problem(data, values):
    data = numpy.ascontiguousarray(data, dtype=numpy.float64)
    values = numpy.ascontiguousarray(values, dtype=numpy.float64)
    l, dim = data.shape
    assert values.shape == (l,)
    problem = svm_problem()
    problem.data = data
    problem.values = values
    problem.l = l
    problem.y = values.ctypes.data_as(double_p)
    problem.x = (svm_node * l)()
    for node, features in zip(problem.x, data):
      node.dim = dim
      node.values = features.ctypes.data_as(double_p)
    return problem
else:
  def gen_svm_node_array(features, indices=None):
    if indices is None:
      nodes_vals = enumerate(features)
    else:
      nodes_vals = zip(indices, features)
    node_array = (svm_node * (len(features)+1))()
    for node, (i, v) in zip(node_array, nodes_vals):
      node.index=i
      node.value=v
    node_array[-1].index=-1
    return node_array

  def gen_svm_problem(feature_lists, values, index_lists=None):
    l = len(feature_lists)
    if index_lists is None:
      index_lists = [None]*l
    assert l == len(values) and l == len(index_lists)
    problem = svm_problem()
    problem.l = l
    problem.y = (ctypes.c_double * l)(*values)
    problem.x = (node_p * l)()
    for i, (features, indices) in enumerate(zip(feature_lists, index_lists)):
      problem.x[i] = gen_svm_node_array(features, indices)
    return problem
  
def default_params():
  params = svm_parameter()
  params.svm_type = SVM_TYPE['C_SVC']
  params.kernel_type = KERNEL_TYPE['RBF']
  params.degree = 3
  params.gamma = 0
  params.coef0 = 0
  params.cache_size = 500
  params.eps = 0.001
  params.C = 1
  params.nr_weight = 0
  params.weight_label = None
  params.weight = None
  params.nu = 0.5
  params.p = 0.1
  params.shrinking = 1
  params.probability = 0
  return params

_fast_classify = _fast_svm_classify.classify_dense if _DENSE else _fast_svm_classify.classify_sparse
def classify_array(model, array):
  return _fast_classify(array, model, libsvm)