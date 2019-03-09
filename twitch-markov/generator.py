import asyncio
import os
import itertools

import aiomysql

BATCH_SIZE = 10000

def run():
    asyncio.get_event_loop().run_until_complete(run_())

async def run_():
    pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"), port=3306, 
                                           user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"), 
                                           db=os.getenv("MYSQL_DATABASE"), cursorclass=aiomysql.cursors.DictCursor,
                                           charset="utf8mb4", loop=asyncio.get_event_loop(),
                                           autocommit=True)

    async with pool.acquire() as database:
        async with database.cursor() as cursor:
            await cursor.execute("DROP TABLE IF EXISTS Markov")
            await cursor.execute("""
                CREATE TABLE Markov (
                    id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
                    before1 VARCHAR(1000) NOT NULL,
                    before2 VARCHAR(1000) NOT NULL,
                    word VARCHAR(1000) NOT NULL,
                    weight INT NOT NULL,
                    UNIQUE KEY(before1(10), before2(10), word(10))
                ) CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
            """)


    current_batch = 0

    async with pool.acquire() as database:
        while True:
            print("BATCH {}".format(current_batch))
            print("  Loading")
            async with database.cursor() as cursor:
                await cursor.execute("SELECT message FROM Messages LIMIT %s OFFSET %s", [BATCH_SIZE, (current_batch) * BATCH_SIZE])

                data = await cursor.fetchall()

            print("  Parsing")

            messages = [message["message"] for message in data]

            if len(messages) == 0:
                break
        
            
            markov = []

            for message in messages:
                words = split_words(message)

                for (a, b, c) in iterate_triplets(itertools.chain(iter([None, None]), iter(words), iter([None, None]))):
                    markov.append((a or "", b or "", c or ""))
                    
            print("  Storing")
            async with database.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO Markov 
                        (before1, before2, word, weight) 
                    VALUES """
                        + ",".join(["(%s, %s, %s, 1)"] * len(markov)) + 
                    """ON DUPLICATE KEY UPDATE weight = weight + 1;
                """, [v for triplet in markov for v in triplet])




            current_batch += 1


    print("DONE")

    pool.close()


def split_words(s):
    start = 0
    words = []

    at_word = False

    # Hack to ensure last word is handled
    s += " "

    for i, c in enumerate(s):
        if c.isalnum() and not at_word:
            at_word = True
            start = i
            continue
        elif c.isalnum() and at_word:
            continue
        elif not c.isalnum() and at_word:
            at_word = False
            words.append(s[start:i])

        if not c.isspace():
            words.append(str(c))

    return words

def iterate_triplets(iterable):
    a, b, c = itertools.tee(iterable, 3)
    next(b)
    next(c)
    next(c)

    return zip(a, b, c)

