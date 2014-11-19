import cython
cimport numpy
import numpy
import ctypes
from libc.stdlib cimport malloc, free

ctypedef void* model_t

ctypedef struct feature_node:
  int index
  double value

ctypedef int (*predictPTR)(model_t, feature_node*)
ctypedef int (*predict_probabilityPTR)(model_t, feature_node*, double*)

double_p = ctypes.POINTER(ctypes.c_double)

@cython.boundscheck(False)
def classify(features, model, liblinear):
  cdef:
    numpy.ndarray[numpy.float64_t, ndim=2, negative_indices=False, mode='c'] features_c = numpy.asarray(features, dtype=numpy.float64, order='C')
    numpy.ndarray[numpy.int32_t, ndim=1, negative_indices=False] classifications = numpy.empty(len(features), dtype=numpy.int32)
    predictPTR predict = <predictPTR><size_t>ctypes.cast(liblinear.predict, ctypes.c_voidp).value
    model_t model_c = <model_t><size_t>ctypes.cast(model, ctypes.c_voidp).value
    feature_node* data = <feature_node *> malloc((1+features_c.shape[1]) * sizeof(feature_node))
    unsigned int i, j, l, lf
  try:
    l = features_c.shape[0]
    lf = features_c.shape[1]
    for j in range(0, lf):
      data[j].index = j
    data[lf].index = -1
    for i in range(0, l):
      for j in range(0, lf):
        data[j].value = features_c[i,j]
      classifications[i] = predict(model_c, data)
    return classifications
  finally:
    free(data)

@cython.boundscheck(False)
def classify_probability(features, model, liblinear, decision_value=False):
  cdef:
    numpy.ndarray[numpy.float64_t, ndim=2, negative_indices=False, mode='c'] features_c = numpy.asarray(features, dtype=numpy.float64, order='C')
    numpy.ndarray[numpy.int32_t, ndim=1, negative_indices=False] classifications = numpy.empty(len(features), dtype=numpy.int32)
    numpy.ndarray[numpy.float64_t, ndim=1, negative_indices=False] probabilities = numpy.empty(len(features), dtype=numpy.float64)
    predict_probabilityPTR predict
    model_t model_c = <model_t><size_t>ctypes.cast(model, ctypes.c_voidp).value
    feature_node* data = <feature_node *> malloc((1+features_c.shape[1]) * sizeof(feature_node))
    unsigned int i, j, l, lf
    double prob[2]
  try:
    assert model.contents.nr_class == 2
    func = liblinear.predict_values if decision_value else liblinear.predict_probability
    predict = <predict_probabilityPTR><size_t>ctypes.cast(func, ctypes.c_voidp).value
    l = features_c.shape[0]
    lf = features_c.shape[1]
    for j in range(0, lf):
      data[j].index = j
    data[lf].index = -1
    for i in range(0, l):
      for j in range(0, lf):
        data[j].value = features_c[i,j]
      classifications[i] = predict(model_c, data, prob)
      probabilities[i] = prob[0]
    return classifications, probabilities
  finally:
    free(data)

@cython.boundscheck(False)
def poly2_features(features):
  cdef:
    numpy.ndarray[numpy.float64_t, ndim=2, negative_indices=False, mode='c'] features_c = numpy.asarray(features, dtype=numpy.float64, order='C')
    numpy.ndarray[numpy.float64_t, ndim=2, negative_indices=False, mode='c'] new_features
    unsigned int i, j, jj, k, l, d, nd
    double v
  l = features.shape[0]
  d = features.shape[1]
  nd = d+(d*(d-1))/2 # d original features plus d-choose-2 pairwise features
  new_features = numpy.empty((l, nd), dtype=numpy.float64, order='C')
  for i in range(0, l):
    k = 0
    for j in range(0, d):
      v = features[i, j]
      new_features[i, k] = v
      k += 1
      for jj in range(0, j):
        new_features[i, k] = v*features[i, jj]
        k += 1
  return new_features