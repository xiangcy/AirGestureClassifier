# Code from https://github.com/markdregan/K-Nearest-Neighbors-with-Dynamic-Time-Warping

import sys
import collections
import itertools
from sklearn import metrics
from scipy.stats import mode
import numpy as np

class KnnDtw(object):
    """K-nearest neighbor classifier using dynamic time warping
    as the distance measure between pairs of time series arrays
    
    Arguments
    ---------
    n_neighbors : int, optional (default = 5)
        Number of neighbors to use by default for KNN
        
    max_warping_window : int, optional (default = infinity)
        Maximum warping window allowed by the DTW dynamic
        programming function
            
    subsample_step : int, optional (default = 1)
        Step size for the timeseries array. By setting subsample_step = 2,
        the timeseries length will be reduced by 50% because every second
        item is skipped. Implemented by x[:, ::subsample_step]
    """
    
    def __init__(self, n_neighbors=10, max_warping_window=10000, subsample_step=1):
        self.n_neighbors = n_neighbors
        self.max_warping_window = max_warping_window
        self.subsample_step = subsample_step
    
    def fit(self, x, l):
        """Fit the model using x as training data and l as class labels
        
        Arguments
        ---------
        x : array of shape [n_samples, n_timepoints]
            Training data set for input into KNN classifer
            
        l : array of shape [n_samples]
            Training labels for input into KNN classifier
        """
        
        self.x = np.array(x)
        self.l = np.array(l)
        
    def _dtw_distance(self, ts_a, ts_b, d = lambda x,y: np.linalg.norm(x-y)):
        """Returns the DTW similarity distance between two 2-D
        timeseries numpy arrays.

        Arguments
        ---------
        ts_a, ts_b : array of shape [n_samples, n_timepoints]
            Two arrays containing n_samples of timeseries data
            whose DTW distance between each sample of A and B
            will be compared
        
        d : DistanceMetric object (default = abs(x-y))
            the distance measure used for A_i - B_j in the
            DTW dynamic programming function
        
        Returns
        -------
        DTW distance between A and B
        """

        # Create cost matrix via broadcasting with large int
        ts_a, ts_b = np.array(ts_a), np.array(ts_b)
        M, N = len(ts_a), len(ts_b)
        cost = sys.maxint * np.ones((M, N))

        # Initialize the first row and column
        cost[0, 0] = d(ts_a[0], ts_b[0])
        for i in xrange(1, M):
            cost[i, 0] = cost[i-1, 0] + d(ts_a[i], ts_b[0])

        for j in xrange(1, N):
            cost[0, j] = cost[0, j-1] + d(ts_a[0], ts_b[j])

        # Populate rest of cost matrix within window
        for i in xrange(1, M):
            for j in xrange(max(1, i - self.max_warping_window),
                            min(N, i + self.max_warping_window)):
                choices = cost[i - 1, j - 1], cost[i, j-1], cost[i-1, j]
                cost[i, j] = min(choices) + d(ts_a[i], ts_b[j])
        
        # Return DTW distance given window 
        return cost[-1, -1]

    def _dtw_match(self, ts_a, ts_b, d = lambda x,y: np.linalg.norm(x-y)):
        ts_a, ts_b = np.array(ts_a), np.array(ts_b)
        M, N = len(ts_a), len(ts_b)
        cost = sys.maxint * np.ones((M, N))
        # If the predecessor is on the left, set to be 1; 
        # If the predecessor is on the top, set to be -1.
        # If the predecessor is on the top left, set to be 0.
        predecessor = np.zeros((M, N))

        # Initialize the first row and column
        cost[0, 0] = d(ts_a[0], ts_b[0])
        for i in xrange(1, M):
            cost[i, 0] = cost[i-1, 0] + d(ts_a[i], ts_b[0])
            predecessor[i, 0] = -1

        for j in xrange(1, N):
            cost[0, j] = cost[0, j-1] + d(ts_a[0], ts_b[j])
            predecessor[0, j] = 1

        for i in xrange(1, M):
            for j in xrange(max(1, i - self.max_warping_window),
                            min(N, i + self.max_warping_window)):
                if cost[i-1, j-1] <= cost[i, j-1] and cost[i-1, j-1] <= cost[i-1, j]:
                    cost[i, j] = cost[i-1, j-1] + d(ts_a[i], ts_b[j])
                    predecessor[i, j] = 0
                elif cost[i, j-1] <= cost[i-1, j-1] and cost[i, j-1] <= cost[i-1, j]:
                    cost[i, j] = cost[i, j-1] + d(ts_a[i], ts_b[j])
                    predecessor[i, j] = 1
                else:
                    cost[i, j] = cost[i-1, j] + d(ts_a[i], ts_b[j])
                    predecessor[i, j] = -1

        x = M - 1
        y = N - 1
        result = []
        while x != 0 or y != 0:
            result = [(x, y)] + result
            if predecessor[x, y] == 1:
                y -= 1
            elif predecessor[x, y] == -1:
                x -= 1
            else:
                x -= 1
                y -= 1
        result = [(0, 0)] + result
        return result
    
    def _dist_matrix(self, x, y):
        """Computes the M x N distance matrix between the training
        dataset and testing dataset (y) using the DTW distance measure
        
        Arguments
        ---------
        x : array of shape [n_samples, n_timepoints]
        
        y : array of shape [n_samples, n_timepoints]
        
        Returns
        -------
        Distance matrix between each item of x and y with
            shape [training_n_samples, testing_n_samples]
        """
        # Convert to numpy array
        x = np.array(x); y = np.array(y)
        # Compute the distance matrix        
        dm_count = 0
        
        # Compute condensed distance matrix (upper triangle) of pairwise dtw distances
        # when x and y are the same array
        if(np.array_equal(x, y)):
            x_s = x.shape
            dm = np.zeros((x_s[0] * (x_s[0] - 1)) // 2, dtype=np.double)
            
            for i in xrange(0, x_s[0] - 1):
                for j in xrange(i + 1, x_s[0]):
                    dm[dm_count] = self._dtw_distance(x[i][::self.subsample_step],
                                                      y[j][::self.subsample_step])
            
            # Convert to squareform
            dm = squareform(dm)
            return dm
        
        # Compute full distance matrix of dtw distnces between x and y
        else:
            x_s = x.shape
            y_s = y.shape
            dm = np.zeros((x_s[0], y_s[0])) 
            dm_size = x_s[0]*y_s[0]
        
            for i in xrange(0, x_s[0]):
                print "i", i
                for j in xrange(0, y_s[0]):
                    dm[i, j] = self._dtw_distance(x[i][::self.subsample_step],
                                                  y[j][::self.subsample_step])
        
            return dm
        
    def predict(self, y):
        """Predict the class labels or probability estimates for 
        the provided data

        Arguments
        ---------
          y : array of shape [n_samples, n_timepoints]
              Array containing the testing data set to be classified
          
        Returns
        -------
          2 arrays representing:
              (1) the predicted class labels 
              (2) the knn label count probability
        """
        y = np.array(y)
        dm = self._dist_matrix(y, self.x)
        n_col = dm.shape[1]
        k = min(n_col, self.n_neighbors)

        # Identify the k nearest neighbors
        knn_idx = dm.argsort()[:, :k]

        # Identify k nearest labels
        knn_labels = self.l[knn_idx]
        
        # Model Label
        mode_data = mode(knn_labels, axis=1)
        mode_label = mode_data[0]
        mode_proba = mode_data[1]/self.n_neighbors

        return mode_label.ravel(), mode_proba.ravel()

    def dtw_matches(self, y):
        y = np.array(y)
        dm = self._dist_matrix(y, self.x)
        
        neighbor_indices = np.argmin(dm, axis = 1)
        results = []
        for i in range(len(y)):
            ind = neighbor_indices[i]
            # print self.l[ind]
            results.append((ind, self._dtw_match(y[i], self.x[ind])))
        return results