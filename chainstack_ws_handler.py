import asyncio
import websockets
import json
import logging
from config import SOLANA_WS_URL, TARGET_OWNER, UI_AMOUNT
from utils import extract_data, send_ping_chainstack_ws
from ave_ws_handler import websocket_connect_ave

async def send_request_chainstack_blocks(websocket):
    request = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "blockSubscribe",
        "params": [
            {"mentionsAccountOrProgram": TARGET_OWNER},
            {
                "commitment": "confirmed",
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
                "showRewards": False,
                "transactionDetails": "full"
            }
        ]
    }
    await websocket.send(json.dumps(request))
    logging.info("Subscription request sent")

async def connect_chainstack_ws():
    active_mints = set()
    while True:
        try:
            async with websockets.connect(SOLANA_WS_URL, max_size=2**20) as websocket:
                logging.info("Connected to Solana WebSocket")
                await send_request_chainstack_blocks(websocket)
                asyncio.create_task(send_ping_chainstack_ws(websocket))

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        mint = await extract_data(data)
                        if mint and mint not in active_mints:
                            active_mints.add(mint)
                            asyncio.create_task(websocket_connect_ave(mint, active_mints))
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON parse error: {e}")
        except websockets.ConnectionClosed as e:
            logging.error(f"Connection closed: {e}. Retrying...")
        except Exception as e:
            logging.error(f"WebSocket error: {e}. Retrying...")
        await asyncio.sleep(5)
