from typing import Any, List, Dict

import eth_account
import requests
from datetime import datetime, timedelta, timezone

from eth_account.signers.local import LocalAccount
from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

# The URL for streaming data from the hyperliquid exchange
URL = "wss://api.hyperliquid.xyz/ws"

TIME_INTERVALS = ("1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M")

_interval_map = {
    '1m': lambda : timedelta(minutes=1),
    '3m': lambda : timedelta(minutes=3),
    '5m': lambda : timedelta(minutes=5),
    '15m': lambda : timedelta(minutes=15),
    '30m': lambda : timedelta(minutes=30),
    '1h' : lambda : timedelta(hours=1),
    '2h' : lambda : timedelta(hours=2),
    '4h' : lambda : timedelta(hours=4),
    '8h' : lambda : timedelta(hours=8),
    '12h' : lambda : timedelta(hours=12),
    '1d': lambda : timedelta(days=1),
    '3d': lambda : timedelta(days=3),
    '1w': lambda : timedelta(days=7),
}

def init(
    secret_key: str,
    address: str,
    main_net: bool = False,
    skip_ws: bool = False,
    perp_dexs=None
):
    """
    Initialize a connection to Hyperliquid and validate account state.

    This function:
    - Create a local Ethereum account from the provide secret key
    - Selects the Hyperliquid testnet or mainnet API
    - Initializes the Info and Exchange clients
    """

    account: LocalAccount = eth_account.Account.from_key(secret_key)
    local_address = address if address else account.address
    print("Running with account address:", local_address)

    # base_url = constants.MAINNET_API_URL if main_net else constants.TESTNET_API_URL
    base_url = constants.TESTNET_API_URL
    info = Info(base_url, skip_ws, perp_dexs)
    user_state = info.user_state(local_address)
    spot_user_state = info.spot_user_state(local_address)
    margin_summary = user_state["marginSummary"]
    print(spot_user_state)
    print(margin_summary)
    if float(margin_summary["accountValue"]) == 0 and len(spot_user_state["balances"]) == 0:
        print("Not running because the provided account has no equity")
        url = info.base_url.split(".", 1)[1]
        error_string = (
            f"No accountValue:\n"
            f"If you think this is a mistake, make sure that { local_address} "
            f" has a balance on {url}.\n"
            f"If address shown is your API wallet address, update the config "
            f"to specify the address of your account, not the address of the API wallet."
        )
        raise Exception(error_string)
    
    exchange = Exchange(
        account,
        base_url,
        account_address=local_address,
        perp_dexs=perp_dexs
    )

    return local_address, info, exchange

def dl_ohlc(sym: str, interval: str, start: datetime, end: datetime) -> List [Dict[str, Any]]:
    """
    Download OHLC (candlestick) data for a given symbol and time range from Hyperliquid
    """

    end_time_ms = int(end.timestamp() * 1000)
    start_time_ms = int(start.timestamp() * 1000)

    resp = requests.post(
        "https://api.hyperliquid.xyz/info",
        headers={"Content-Type": "application/json"},
        json={
            "type": 'candleSnapshot',
            "req": {
                "coin": sym,
                "interval": interval,
                "startTime": start_time_ms, 
                "endTime": end_time_ms, 
            }
        }
    )

    return resp.json()

def dl_last_candles(sym: str, interval: str, no_lags: int = 5):
    """
    Download the most recent candlestick data for a give symbol
    and calculate base on interval the time window
    and retrieves the last 'no_lags' candles for the specified interval    
    """

    now = datetime.now(timezone.utc)
    delta = _interval_map[interval]
    start = now - delta() * no_lags

    return dl_ohlc(sym, interval,start, now)

