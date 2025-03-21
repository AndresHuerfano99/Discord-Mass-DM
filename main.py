#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import time
import random

try:
    import psutil
    from tasksio import TaskPool
    from lib.scraper import Scraper
    from aiohttp import ClientSession
    import logging
    import asyncio
    from datetime import datetime
    logging.basicConfig(
        level=logging.INFO,
        format="\x1b[38;5;9m[\x1b[0m%(asctime)s\x1b[38;5;9m]\x1b[0m %(message)s\x1b[0m",
        datefmt="%H:%M:%S"
    )
except Exception as e:
    print(e)

# Set console title and clear the screen
os.system('title Discord Mass DM')
os.system('cls' if os.name == 'nt' else 'clear')


def clear_screen() -> None:
    """
    Clears the terminal screen.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


class Discord:
    """
    A class to handle Discord token login, server join, and mass DM operations.
    """

    def __init__(self) -> None:
        # Define a cross-platform clear function
        self.clear = (lambda: os.system("clear")) if sys.platform == "linux" else (lambda: os.system("cls"))
        self.clear()

        self.tokens: list[str] = []
        self.guild_name: str | None = None
        self.guild_id: str | None = None
        self.channel_id: str | None = None

        # Load tokens from file
        try:
            with open("data/tokens.txt", "r") as token_file:
                for line in token_file:
                    token = line.strip()
                    if token:
                        self.tokens.append(token)
        except Exception:
            open("data/tokens.txt", "a+").close()
            logging.info("Please insert your tokens \x1b[38;5;9m(\x1b[0mtokens.txt\x1b[38;5;9m)\x1b[0m")
            sys.exit()

        logging.info(f"Successfully loaded \x1b[38;5;9m{len(self.tokens)}\x1b[0m token(s)\n")
        self.invite = input("\x1b[38;5;9m[\x1b[0m?\x1b[38;5;9m] Invite \x1b[38;5;9m->\x1b[0m ")
        self.message = input("\x1b[38;5;9m[\x1b[0m?\x1b[38;5;9m] Message \x1b[38;5;9m->\x1b[0m ").replace("\\n", "\n")
        try:
            self.delay = float(input("\x1b[38;5;9m[\x1b[0m?\x1b[38;5;9m] Delay \x1b[38;5;9m->\x1b[0m "))
        except Exception:
            self.delay = 0

        print()

    def stop(self) -> None:
        """
        Terminates the current process.
        """
        process = psutil.Process(os.getpid())
        process.terminate()

    def nonce(self) -> str:
        """
        Generates a nonce value based on the current time.

        Returns:
            str: The generated nonce.
        """
        date = datetime.now()
        unixts = time.mktime(date.timetuple())
        # Discord's custom nonce calculation
        return str((int(unixts) * 1000 - 1420070400000) * 4194304)

    async def headers(self, token: str) -> dict:
        """
        Generates HTTP headers for Discord requests using cookies.

        Args:
            token (str): The Discord token.

        Returns:
            dict: A dictionary of HTTP headers.
        """
        async with ClientSession() as session:
            async with session.get("https://discord.com/app") as response:
                cookies = str(response.cookies)
                dcfduid = cookies.split("dcfduid=")[1].split(";")[0]
                sdcfduid = cookies.split("sdcfduid=")[1].split(";")[0]

        return {
            "Authorization": token,
            "accept": "*/*",
            "accept-language": "en-US",
            "connection": "keep-alive",
            "cookie": f"__dcfduid={dcfduid}; __sdcfduid={sdcfduid}; locale=en-US",
            "DNT": "1",
            "origin": "https://discord.com",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "referer": "https://discord.com/channels/@me",
            "TE": "Trailers",
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) discord/1.0.9001 Chrome/83.0.4103.122 "
                           "Electron/9.3.5 Safari/537.36")
        }

    async def login(self, token: str) -> None:
        """
        Attempts to log in with the given token.

        Args:
            token (str): The Discord token.
        """
        try:
            headers = await self.headers(token)
            async with ClientSession(headers=headers) as client:
                async with client.get("https://discord.com/api/v9/users/@me/library") as response:
                    if response.status == 200:
                        logging.info(f"Successfully logged in \x1b[38;5;9m({token[:59]})\x1b[0m")
                    elif response.status == 401:
                        logging.info(f"Invalid account \x1b[38;5;9m({token[:59]})\x1b[0m")
                        self.tokens.remove(token)
                    elif response.status == 403:
                        logging.info(f"Locked account \x1b[38;5;9m({token[:59]})\x1b[0m")
                        self.tokens.remove(token)
                    elif response.status == 429:
                        logging.info(f"Ratelimited \x1b[38;5;9m({token[:59]})\x1b[0m")
                        await asyncio.sleep(self.delay)
                        await self.login(token)
        except Exception:
            await self.login(token)

    async def join(self, token: str) -> None:
        """
        Attempts to join a Discord server using an invite code.

        Args:
            token (str): The Discord token.
        """
        try:
            headers = await self.headers(token)
            url = f"https://discord.com/api/v9/invites/{self.invite}"
            async with ClientSession(headers=headers) as client:
                async with client.post(url, json={}) as response:
                    resp_json = await response.json()
                    if response.status == 200:
                        self.guild_name = resp_json["guild"]["name"]
                        self.guild_id = resp_json["guild"]["id"]
                        self.channel_id = resp_json["channel"]["id"]
                        logging.info(f"Successfully joined {self.guild_name[:20]} \x1b[38;5;9m({token[:59]})\x1b[0m")
                    elif response.status in (401, 403):
                        logging.info(f"Invalid/Locked account \x1b[38;5;9m({token[:59]})\x1b[0m")
                        self.tokens.remove(token)
                    elif response.status == 429:
                        logging.info(f"Ratelimited \x1b[38;5;9m({token[:59]})\x1b[0m")
                        await asyncio.sleep(self.delay)
                        self.tokens.remove(token)
                    else:
                        self.tokens.remove(token)
        except Exception:
            await self.join(token)

    async def create_dm(self, token: str, user: str) -> str | bool:
        """
        Creates a direct message channel with a user.

        Args:
            token (str): The Discord token.
            user (str): The user ID to DM.

        Returns:
            str | bool: The channel ID if successful, otherwise False.
        """
        try:
            headers = await self.headers(token)
            async with ClientSession(headers=headers) as client:
                url = "https://discord.com/api/v9/users/@me/channels"
                async with client.post(url, json={"recipients": [user]}) as response:
                    resp_json = await response.json()
                    if response.status == 200:
                        logging.info(f"Successfully created DM with {resp_json['recipients'][0]['username']} \x1b[38;5;9m({token[:59]})\x1b[0m")
                        return resp_json["id"]
                    elif response.status in (401, 403):
                        logging.info(f"Invalid account or cannot message user \x1b[38;5;9m({token[:59]})\x1b[0m")
                        self.tokens.remove(token)
                        return False
                    elif response.status == 429:
                        logging.info(f"Ratelimited \x1b[38;5;9m({token[:59]})\x1b[0m")
                        await asyncio.sleep(self.delay)
                        return await self.create_dm(token, user)
                    else:
                        return False
        except Exception:
            return await self.create_dm(token, user)

    async def direct_message(self, token: str, channel: str) -> bool:
        """
        Sends a direct message to a specified channel.

        Args:
            token (str): The Discord token.
            channel (str): The DM channel ID.

        Returns:
            bool: True if message was sent successfully, False otherwise.
        """
        try:
            headers = await self.headers(token)
            url = f"https://discord.com/api/v9/channels/{channel}/messages"
            payload = {"content": self.message, "nonce": self.nonce(), "tts": False}
            async with ClientSession(headers=headers) as client:
                async with client.post(url, json=payload) as response:
                    resp_json = await response.json()
                    if response.status == 200:
                        logging.info(f"Successfully sent message \x1b[38;5;9m({token[:59]})\x1b[0m")
                    elif response.status == 401:
                        logging.info(f"Invalid account \x1b[38;5;9m({token[:59]})\x1b[0m")
                        self.tokens.remove(token)
                        return False
                    elif response.status == 403:
                        if resp_json.get("code") == 40003:
                            logging.info(f"Ratelimited \x1b[38;5;9m({token[:59]})\x1b[0m")
                            await asyncio.sleep(self.delay)
                            return await self.direct_message(token, channel)
                        elif resp_json.get("code") == 50007:
                            logging.info(f"User has DMs disabled \x1b[38;5;9m({token[:59]})\x1b[0m")
                        elif resp_json.get("code") == 40002:
                            logging.info(f"Locked account \x1b[38;5;9m({token[:59]})\x1b[0m")
                            self.tokens.remove(token)
                            return False
                    elif response.status == 429:
                        logging.info(f"Ratelimited \x1b[38;5;9m({token[:59]})\x1b[0m")
                        await asyncio.sleep(self.delay)
                        return await self.direct_message(token, channel)
                    else:
                        return False
        except Exception:
            return await self.direct_message(token, channel)

    async def send(self, token: str, user: str) -> None:
        """
        Sends a DM message to a user by creating a DM channel and sending the message.

        Args:
            token (str): The Discord token.
            user (str): The user ID to DM.
        """
        channel = await self.create_dm(token, user)
        if channel is False:
            # Try with a random token if DM creation fails
            return await self.send(random.choice(self.tokens), user)
        response = await self.direct_message(token, channel)
        if response is False:
            return await self.send(random.choice(self.tokens), user)

    async def start(self) -> None:
        """
        Main entry point to process tokens, join server, scrape users, and send messages.
        """
        if not self.tokens:
            logging.info("No tokens loaded.")
            sys.exit()

        # Login with all tokens
        async with TaskPool(1_000) as pool:
            for token in self.tokens:
                if self.tokens:
                    await pool.put(self.login(token))
                else:
                    self.stop()

        if not self.tokens:
            self.stop()

        print()
        logging.info("Joining server.")
        print()

        # Join the server using all tokens
        async with TaskPool(1_000) as pool:
            for token in self.tokens:
                if self.tokens:
                    await pool.put(self.join(token))
                    if self.delay:
                        await asyncio.sleep(self.delay)
                else:
                    self.stop()

        if not self.tokens:
            self.stop()

        # Scrape users from the joined server
        scraper = Scraper(
            token=self.tokens[0],
            guild_id=self.guild_id,
            channel_id=self.channel_id
        )
        self.users = scraper.fetch()

        print()
        logging.info(f"Successfully scraped \x1b[38;5;9m{len(self.users)}\x1b[0m members")
        logging.info("Sending messages.")
        print()

        if not self.tokens:
            self.stop()

        # Send messages to all scraped users
        async with TaskPool(1_000) as pool:
            for user in self.users:
                if self.tokens:
                    await pool.put(self.send(random.choice(self.tokens), user))
                    if self.delay:
                        await asyncio.sleep(self.delay)
                else:
                    self.stop()


if __name__ == "__main__":
    if not os.getenv('requirements'):
        subprocess.Popen(['start', 'start.bat'], shell=True)
        sys.exit()

    clear_screen()
    client = Discord()
    asyncio.get_event_loop().run_until_complete(client.start())
