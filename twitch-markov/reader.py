import asyncio
import datetime
import logging
import re
import os

import aiohttp
import aiomysql

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


MESSAGE_REGEX = re.compile(":([a-z0-9_]+)![a-z0-9_]+@[a-z0-9_]+.tmi.twitch.tv PRIVMSG #([a-z0-9_]+) :(.+)")

class TwitchConnection:
    def __init__(self, nick, password, loop=asyncio.get_event_loop()):
        self.nick = nick
        self.password = password
        self.loop = loop

        self.joined = set()

        self.message_cache = []

    def start(self):
        self.loop.run_until_complete(self.connect())
        self.loop.run_until_complete(self.read_loop())

    async def connect(self):
        await self.connect_database()

        self.reader, self.writer = await asyncio.open_connection("irc.chat.twitch.tv", 6667)

        self.send("PASS {}".format(self.password))
        self.send("NICK {}".format(self.nick))


    async def connect_database(self):
        self.database = await aiomysql.connect(host=os.getenv("MYSQL_HOST"), port=3306, 
                                               user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"), 
                                               db=os.getenv("MYSQL_DATABASE"), cursorclass=aiomysql.cursors.DictCursor,
                                               charset="utf8mb4", loop=self.loop)

        async with self.database.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS Messages (
                    id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
                    time TIMESTAMP NOT NULL,
                    channel VARCHAR(25) NOT NULL,
                    sender VARCHAR(25) NOT NULL,
                    message VARCHAR(1000) NOT NULL
                ) CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
            """)
            await cur.execute("""ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;""")
        await self.database.commit()


    def send(self, s):
        LOG.debug("> {}".format(s))
        self.writer.write((s + "\n").encode())

    async def receive(self):
        line = await self.reader.readline()
        line = line.decode().strip()
        LOG.debug("< {}".format(line))
        return line



    async def read_loop(self):
        self.loop.create_task(self.message_push_loop())
        self.loop.create_task(self.twitch_join_loop())
        while not self.reader.at_eof():
            line = await self.receive()

            if line.startswith("PING"):
                self.send("PONG :tmi.twitch.tv")

            match = MESSAGE_REGEX.match(line)
            if match:
                await self.on_message(match.group(1), match.group(2), match.group(3))
        LOG.info("Connection closed")


    def join(self, channel):
        self.send("JOIN #{}".format(channel))
        self.joined.add(channel)
    def part(self, channel):
        self.send("PART #{}".format(channel))
        self.joined.remove(channel)

    def message(self, channel, message):
        self.send("PRIVMSG #{} :{}".format(channel, message))

    async def on_message(self, sender, channel, content):
        self.message_cache.append((datetime.datetime.now(), sender, channel, content))

    async def message_push_loop(self):
        while not self.reader.at_eof():
            await asyncio.sleep(1)
            messages = self.message_cache
            self.message_cache = []

            message_count = len(messages)
            if message_count == 0:
                continue
            messages = [value for message in messages for value in message]

            LOG.info("Inserting {} messages".format(message_count))

            async with self.database.cursor() as cursor:
                sql = "INSERT INTO Messages (time, sender, channel, message) VALUES " + ",".join(["(%s, %s, %s, %s)"] * message_count) + ";"

                await cursor.execute(sql, messages)
            await self.database.commit()

    async def twitch_join_loop(self):
        while not self.reader.at_eof():
            async with aiohttp.ClientSession() as session:
                headers = headers={"Client-ID": os.getenv("TWITCH_CLIENT_ID")}
                async with session.get("https://api.twitch.tv/helix/streams", params={'first': '100'}, headers=headers) as response:
                    content = await response.json()

                user_ids = [stream["user_id"] for stream in content["data"]]

                async with session.get("https://api.twitch.tv/helix/users?" + "&".join(["id={}".format(i) for i in user_ids]), headers=headers) as response:
                    content = await response.json()

                user_names = [stream["login"] for stream in content["data"]]


            for user_name in user_names:
                if user_name in self.joined:
                    continue
                LOG.info("Joining {}".format(user_name))
                self.join(user_name)
                await asyncio.sleep(1)

            LOG.info("Finished joining; now in {} channels".format(len(self.joined)))

            await asyncio.sleep(60)



def run():
    connection = TwitchConnection(os.getenv("TWITCH_BOT_USER"), os.getenv("TWITCH_BOT_TOKEN"), loop=asyncio.get_event_loop())
    connection.start()


