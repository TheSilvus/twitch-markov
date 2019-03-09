import asyncio
import os
import itertools

import aiomysql



def run():
    asyncio.get_event_loop().run_until_complete(run_())

async def run_():
    database = await aiomysql.connect(host=os.getenv("MYSQL_HOST"), port=3306, 
                                           user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"), 
                                           db=os.getenv("MYSQL_DATABASE"), cursorclass=aiomysql.cursors.DictCursor,
                                           charset="utf8mb4", loop=asyncio.get_event_loop(),
                                           autocommit=True)

    a = ""
    b = ""

    string = ""

    while True:
        async with database.cursor() as cursor:
            await cursor.execute("SELECT word FROM Markov WHERE before1=%s AND before2=%s ORDER BY weight*RAND() DESC LIMIT 1", [a, b])

            result = await cursor.fetchone()

        if result == None:
            print("ERROR")
            break
        elif result["word"] == "":
            break


        string += " " + result["word"]

        a = b
        b = result["word"]
        
    print(string)
        

