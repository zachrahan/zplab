import _svm
import numpy
import ctypes
import elegans.utility.gzip_array as gzip_array

def cv_predict(xs, y, svm_type, xv_fold=5, scale=True, **params):
  xs = numpy.array(xs, dtype=float)
  if len(xs.shape) == 1:
    xs = xs[:,numpy.newaxis]
  if scale:
    xs -= xs.mean(axis=0)
    stds = xs.std(axis=0)
    stds[stds==0] = 1
    xs /= stds
  y = numpy.asarray(y, dtype=float)
  svm_params = _svm.default_params()
  svm_params.svm_type = _svm.SVM_TYPE[svm_type]
  assert not numpy.any(numpy.isnan(xs)) and not numpy.any(numpy.isnan(y))
  problem = _svm.gen_svm_problem(xs, y)
  for k, v in params.items():
    setattr(svm_params, k, v)
  predictions = numpy.empty(y.shape, dtype=numpy.float64)
  _svm.libsvm.svm_cross_validation(problem, svm_params, xv_fold, 
    predictions.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))
  return predictions

class SVM(object):
  def __init__(self, xs, y, svm_type='NU_SVC', scale=True, **params):
    self._setup(xs, y, svm_type, scale)
    self._train(params)

  def _setup(self, xs, y, svm_type, scale=True):
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
    y = numpy.asarray(y, dtype=float)
    self.params = _svm.default_params()
    self.params.svm_type = _svm.SVM_TYPE[svm_type]
    assert not numpy.any(numpy.isnan(xs)) and not numpy.any(numpy.isnan(y))
    self.problem = _svm.gen_svm_problem(xs, y)
    return xs, y

  def _train(self, params):
    for k, v in params.items():
      setattr(self.params, k, v)
    self.model = _svm.libsvm.svm_train(self.problem, self.params)
    
  def __call__(self, xs):
    xs = numpy.array(xs, dtype=float)
    if len(xs.shape) == 1:
      xs = xs[:,numpy.newaxis]
    xs -= self.means
    xs /= self.stds
    return _svm.classify_array(self.model, xs)
  

  def __del__(self):
    if self.model:
      _svm.libsvm.svm_free_and_destroy_model(self.model)

  def save(self, filename):
    _svm.libsvm.svm_save_model(filename, self.model)
    gzip_array.write([self.means, self.stds], filename+'.mean_std')


class CV_SVM(SVM):
  param_bounds = {
    'C': (0, numpy.inf),
    'gamma': (0, numpy.inf),
    'nu': (0, 1)
  }
  
  def __init__(self, xs, y, svm_type='NU_SVC', xv_fold=4, refine_grid=6, scale=True, fixed_params={}, **params):
    xs, y = self._setup(xs, y, svm_type, scale)
    for k, v in fixed_params.items():
      setattr(self.params, k, v)
    self.best_err, best_param_is, errs = grid_search(self.problem, numpy.inf, self.params, xs, y, xv_fold, params)
    if refine_grid:
      try:
        refine_grid = dict(refine_grid)
      except TypeError:
        refine_grid = dict((k, refine_grid) for k in params)
      new_params = {}
      for (k, p), pi in zip(params.items(), best_param_is):
        new_params[k] = _refined_steps(p, pi, refine_grid[k], *self.param_bounds[k])
      err, param_is, ref_errs = grid_search(self.problem, self.best_err, self.params, xs, y, xv_fold, new_params)
      errs.update(ref_errs)
      if param_is is not None:
        self.best_err = err
        best_param_is = param_is
        params = new_params
    self.errors = errs
    self.best_params = dict((k, p[pi]) for (k, p), pi in zip(params.items(), best_param_is))
    self._train(self.best_params)
    # print self.best_params, self.best_err
    
    
class SavedSVM(SVM):
  def __init__(self, filename):
    self.model = _svm.libsvm.svm_load_model(filename)
    self.means, self.stds = gzip_array.read(filename+'.mean_std')
        
class SVR(CV_SVM):
  def __init__(self, xs, y, xv_fold=4, refine_grid=4, scale=True, C=numpy.logspace(-5,10,6,base=2),
      nu=numpy.linspace(0.1,0.9,6), gamma=numpy.logspace(-10,3,6,base=2)):
    CV_SVM.__init__(self, xs, y, 'NU_SVR', xv_fold, refine_grid, scale, C=C, nu=nu, gamma=gamma)

class SVC(CV_SVM):
  def __init__(self, xs, y, xv_fold=4, refine_grid=6, scale=True,nu=numpy.linspace(0.1,0.9,6),
      gamma=numpy.logspace(-10,3,6,base=2)):
    CV_SVM.__init__(self, xs, y, 'NU_SVC', xv_fold, refine_grid, scale, nu=nu, gamma=gamma, fixed_params={'eps':0.00001})

class C_SVC(CV_SVM):
  def __init__(self, xs, y, xv_fold=4, refine_grid=6, scale=True, C=numpy.logspace(-5,10,6,base=2),
      gamma=numpy.logspace(-10,3,6,base=2)):
    CV_SVM.__init__(self, xs, y, 'C_SVC', xv_fold, refine_grid, scale, C=C, gamma=gamma)
    

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

def grid_search(problem, best_err, svm_params, xs, y, xv_fold, params):
  predictions = numpy.empty(y.shape, dtype=numpy.float64)
  indices = list(numpy.ndindex(*[len(p) for p in params.values()]))
  l = len(indices)
  next = 0
  best_params = None
  errs = {}
  for i, param_is in enumerate(indices):
    pct = float(i)/l
    if pct >= next:
      print i, l, int(100*pct)
      next += 0.1
    pset = []
    for (k, p), pi in zip(params.items(), param_is):
      setattr(svm_params, k, p[pi])
      pset.append((k, p[pi]))
    _svm.libsvm.svm_cross_validation(problem, svm_params, xv_fold, 
      predictions.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))
    err = numpy.sqrt(((y-predictions)**2).mean())
    errs[tuple(pset)] = err
    if err < best_err:
      best_err = err
      best_params = param_is
  return best_err, best_params, errs
