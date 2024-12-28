import asyncio
import logging
import aiohttp
from utils import send_ping_ave
from config import WS_URL

# Global tracked dictionary
tracked = {}


async def reconnect_and_resubscribe():
    """Handle reconnection logic and resubscribe for tracked mints."""
    global tracked
    for mint in list(tracked.keys()):
        await websocket_connect_ave(mint, set())


async def websocket_connect_ave(mint, active_mints):
    subscribe_message = {
        "jsonrpc": "2.0",
        "method": "subscribe",
        "params": ["price_extra", [f"{mint}-solana"]],
        "id": 1,
    }

    unsubscribe_message = {
        "jsonrpc": "2.0",
        "method": "unsubscribe",
        "params": ["price_extra", [f"{mint}-solana"]],
        "id": 1,
    }

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    WS_URL,
                    headers={
                        "origin": "https://ave.ai",
                        "pragma": "no-cache",
                        "cache-control": "no-cache",
                        "sec-websocket-extensions": "permessage-deflate; client_max_window_bits",
                        "sec-websocket-version": "13",
                        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    },
                ) as ws:
                    logging.info(f"Connected to AVE WebSocket for mint: {mint}")

                    await ws.send_json(subscribe_message)
                    logging.info(f"Subscription message sent for mint: {mint}")

                    asyncio.create_task(send_ping_ave(ws))

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.json()
                            if "result" in data and "prices" in data["result"]["data"]:
                                prices = data["result"]["data"]["prices"]
                                for price in prices:
                                    token = price["token"]
                                    volume_u_5m = price.get("volume_u_5m", 0)

                                    # Unsubscribe condition
                                    price_change = price.get("price_change", 0)
                                    if price_change < -80 and volume_u_5m < 10000:
                                        logging.info(
                                            f"Unsubscribing from mint {mint} (price_change: {price_change}, volume_u_5m: {volume_u_5m})."
                                        )
                                        await ws.send_json(unsubscribe_message)
                                        active_mints.discard(mint)
                                        return

                                    gmgn = f"https://gmgn.ai/sol/token/{mint}"
                                    photon = (
                                        f"https://photon-sol.tinyastro.io/en/lp/{mint}"
                                    )
                                    bullx = f"https://neo.bullx.io/terminal?chainId=1399811149&address={mint}"
                                    twitter_search = f"https://x.com/search?f=live&q=({mint}%20OR%20url%3A{mint})&src=typed_query"

                                    # Filter for 5m_vol > 30000
                                    if volume_u_5m > 500000:
                                        global tracked
                                        if token not in tracked:
                                            # First occurrence: Add to tracked and send message
                                            tracked[token] = volume_u_5m
                                            message = (
                                                f"🔥 <b>Just hit ${round(volume_u_5m / 1000)}k volume in 5 mins</b>\n\n"
                                                f"<code>{token}</code>\n"
                                                f"MC: ${round(price.get('uprice', 0) * 10**6)}k "
                                                f"<i>({price.get('price_change_5m', 0)}%)</i> | "
                                                f"Bv / Sv: {round(price.get('buy_volume_u_5m', 1) / price.get('sell_volume_u_5m', 1), 3) if price.get('sell_volume_u_5m', 1) != 0 else 0}\n\n"
                                                f"<a href='{twitter_search}'>X Search</a> | <a href='{gmgn}'>GmGn</a> | <a href='{photon}'>Photon</a> | <a href='{bullx}'>BullX</a>"
                                            )
                                            print(
                                                message
                                            )  # Redirects to Telegram via TelegramConsoleRedirector
                                        else:
                                            # Compare with existing volume and send update if needed
                                            prev_volume = tracked[token]
                                            if volume_u_5m > prev_volume * 2:
                                                tracked[token] = volume_u_5m
                                                message = (
                                                    f"🔥🔥 <b>Flipped ${round(prev_volume / 1000)}k volume in 5 mins, now ${round(volume_u_5m / 1000)}k</b>\n\n"
                                                    f"<code>{token}</code>\n"
                                                    f"MC: ${round(price.get('uprice', 0) * 10**6)}k "
                                                    f"<i>({price.get('price_change_5m', 0)}%)</i> | "
                                                    f"Bv / Sv: {round(price.get('buy_volume_u_5m', 1) / price.get('sell_volume_u_5m', 1), 3) if price.get('sell_volume_u_5m', 1) != 0 else 0}\n\n"
                                                    f"<a href='{twitter_search}'>X Search</a> | <a href='{gmgn}'>GmGn</a> | <a href='{photon}'>Photon</a> | <a href='{bullx}'>BullX</a>"
                                                )
                                                print(
                                                    message
                                                )  # Redirects to Telegram via TelegramConsoleRedirector

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logging.error(
                                f"WebSocket error for mint {mint}: {msg.data}"
                            )
                            break

        except Exception as e:
            logging.error(f"Connection error for mint {mint}: {e}")
            await reconnect_and_resubscribe()
        await asyncio.sleep(5)
