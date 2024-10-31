from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_result
import csv
from config import settings
import random
import glob
import time
from urllib.parse import unquote
from pyrogram.raw.functions.messages import RequestWebView
from contextlib import suppress
import asyncio
from pyrogram import Client
from pyrogram.errors import (
    AuthKeyUnregistered,
    FloodWait,
    Unauthorized,
    UserDeactivated,
)
import os
from logger import logger

API_ID = settings.API_ID
API_HASH = settings.API_HASH
PEER = settings.PEER
GAME_URL = settings.GAME_URL
RANDOM_SLEEP_BEFORE_START = settings.RANDOM_SLEEP_BEFORE_START

def get_session_names():
    names = [os.path.splitext(os.path.basename(file))[0] for file in glob.glob('sessions/*.session')]

    return names

async def get_tg_clients() -> list[Client]:
    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not API_ID or not API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir='sessions/',
    ) for session_name in session_names]

    return tg_clients

async def get_tg_web_data(tg_client: Client, proxy: str | None) -> str:
    session_name = tg_client.name
    tg_web_data = ""
    if RANDOM_SLEEP_BEFORE_START:
        try:
            random_sleep_time = random.randint(1, 5) * int(session_name)
            logger.info(
                f"<magenta>{session_name}</magenta> | random sleep <yellow>{random_sleep_time}</yellow>s before start")
            await asyncio.sleep(random_sleep_time)
        except:
            pass

    for i in range(0,3):
        try:
            if proxy != None:
                tg_client.proxy = proxy.strip()

            if not tg_client.is_connected:
                await tg_client.connect()
                logger.info(f"<magenta>{session_name}</magenta> | "
                            f"<green>successful login</green>")

            dialogs = tg_client.get_dialogs()
            async for dialog in dialogs:
                if (
                    dialog.chat
                    and dialog.chat.username
                    and dialog.chat.username == PEER
                ):
                    break

            while True:
                try:
                    peer = await tg_client.resolve_peer(PEER)
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f'<magenta>{session_name}</magenta> | '
                                   f'FloodWait {fl}')
                    fls *= 2
                    logger.info(f'<magenta>{session_name}</magenta> | '
                                f'Sleep {fls}s')

                    await asyncio.sleep(fls)

            web_view = await tg_client.invoke(
                RequestWebView(
                    peer=peer,
                    bot=peer,
                    platform='android',
                    from_bot_menu=False,
                    url=GAME_URL,
                )
            )

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split(
                        '&tgWebAppVersion', maxsplit=1
                    )[0]
                )
            )

            if tg_client.is_connected:
                await tg_client.disconnect()

            if tg_web_data != None and tg_web_data != '':
                logger.info(f"<magenta>{session_name}</magenta> | "
                            f"<green>successful get tg_web_data</green> | "
                            f"<yellow>{tg_web_data}</yellow>")
                return (session_name, tg_web_data)
            else:
                logger.info(f"<magenta>{session_name}</magenta> | "
                            f"<red>failed to get tg_web_data</red>")
        except Exception as e:
            logger.info(f"<magenta>{session_name}</magenta> | "
                        f"<red>{e}</red> | "
                        f"<yellow>retry after 3s</yellow>")
            await asyncio.sleep(3)

    logger.info(f"<magenta>{session_name}</magenta> | "
                f"<red>failed to get tg_web_data retrying twice</red>")
    return (session_name, "error")


async def run_tasks(tg_clients: list[Client]):
    with open('proxies.txt', 'r') as file:
        proxies = file.readlines()

    if not proxies:
        proxies = [None] * len(tg_clients)

    tasks = [asyncio.create_task(get_tg_web_data(tg_client=tg_client, proxy=proxy))
             for tg_client, proxy in zip(tg_clients, proxies)]

    results = await asyncio.gather(*tasks)

    with open('data.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['session name', 'tg web data'])
        for result in results:
            try:
                writer.writerow(result)
            except Exception as e:
                logger.info(f"<red>write error<red> | "
                            f"<magenta>{result[0]}</magenta> | "
                            f"<yellow>{result[1]}</yellow>")

    logger.info("<green>successful</green> save in <yellow>data.csv</yellow>")

async def main():
    tg_clients = await get_tg_clients()
    await run_tasks(tg_clients=tg_clients)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt, RuntimeError, RuntimeWarning):
        asyncio.run(main())