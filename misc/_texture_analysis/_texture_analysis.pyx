import cython 
cimport numpy
import numpy
import random

# determine datatypes for mcp
ctypedef numpy.float32_t FLOAT_T
ctypedef float FLOAT_C
FLOAT = numpy.float32

@cython.boundscheck(False)
def sample_texture(image, mask=None, int size=1):
  cdef:
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='fortran'] image_f = numpy.asarray(image, dtype=FLOAT, order='F')
    numpy.ndarray[numpy.uint8_t, ndim=2, negative_indices=False, mode='fortran'] mask_f
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='c'] textures
    unsigned int stop_x, stop_y, skip_mask
    unsigned int i, j, ti, tj
    char ii, jj
    int io, jo
  stop_x, stop_y = image.shape
  if mask is None:
    skip_mask = 1
    tex_size = image.size
  else:
    skip_mask = 0
    tex_size = mask.sum()
    mask_f = numpy.asarray(mask, dtype=numpy.uint8, order='F')
  textures = numpy.empty((tex_size, (2*size+1)**2), dtype=FLOAT, order='C')
  ti = 0
  for i in range(stop_x):
    for j in range(stop_y):
      if skip_mask or mask_f[i, j]:
        tj = 0
        for ii in range(-size,size+1):
          for jj in range(-size,size+1):
            io = i+ii
            jo = j+jj
            if io < 0: io = 0
            if io >= stop_x: io = stop_x-1
            if jo < 0: jo = 0
            if jo >= stop_y: jo = stop_y-1            
            textures[ti, tj] = image_f[io, jo]
            tj += 1
        ti += 1
  return textures

@cython.boundscheck(False)
def sample_ar_texture(image, mask=None, int size=4):
  """Get AR features from: Kwang In Kim et al. Support vector machines for texture classification. PAMI (2002)"""
  cdef:
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='fortran'] image_f = numpy.asarray(image, dtype=FLOAT, order='F')
    numpy.ndarray[numpy.uint8_t, ndim=2, negative_indices=False, mode='fortran'] mask_f
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='c'] textures
    unsigned int stop_x, stop_y, skip_mask
    unsigned int i, j, ti, tj
    char ii, jj
    int io, jo
  stop_x, stop_y = image.shape
  if mask is None:
    skip_mask = 1
    tex_size = image.size
  else:
    skip_mask = 0
    tex_size = mask.sum()
    mask_f = numpy.asarray(mask, dtype=numpy.uint8, order='F')
    assert mask.shape == image.shape
  textures = numpy.empty((tex_size, 8*size+1), dtype=FLOAT, order='C')
  ti = 0
  for i in range(stop_x):
    for j in range(stop_y):
      if skip_mask or mask_f[i, j]:
        tj = 0
        for ii in range(-size,size+1):
          for jj in range(-size,size+1):
            if ii == jj or ii == -jj or ii == 0 or jj == 0 :
              io = i+ii
              jo = j+jj
              if io < 0: io = 0
              if io >= stop_x: io = stop_x-1
              if jo < 0: jo = 0
              if jo >= stop_y: jo = stop_y-1            
              textures[ti, tj] = image_f[io, jo]
              tj += 1
        ti += 1
  return textures


cdef inline FLOAT_C sqr(FLOAT_C a):
  return a*a

@cython.boundscheck(False)
cdef unsigned int weighted_random_choice(numpy.ndarray[FLOAT_T, ndim=1, negative_indices=False] weights):
  cdef:
    FLOAT_C total = 0
    unsigned int i
    unsigned int l = weights.shape[0]
    FLOAT_C rnd = random.random()
  for i in range(l):
    total += weights[i]
  rnd *= total
  for i in range(l):
    rnd -= weights[i]
    if rnd < 0:
      return i

@cython.boundscheck(False)
def seed_kmeans(data, unsigned int k):
  """k-means++: The Advantages of Careful Seeding David Arthur; Sergei Vassilvitskii"""
  cdef:
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='c'] data_c = numpy.asarray(data, dtype=FLOAT, order='C')
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='c'] means = numpy.empty((k, data.shape[1]), dtype=FLOAT, order='C')
    numpy.ndarray[FLOAT_T, ndim=1, negative_indices=False] distances = numpy.empty(data.shape[0], dtype=FLOAT)
    FLOAT_C distance, min_distance
    FLOAT_C inf = numpy.inf
    unsigned int t, m, i, j, l, size
  
  l, size = data.shape
  means[0] = data[random.randrange(l)]
  
  for m in range(1, k):
    for t in range(l):
      min_distance = inf
      for i in range(m):
        distance = 0
        for j in range(size):
          distance += sqr(means[i, j] - data_c[t, j])
        if distance < min_distance:
          min_distance = distance
      distances[t] = min_distance
    means[m] = data[weighted_random_choice(distances)]
  return means

@cython.boundscheck(False)
def kmeans(data, unsigned int k, unsigned int thresh_count=0, unsigned int iter_max=0, seed_carefully=True):
  cdef:
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='c'] data_c = numpy.asarray(data, dtype=FLOAT, order='C')
    numpy.ndarray[FLOAT_T, ndim=2, negative_indices=False, mode='c'] means
    numpy.ndarray[numpy.uint8_t, ndim=1, negative_indices=False] nearest = numpy.empty(data.shape[0], dtype=numpy.uint8)
    numpy.ndarray[numpy.uint32_t, ndim=1, negative_indices=False] counts = numpy.empty(k, dtype=numpy.uint32)
    numpy.ndarray[numpy.uint8_t, ndim=1, negative_indices=False] valid_means = numpy.ones(k, dtype=numpy.uint8)
    FLOAT_C distance, min_distance
    FLOAT_C inf = numpy.inf
    unsigned int t, m, i, l, argmin, changed, size, count
    unsigned int iters = 0
  l, size = data.shape
  if seed_carefully:
    means = seed_kmeans(data_c, k)
  else:
    means = data[numpy.random.permutation(l)[:k]].astype(FLOAT)
  while True:
    
    changed = 0
    for t in range(l):
      min_distance = inf
      for m in range(k):
        if not valid_means[m]:
          continue
        distance = 0
        for i in range(size):
          distance += sqr(means[m, i] - data_c[t, i])
          if distance > min_distance:
            break
        if distance < min_distance:
          argmin = m
          min_distance = distance
      if nearest[t] != argmin:
        nearest[t] = argmin
        changed += 1
    
    counts.fill(0)
    means.fill(0)
    for t in range(l):
      argmin = nearest[t]
      counts[argmin] += 1
      for i in range(size):
        means[argmin, i] += data_c[t, i]
    
    for m in range(k):
      count = counts[m]
      if count == 0:
        valid_means[m] = 0
      else:
        for i in range(size):
          means[m, i] /= count
    iters += 1
    if changed <= thresh_count:
      break
    if iter_max != 0 and iters >= iter_max:
      break
  return means[valid_means.astype(bool)], iters