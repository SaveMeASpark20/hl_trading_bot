
from dataclasses import dataclass
from typing import Optional
from stream import Tick

import numpy as np

@dataclass
class Order:
    coin: str
    sz: float
    is_buy: bool

@dataclass
class TickReplay:
    """
    Records all information about a single trading tick for analysis and backtesting

    This calass captures the complete state of a trading decision, including
    the input data, model prediction, and resulting order. Useful for
    post-trade analysis, strategy evaluation, and debugging.

    Attributes:
        coin: The assets being traded(the should be same on training and testing)
        sz: size of the executed order
        is_buy: Whether the order was a buy (True) or sell (False)
        y_hat : The model's prediction (forecasted return)
        last_price: The market price when the decision was made
        lag: The calculated feature (e.g., log return) used for prediction
    """

    coin: str
    sz: float
    is_buy: bool
    y_hat: bool
    last_price : float
    lag : float
    



class BasicTakerStrat(Tick):
    """
    A basic market-taking trading strategy using predictive models.

    This strategyoperates as follows:
    - Uses streaming price data to calculate features (e.g., log returns)
    - Feeds features into a machine learning model to predict future returns
    - Generate buy/sel signals based on predictions
    - Executes market order to enter positions
    -Closes previous positions before opening new ones

    The strategy is "taker" because it uses market orders that immediately
    execute at current market prices, paying the taker fee.

    Example:
        >>>
        >>> strategy = BasicTakerStrat(
        ...     exchange=exchange,
        ...     coin='BTC',
        ...     model=model,
        ...     sz=0.1 # Trade 0.1 BTC,
        ...     lag=lag_calculator,
        ...     leverage=2.0,
        ... )

        >>> 
        >>> # Feed streaming prices to the strategy
        >>> strategy.on_tick(50000.0)
        >>> strategy.on_tick(50100.0)
    """

    def __init__(
            self,
            exchange,
            coin: str,
            model,
            sz: float,
            lag,
            leverage: float = 1.0
    ):
        """
        Initialize the trading strategy.

        Args:
            exchange: Exchange client with market_open() and market_close() methods
            coin: The asset symbol to trade (e.g., 'BTC', 'ETH')
            model: Trained ML model with a predict() method
            sz: Position size fo each trade
            lag: Feature calculator (e.g., LogReturn instance) with on_tick() method
            leverage: Leverage multiplier (default 1.0 = no leverage)
        """

        self.exchange = exchange
        self.coin = coin
        self.model = model
        self.lag = lag
        self.sz = sz
        self.leverage = leverage
        
        print("self coin",self.coin)
    def strategy(self, y_hat: float) -> Order:
        is_buy = np.sign(y_hat) == 1
        return Order(self.coin, self.sz, is_buy)
    
    def execute(self, order: Order) -> None:
        
        """
        Execute a trade on the exchange.
        1. Close any existing position in the asset
        2. Open a new position according to the order
        """
        # Close any position
        try: 
            r= self.exchange.market_close(self.coin)
            print(f"Position closed:{r}")
        except Exception as e:
            print(f"Error close position: {e}")

        try:
            r= self.exchange.market_open(
                self.coin,
                bool(order.is_buy),
                float(order.sz)
            )
            print(f"Order Opened: {r}")
        except Exception as e:
            print(f'Error opening position: {e}')

    def on_tick(self, price: float) -> Optional[TickReplay]:
        """
        Process a new price tick and execute the full trading pipeline.

        This is the main entry point for streaming data. Each price tick triggers:
        1. Feature calculation (e.g., log return)
        2. Model prediction
        3. Order generation
        4. Trade execution
        5. Recording of the tick for analysis

        Args:
            price: The current market price
        
        Returns:
            TickReplay object containing all information about this trading decision,
            or None if feature calculation hasn't produced a value yet

        Example:
            >>> replay = strategy.on_tick(50123.45)
            >>> print(f"Predicted return: {replay.y_hat}")    
            >>> print(f"Order direction: {'BUY' if replay.is_buy else 'SELL'}")    
        """

        print(f'On tick: {price}')

        # Calculate feature (e.g., log return) from the new price
        # This might return None if we don't have enough data yet
        # lag = self.lag.on_tick(px)
        lag = self.lag.on_tick(price)
        print(f'Calculated log return: {lag}')

        # Generate prediction from the model
        # Note: This will use the lag value; if lag is None, model should handle it
        y_hat = self.model.predict(lag)
        print(f'Forecast future log return: {y_hat}')

        #Convert prediction into a trading order
        order = self.strategy(y_hat)
        print(f'Order: {order}')

        self.execute(order)
            


