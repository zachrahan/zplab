import cython
cimport numpy
import numpy
import ctypes
from libc.stdlib cimport malloc, free

ctypedef void* svm_model
ctypedef void* svm_node

ctypedef struct sparse_node:
  int index
  double value

ctypedef struct dense_node:
  int dim
  double *values

ctypedef double (*svm_predictPTR)(svm_model, void*)

double_p = ctypes.POINTER(ctypes.c_double)

@cython.boundscheck(False)
def classify_sparse(features, model, libsvm):
  cdef:
    numpy.ndarray[numpy.float64_t, ndim=2, negative_indices=False, mode='c'] features_c = numpy.asarray(features, dtype=numpy.float64, order='C')
    numpy.ndarray[numpy.float64_t, ndim=1, negative_indices=False] classifications = numpy.empty(len(features), dtype=numpy.float64)
    svm_predictPTR svm_predict = <svm_predictPTR><size_t>ctypes.cast(libsvm.svm_predict, ctypes.c_voidp).value
    svm_model model_c = <svm_model><size_t>ctypes.cast(model, ctypes.c_voidp).value
    sparse_node* data = <sparse_node *> malloc((1+features_c.shape[1]) * sizeof(sparse_node))
    void *data_v = <void *> data
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
      classifications[i] = svm_predict(model_c, data_v)
    return classifications
  finally:
    free(data)

@cython.boundscheck(False)
def classify_dense(features, model, libsvm):
  cdef:
    numpy.ndarray[numpy.float64_t, ndim=2, negative_indices=False, mode='c'] features_c = numpy.asarray(features, dtype=numpy.float64, order='C')
    numpy.ndarray[numpy.float64_t, ndim=1, negative_indices=False] classifications = numpy.empty(len(features), dtype=numpy.float64)
    svm_predictPTR svm_predict = <svm_predictPTR><size_t>ctypes.cast(libsvm.svm_predict, ctypes.c_voidp).value
    svm_model model_c = <svm_model><size_t>ctypes.cast(model, ctypes.c_voidp).value
    dense_node data
    void *data_v = <void *>&data
    unsigned int i, j, l, lf
  l, lf = features.shape
  data.dim = lf
  data.values = <double *>features_c.data
  for i in range(0, l):
    classifications[i] = svm_predict(model_c, data_v)
    data.values += lf
  return classifications

