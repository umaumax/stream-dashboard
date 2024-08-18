#!/usr/bin/env python3

import os
import json
from collections import defaultdict

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

st.title("Chrome Trace Viewer")

# dummy data
trace_data = {
    "traceEvents": [
        {"name": "Event A", "ts": 1000, "ph": "B", "pid": 101, "tid": 101},
        {"name": "Event A", "ts": 1200, "ph": "B", "pid": 101, "tid": 101},
        {"name": "Event A", "ts": 1400, "ph": "E", "pid": 101, "tid": 101},
        {"name": "Event A", "ts": 1500, "ph": "E", "pid": 101, "tid": 101},
        {"name": "Event B", "ts": 1200, "ph": "B", "pid": 101, "tid": 101},
        {"name": "Event B", "ts": 1700, "ph": "E", "pid": 101, "tid": 101},
        {"name": "Event A", "ts": 2000, "ph": "B", "pid": 101, "tid": 102},
        {"name": "Event A", "ts": 2500, "ph": "E", "pid": 101, "tid": 102},
        {"name": "Event B", "ts": 2200, "ph": "B", "pid": 101, "tid": 102},
        {"name": "Event B", "ts": 2700, "ph": "E", "pid": 101, "tid": 102},
        {"name": "Event C", "ts": 1200, "ph": "B", "pid": 102, "tid": 103},
        {"name": "Event C", "ts": 1700, "ph": "E", "pid": 102, "tid": 103},
    ]
}

uploaded_file = st.file_uploader(
    "Upload your Chrome Trace JSON file",
    type="json")

if uploaded_file is not None:
    trace_data = json.load(uploaded_file)
else:
    filepath = './trace.json'
    if os.path.isfile(filepath):
        with open(filepath) as f:
            trace_data = json.load(f)


def process_trace_data(trace_data):
    events = trace_data["traceEvents"]
    event_begin_working_stacks = defaultdict(list)
    event_end_working_stacks = defaultdict(list)
    event_stacks = defaultdict(list)
    depth = defaultdict(int)

    index = 0
    while True:
        event = None
        if index < len(events):
            event = events[index]
        working_stack_flag = False
        for (pid, tid, name), event_end_working_stack in event_end_working_stacks.items():
            if event is not None and event["tid"] != tid:
                continue
            if len(event_end_working_stack) == 0:
                continue
            if event is None or event["ts"] > event_end_working_stack[-1]["ts"] + \
                    event_end_working_stack[-1]["dur"]:
                event = event_end_working_stack.pop()
                event["ph"] = "E"
                event["ts"] = event["ts"] + event["dur"]
                working_stack_flag = True
                break
        if not working_stack_flag:
            index += 1
        if event is None:
            break
        key = (event["pid"], event["tid"], event["name"])
        tid = event["tid"]
        # print(event)
        if event["ph"] == "B":
            event_begin_working_stacks[key].append(
                {"start": event["ts"], "end": None, "depth": depth[tid]})
            depth[tid] += 1
        elif event["ph"] == "E":
            if event_begin_working_stacks[key] and event_begin_working_stacks[key][-1]["end"] is None:
                event_begin_working_stacks[key][-1]["end"] = event["ts"]
                event_stacks[key].append(event_begin_working_stacks[key].pop())
                depth[tid] -= 1
            else:
                print(f'[WARN] There is no begin event...: f{key=}')
        elif event["ph"] == "X":
            event_begin_working_stacks[key].append(
                {"start": event["ts"], "end": None, "depth": depth[tid]})
            event_end_working_stacks[key].append(event)
            depth[tid] += 1
        else:
            print(f'[WARN] Unknown event f{event}')
            pass

    final_stack = []
    for (pid, tid, name), events in event_stacks.items():
        stack = []
        events.sort(key=lambda x: x["start"])
        for e in events:
            if e["end"] is not None:
                stack.append({
                    "pid": pid,
                    "tid": tid,
                    "name": name,
                    "start": e["start"],
                    "end": e["end"],
                    "duration": e["end"] - e["start"],
                    "y": -tid * 1000 - e['depth'],  # NOTE: ソートさせるための計算
                })
        final_stack.extend(stack)

    return final_stack


df = pd.DataFrame(process_trace_data(trace_data))

# NOTE: 0基準にする
df['start'] -= df['start'].min()
x = df['y']
y = df['duration']
base = df['start']

fig = px.bar(df,
             x='duration', y='y',
             base='start',
             text='name',
             color='name',
             orientation='h',
             )
fig.update_xaxes(
    showgrid=True,
)
fig.update_layout(
    yaxis_title="tid",
    bargap=0,
    yaxis=dict(
        tickvals=df['y'],
        ticktext=df['tid'],
    )
)

st.plotly_chart(fig)
