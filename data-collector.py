#!/usr/bin/env python3
import json
import logging
import psutil
import time
import subprocess
import asyncio
from tinydb import TinyDB, Query
import coloredlogs
import inspect

db = TinyDB("db.json")

logger = logging.getLogger(__name__)
coloredlogs.install(
    level='DEBUG',
    logger=logger,
    fmt='%(asctime)s %(name)8s[%(process)d] %(levelname)-5s [%(filename)s:%(lineno)d - %(funcName)20s()] %(message)s')

memory_interval = 1
ls_interval = 1


async def get_memory_usage():
    memory_usage_table = db.table('memory_usage')
    while True:
        memory_percent = psutil.virtual_memory().percent
        unix_timestamp = time.time()
        data = {'unixtime': unix_timestamp, 'memory_percent': memory_percent}
        memory_usage_table.insert(data)
        logger.debug(data)
        await asyncio.sleep(memory_interval)


async def run_ls_command():
    while True:
        result = subprocess.run(['ls'], capture_output=True, text=True)
        lines = result.stdout.rstrip('\r\n').split('\n')
        logger.debug(lines)
        with open('ls-result.log', mode='w') as f:
            f.writelines('\n'.join(lines))
        await asyncio.sleep(ls_interval)


async def parse_app_log():
    cnt = 0
    with open('app.log', mode='w') as f:
        def write_json_data(data):
            f.write(json.dumps(data) + '\n')
            f.flush()

        var_counts = {'fizz': 0, 'buzz': 0, 'fizzbuzz': 0}
        while True:
            # generate a dummy input line
            line = f'[{cnt}] -'
            if cnt % 3 == 0 and cnt % 5 == 0:
                line = f'[{cnt}] fizzbuzz'
            elif cnt % 3 == 0:
                line = f'[{cnt}] fizz'
            elif cnt % 5 == 0:
                line = f'[{cnt}] buzz'

            if 'fizzbuzz' in line:
                var_counts['fizzbuzz'] += 1
            elif 'fizz' in line:
                var_counts['fizz'] += 1
            elif 'buzz' in line:
                var_counts['buzz'] += 1

            unix_timestamp = time.time()
            data = {'unixtime': unix_timestamp} | var_counts
            write_json_data(data)
            logger.debug(data)

            await asyncio.sleep(0.5)
            cnt += 1


async def main():
    tasks = []
    tasks.append(asyncio.create_task(get_memory_usage()))
    tasks.append(asyncio.create_task(run_ls_command()))
    tasks.append(asyncio.create_task(parse_app_log()))
    await asyncio.gather(*tasks)

asyncio.run(main())
