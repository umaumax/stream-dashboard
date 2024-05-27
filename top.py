#!/usr/bin/env python3

from datetime import datetime
import os
import re
import subprocess
import asyncio
import argparse
import sys

import pandas as pd
from result import Ok, Err, Result, is_ok, is_err
import aiofiles


def get_top_output() -> str:
    result = subprocess.run(['top', '-b', '-n', '1'], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def get_file_creation_time(file_path) -> Result[datetime, str]:
    try:
        stat = os.stat(file_path)
        try:
            file_creation_time = datetime.fromtimestamp(stat.st_birthtime)
        except AttributeError:
            file_creation_time = datetime.fromtimestamp(stat.st_ctime)
        return Ok(file_creation_time)
    except Exception as e:
        return Err(f"🔥Error accessing file creation time: {str(e)}")


def get_top_time(current_date, line) -> Result[datetime, str]:
    match = re.match(
        r'top - (\d{2}):(\d{2}):(\d{2}) up (\d*) days, *(\d{1,2}):(\d{2})',
        line)
    if not match:
        return Err(
            f"🔥Unexpected format: Unable to find the top command execution time. at '{line}'")
    current_hour = int(match.group(1))
    current_minute = int(match.group(2))
    current_second = int(match.group(3))
    uptime_day = int(match.group(4))
    uptime_hour = int(match.group(5))
    uptime_minute = int(match.group(6))
    return Ok(datetime(current_date.year, current_date.month, current_date.day, current_hour,
                       current_minute, current_second, microsecond=0, tzinfo=None))


async def parse_top_output(f, base_datetime=None, follow=False) -> Result[dict, str]:
    process_head = False
    top_time = None
    processes = []
    if base_datetime is None:
        base_datetime_result = get_file_creation_time(f.name)
        if base_datetime_result.is_err():
            return base_datetime_result
        base_datetime = base_datetime_result.ok()

    while True:
        line = await f.readline()
        if not line:
            if not follow:
                break
            await asyncio.sleep(0.1)
            continue
        line = line.rstrip()
        # for debugging
        # print(line)
        if line.startswith("top -"):
            top_time_result = get_top_time(base_datetime, line)
            if top_time_result.is_err():
                return top_time_result
            top_time = top_time_result.ok()
        if line.startswith("  PID"):
            process_head = True
            continue
        if not process_head:
            continue
        if process_head and not line:
            # reaeched the end to top output
            # NOTE: In the top -n command, a blank line is not output until
            # after the next command, so the exit decision is delayed by one.
            break

        parts = re.split(r'\s+', line.strip())
        if len(parts) < 12:
            return Err(f"🔥Failed to parse '{line}'")
        pid = parts[0]
        command = ' '.join(parts[11:])
        process_info = {
            'PID': pid,
            'USER': parts[1],
            'PR': parts[2],
            'NI': parts[3],
            'VIRT': parts[4],
            'RES': parts[5],
            'SHR': parts[6],
            'S': parts[7],
            '%CPU': parts[8],
            '%MEM': parts[9],
            'TIME+': parts[10],
            'COMMAND': command,
            'unixtime': top_time,
            'key': f'{pid} {command}',
        }
        processes.append(process_info)
    return Ok(processes)


async def stream_top_output_to_jsonl(input_filepath, output_filepath, follow=False) -> Result[type(()), str]:
    async with aiofiles.open(input_filepath, mode='r') as f_in:
        creation_time_result = get_file_creation_time(input_filepath)
        if creation_time_result.is_err():
            return creation_time_result
        creation_time = creation_time_result.ok()
        async with aiofiles.open(output_filepath, mode='w') as f_out:
            while True:
                parsed_data_result = await parse_top_output(
                    f_in, base_datetime=creation_time, follow=follow)
                if parsed_data_result.is_err():
                    return parsed_data_result
                parsed_data = parsed_data_result.ok()
                if len(parsed_data) == 0:
                    break
                print(parsed_data)
                columns = parsed_data[0].keys()
                df = pd.DataFrame(parsed_data, columns=columns)
                print(df)
                await f_out.write(df.to_json(orient='records') + '\n')
                await f_out.flush()
        return Ok(())


async def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-in',
        '--input-filepath',
        type=argparse.FileType(), default='/dev/stdin')
    parser.add_argument(
        '-o',
        '--output-filepath',
        default='/dev/stdout')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument(
        '-f',
        '--follow',
        action='store_true',
        help='output appended data as the file grows')
    parser.add_argument('args', nargs='*')  # any length of args is ok

    args, extra_args = parser.parse_known_args()

    result = await stream_top_output_to_jsonl(
        args.input_filepath.name,
        args.output_filepath, follow=args.follow)
    return result


if __name__ == '__main__':
    result = asyncio.run(main())
    if result.is_err():
        print(result.err(), file=sys.stderr)
        sys.exit(1)
