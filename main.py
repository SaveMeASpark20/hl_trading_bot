import asyncio
import os
from dotenv import load_dotenv
from settings import params
import hl
import strategy
import models
from stream import LogReturn
from typing import List
import websockets
from datetime import datetime, timezone
import json


load_dotenv()

def create_model() -> models.LinReg:
    model_params = params['model']
    weights = model_params['weight']
    bias = model_params['weight']
    
    return models.LinReg(weights, bias)

def dl_prices_ts(coin: str, interval: str) -> List[tuple[int, str]]:
    """
    Download the price data for a trading pair

    Fetch candlestick data from the exchange API
    and converts it to a simple list of timestamp, price

    """

    candles = hl.dl_last_candles(coin, interval)
    
    #t = timestamp
    #c = closing

    prices = [(candle['t'], candle['c']) for candle in candles]
     
    return prices

def create_strategy(exchange) -> strategy.BasicTakerStrat:
    """
    1. extracts config from global params
    2. Creates the prediction model
    3. Initializes the lag calculator
    4. Download historical price data
    5. Warms up the lag calculator with historical data
    6. Constructs the complete strategy instances
    """

    coin = params['sym']
    interval = params['interval']

    model = create_model()

    trade_sz = 0.0002

    lag = LogReturn()

    prices = dl_prices_ts(coin, interval)
    for _, price in prices:
        lag.on_tick(float(price))

    return strategy.BasicTakerStrat(exchange, coin, model, trade_sz, lag)

def interval_mins(interval: str) -> int:
    """
    Convert a time interval string to minutes

    Supports standard trading intervals:
    - 'Xm' for minutes (e.g., '15m' = 15 minutes)
    - 'Xh' for hours (e.g., '1h' = 60 minutes)
    - 'Xd' for days (e.g., '1d' = 1440 minutes) 
    """
    #get the last char on the interval
    dur = interval[-1]

    if dur == 'h':
        return  interval[:-1] * 60
    
    if dur == 'm':
        return interval[:-1]
    
    if dur == 'd':
        return interval[:-1] * 24 * 60
    
    raise ValueError(f"Invalid Interval: {interval}")

async def trade_periodically(interval: str, strat) -> None:
    """
    Async task that continously  and executes trades, it gets the time and waiting time for execution

    Timing example for '1h' interval:
    - Current time: 10:37:45
    - Next execution: 11:00:00
    - Wait time: 22 minutes, 15 seconds
    """

    global last_price

    no_mins = interval_mins(interval)
    period_mins = max(1, no_mins)

    while True:

        #Calculate how many minutes has pass  since the last interval boundary
        now = datetime.now(timezone.utc)
        mins_past = now.minute  % period_mins

        #Calculate until the next interval boundary in seconds
        # Formula: (remaining minutes in period * 60) - current seconds - micorseconds
        seconds_until_next = (
                (period_mins - mins_past) * 60 
                - now.second 
                - (now.microsecond / 1_000_000.0)
        )

        #with tiny buffer
        await asyncio.sleep(seconds_until_next + 0.0001)

        execution_time = datetime.now(timezone.utc)

        if last_price:
            tick = strat.on_tick(last_price)
            if tick:
                print(f"--- [Sync Every {interval}] {execution_time.strftime('%H:%M:%S')} |"
                  f"Price: {last_price}")
        else:
            #No price data available yet
            print(
                f"--- [Sync Every {interval}] {execution_time.strftime('%H:%M:%S')} | "
                f"Price {last_price} ---"
            )

async def connect_and_listen(interval: str, strat) -> None:
    """
    Connect to Websocket feed and listen for real-time price updates
    Async create_task periodically for getting the time of waiting to execute
    """

    global last_price

    timer_task = asyncio.create_task(trade_periodically(interval, strat))
    try:
        # Connect to WebSocket with keepalive ping
        async with websockets.connect(hl.URL, ping_interval=20) as ws:
            print(f"Connected to {strat.coin} stream")

            #subscribe to trade updates for the specified coin
            await ws.send(json.dumps({
                "method": "subscribe",
                "subscription": {"type": "trades", "coin": strat.coin}
            }))        

            async for message in ws:
                data = json.loads(message)
                trade_data = data.get("data")
                print(f"data: {data}")
                print(f"trade data: {trade_data}")

                if isinstance(trade_data, list):
                    last_trade = trade_data[-1]
                    last_price = float(last_trade['px'])
                    # Price is stored; periodic task will use it for trading

    finally:
        #Clean up: cancel the periodic trading task when Websocket disconnects
        #This prevents multiple timer tasks for accumulating on reconnects
        timer_task.cancel()

async def main() -> None:
    """
    Main application entry point.

    This function:
    1. Loads credentials from environment variables 
    2. Initialize the exchange connection
    """

    secret_key = os.environ["HL_SECRET"]
    wallet = os.environ["HL_WALLET"]

    backoff = 1
    interval = params['interval']
    
    address, info, exchange = hl.init(secret_key, wallet)

    strat = create_strategy(exchange)
    if interval not in hl.TIME_INTERVALS:
        raise Exception(f"Invalid time interval: {interval}")

    #Connection loop auto reconnect, also trading happening
    
    while True:
        try:
            #connect and listening and trading
            await connect_and_listen(interval, strat)
            backoff = 1 # Reset backoff on clen exit
        except (websockets.ConnectionClosed, OSError) as e:
            print(f"Disconnected: {e}. Reconnection in {backoff}s...") 
            await asyncio.sleep(backoff)

            backoff = min(backoff * 2, 30) # Cap at 30 seconds


asyncio.run(main())