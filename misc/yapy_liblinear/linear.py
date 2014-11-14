import _linear
import numpy
import ctypes
import elegans.utility.gzip_array as gzip_array

def cv_predict(xs, y, solver_type, xv_fold=5, scale=True, **linear_params):
  xs = numpy.array(xs, dtype=float)
  if len(xs.shape) == 1:
    xs = xs[:,numpy.newaxis]
  if scale:
    xs -= xs.mean(axis=0)
    stds = xs.std(axis=0)
    stds[stds==0] = 1
    xs /= stds
  y = numpy.asarray(y, dtype=int)
  params = _linear.default_params()
  params.solver_type = _linear.SOLVER_TYPE[solver_type]
  assert not numpy.any(numpy.isnan(xs)) and not numpy.any(numpy.isnan(y))
  problem = _linear.gen_problem(xs, y)
  for k, v in linear_params.items():
    setattr(params, k, v)
  predictions = numpy.empty(y.shape, dtype=numpy.int32)
  _linear.liblinear.cross_validation(problem, params, xv_fold, 
    predictions.ctypes.data_as(ctypes.POINTER(ctypes.c_int)))
  return predictions

class LinearClassifier(object):
  def __init__(self, xs, y, solver_type, scale=True, **linear_params):
    self._setup(xs, y, solver_type, scale)
    self._train(linear_params)

  def _setup(self, xs, y, solver_type, scale=True):
    self.model = None
    xs = numpy.array(xs, dtype=float)
    if len(xs.shape) == 1:
      xs = xs[:,numpy.newaxis]
    if scale:
      self.means = xs.mean(axis=0)
      self.stds = xs.std(axis=0)
      self.stds[self.stds==0] = 1
      xs -= self.means
      xs /= self.stds
    else:
      self.means = numpy.zeros(xs.shape[1], float)
      self.stds = numpy.ones_like(self.means)
    y = numpy.asarray(y, dtype=int)
    self.params = _linear.default_params()
    self.params.solver_type = _linear.SOLVER_TYPE[solver_type]
    assert not numpy.any(numpy.isnan(xs)) and not numpy.any(numpy.isnan(y))
    self.problem = _linear.gen_problem(xs, y)
    return xs, y

  def _train(self, linear_params):
    for k, v in linear_params.items():
      setattr(self.params, k, v)
    self.model = _linear.liblinear.train(self.problem, self.params)
    
  def __call__(self, xs):
    xs = numpy.array(xs, dtype=float)
    if len(xs.shape) == 1:
      xs = xs[:,numpy.newaxis]
    xs -= self.means
    xs /= self.stds
    return _linear.classify_array(self.model, xs)
  
  def predict_probability(self, xs, decision_values=False):
    xs = numpy.array(xs, dtype=float)
    if len(xs.shape) == 1:
      xs = xs[:,numpy.newaxis]
    xs -= self.means
    xs /= self.stds
    return _linear.classify_array_probability(self.model, xs, decision_values)

  def __del__(self):
    if self.model:
      _linear.liblinear.free_and_destroy_model(self.model)

  def save(self, filename):
    _linear.liblinear.save_model(filename, self.model)
    gzip_array.write([self.means, self.stds], filename+'.mean_std')


class CV_LinearClassifier(LinearClassifier):

  def __init__(self, xs, y, solver_type, C, xv_fold=4, refine_grid=6, scale=True, **linear_params):
    xs, y = self._setup(xs, y, solver_type, scale)
    for k, v in linear_params.items():
      setattr(self.params, k, v)
    self.best_err = numpy.inf
    self.errs = {}
    self.search_C(C, y, xv_fold)
    if refine_grid:
      C = _refined_steps(C, self.best_index, refine_grid, 0, numpy.inf)
      self.search_C(C, y, xv_fold)
    self._train({'C':self.best_C})
    print self.best_C, self.best_err
  
  def search_C(self, C, y, xv_fold):
    predictions = numpy.empty(y.shape, dtype=numpy.int32)
    next = 0
    l = len(C)
    for i, Cval in enumerate(C):
      pct = float(i)/l
      if pct >= next:
        print i, l, int(100*pct)
        next += 0.1
      self.params.C = Cval
      _linear.liblinear.check_parameter(self.problem, self.params)
      _linear.liblinear.cross_validation(self.problem, self.params, xv_fold, 
        predictions.ctypes.data_as(ctypes.POINTER(ctypes.c_int)))
      err = numpy.absolute(y-predictions).mean()
      self.errs[Cval] = err
      if err < self.best_err:
        self.best_err = err
        self.best_index = i
        self.best_C = Cval
    
class SavedLinearClassifier(LinearClassifier):
  def __init__(self, filename):
    self.model = _linear.liblinear.load_model(filename)
    self.means, self.stds = gzip_array.read(filename+'.mean_std')    

def _refined_steps(old, i, new_steps, vmin, vmax):
  if new_steps == 0 or len(old) == 1:
    return [old[i]]
  low = old[max(0, i-1)]
  best = old[i]
  high = old[min(i+1, len(old)-1)]
  extend_h = 0.75*(high - best)
  if extend_h == 0:
    extend_h = 0.75*(high - low)
  extend_l = 0.75*(best - low)
  if extend_l == 0:
    extend_l = 0.75*(high - low)
  return numpy.linspace(max(vmin, best-extend_l), min(vmax, best+extend_h), new_steps)
