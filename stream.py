"""
Time Series Window Processing Module

This module privides a set of classes for processing streaming time series data
using sliding windows. It' designed for real-time calculation like log returns
and lagged values, commonly used in financial data analysis.
"""

from abc import ABC, abstractmethod
from collections import deque
from typing import Optional, Deque
import numpy as np

class Tick(ABC):
    """
    Abstract base class for streaming data processors.

    All tick-based processor should inherit from this class and implement
    the on_tick method to handle incoming data points.
    """

    @abstractmethod
    def on_tick(self, x):
        """
        Process a single incoming data point.

        Args:
            x: The incoming data point (type depnds on implementation)

        Returns:
            Implementaion-specific return value
        """ 
        pass

class Window(Tick):

    def __init__(
            self,
            window_size: int,
            ):    
        
        self.data: Deque = deque(maxlen=window_size)

    def on_tick(self, elem) -> Optional[float]: # gagamit kasi lag, kapag simula di nagrereturn yun kaya optional
        """Return old element if capacity of window_size is max"""

        old_elem = None

        if self.is_full():
            old_elem = self.data.popleft()

        self.data.append(elem)

        return old_elem

    def is_full(self) -> bool:
        return len(self.data) == self.data.maxlen
    

class LogReturn(Tick) :
    def __init__(self):
        self.price = Window(2)

    def on_tick(self, price) -> Optional[float]:
        self.price.on_tick(price)

        if self.price.is_full():
            return np.log(self.price.data[1] / self.price.data[0])
        
        return None

#comment ko muna malayo sa ginawang lags eh hahaha
# class LagReturn(Tick) :
#     def __init__(self, lags):
#         self.lags = Window(lags)
#         self.log_return = LogReturn()
#     def on_tick(self, price):
        
#         log_return = self.log_return.on_tick(price)
#         if log_return is not None:
#             self.lags.data.appendleft(log_return) # kaya left kasi kapag vinisualize mo napupunta sa dulo yung una kasi idadrop natin yung naka null sa time series

#         if self.lags.is_full():
#             return self.lags.data

        
            


        
            
        








