import numpy as np

class LinReg:
    """
    y= X*w + b
    X= input feature vector
    w= weight vector
    b= bias(intercept term)
    """

    def __init__(self, weights: np.ndarray, bias: float):
        self.weights = weights
        self.bias = bias

    def predict(self, x: np.ndarray) -> float:
        """ 
        Generate a prediction formula y= X*w + b
        
        Example (single prediction):
            >>> model = LinReg(np.array([2.0, 3.0]), bias=1.0)
            >>> x = np.array([1.0, 2.0])
            >>> prediction = model.predict(x)
            >>> # Returns: 2.0*1.0 + 3.0*2.0 + 1.0 = 9.0

        Example (batch prediction):
            >>> x_batch = np.array([
            ...     [1.0, 2.0],
            ...     [2.0, 1.0]
            ... ])
            >>> predictions = model.predict(x_batch)
            >>> # Returns: [9.0, 8.0]

        """

        return np.dot(x, self.weights) + self.bias