import logging
from config import UI_AMOUNT, TARGET_OWNER
import asyncio

async def extract_data(data):
    try:
        transactions = data.get("params", {}).get("result", {}).get("value", {}).get("block", {}).get("transactions", [])
        for tx in transactions:
            post_token_balances = tx.get("meta", {}).get("postTokenBalances", [])
            if len(post_token_balances) >= 2:
                first_post_token_balance = post_token_balances[0]
                uiAmount = first_post_token_balance.get('uiTokenAmount')
                if first_post_token_balance.get("owner") == TARGET_OWNER and uiAmount.get("uiAmount") == UI_AMOUNT:
                    mint = first_post_token_balance.get("mint")
                    logging.info(f"Migration detected: {mint}")
                    return mint
    except Exception as e:
        logging.error(f"Error extracting data: {e}")
    return None

async def send_ping_chainstack_ws(websocket):
    while True:
        await websocket.ping()
        await asyncio.sleep(6)

async def send_ping_ave(ws):
    while not ws.closed:
        try:
            await ws.ping()
        except Exception as e:
            logging.error(f"Ping failed: {e}")
            break
        await asyncio.sleep(7)
