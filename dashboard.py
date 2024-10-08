#!/usr/bin/env python3

from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
import json
import os
import traceback

import uuid
import aiofiles
import streamlit as st
import streamlit_authenticator as stauth
import yaml
import pandas as pd
from tinydb import TinyDB
import plotly
import plotly.subplots
import plotly.express as px
import plotly.graph_objects as go

from file_watcher import FileWatcher, FileWatcherConst
import components

db = TinyDB("db.json")

st.set_page_config(
    page_title="Streamlit Dashboard App",
    layout="wide",
    initial_sidebar_state="collapsed")

st.title('Streamlit Dashboard')


async def wait_with_progress_bar(progress_bar, text, interval):
    N = 10
    sleep_duration = interval / N
    if sleep_duration >= 0.1:
        for i in range(0, N):
            await asyncio.sleep(sleep_duration)
            progress_bar.progress(
                (i + 1) / N, text='{} (⏱ {:.1f}/{:.1f}[s])'.format(text, sleep_duration * (i + 1), interval))
    else:
        await asyncio.sleep(interval)


async def update_table_data(table_name, col):
    interval_slider = st.sidebar.slider('update interval[s]', 1, 60, 1)
    table = db.table(table_name)
    cnt = 0
    progress_bar = col.progress(0, text='')
    chart = col.empty()
    while st.session_state.running:
        progress_text = "[{}] at {}".format(
            cnt, datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        progress_bar.progress(0, text=progress_text)
        try:
            data = table.all()
            if len(data) == 0:
                chart.error(f'Not Found Data: {table_name}')
            if table_name == 'memory_usage':
                update_memory_chart(chart, data)
            else:
                st.error(f'TODO: implement for {table_name}')
        except Exception as e:
            error_text = f'🔥 [Exception] update_table_data({table_name})\n{traceback.format_exc()}'
            print(error_text)
            chart.error(error_text)
        await wait_with_progress_bar(progress_bar, progress_text, interval_slider)
        cnt += 1

print('🌟 st.query_params: ', st.query_params)


async def load_ls_command():
    ls_interval = st.sidebar.slider('ls update interval[s]', 0.1, 10.0, 2.0)
    cnt = 0
    while st.session_state.running:
        with open('ls-result.log') as f:
            lines = f.readlines()

        df = pd.DataFrame({
            'line': lines,
            'link': [f'?line={line}' for line in lines],
        })
        # print(df)

        progress_text = "[{}] at {}".format(
            cnt, datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        with ls_placeholder.container(border=True):
            st.subheader("ls result")
            progress_bar = st.progress(0, text=progress_text)
            st.write(df)

            # examples
            st.dataframe(
                df,
                column_config={
                    "line": st.column_config.Column(
                        "line",
                    ),
                    "link": st.column_config.LinkColumn(
                        "link",
                        display_text="open"
                    ),
                },
            )
            for line in lines:
                st.link_button(f"{line}", f"?line={line}")
        await wait_with_progress_bar(progress_bar, progress_text, ls_interval)
        cnt += 1


def update_memory_chart(container, data):
    df = pd.DataFrame(data)
    df['Total'] = df.sum(axis=1)
    # NOTE: 移動平均線
    df['MA_5'] = df['memory_percent'].rolling(window=5).mean()
    df['datetime(utc)'] = pd.to_datetime(df['unixtime'], unit='s', utc=True)
    df['datetime(jst)'] = df['datetime(utc)'].dt.tz_convert('Asia/Tokyo')
    # print(df)
    fig = px.line(
        df,
        x='datetime(jst)',
        y=['memory_percent', 'MA_5'],
        title="メモリ使用量の推移")
    container.plotly_chart(fig)


def create_top_graph(df):
    # NOTE: for debugging
    # st.write(df)

    keys = df['key'].unique()
    # NOTE: filter meaningful logs
    df = df[(df['%CPU'] >= '5.0') | (df['%MEM'] >= '1.0')]

    # CPU Usage
    line_chart_tab, stacked_chart_tab = st.tabs(
        ["Line Chart", "Stacked Chart"])
    with line_chart_tab:
        cpu_fig = px.line(
            df,
            x='unixtime',
            y='%CPU',
            color='key',
            markers=True,
            title='CPU Usage Over Time')
        st.plotly_chart(cpu_fig)

    with stacked_chart_tab:
        fig = go.Figure()
        for key in keys:
            key_df = df[df['key'] == key]
            fig.add_trace(go.Scatter(
                x=key_df['unixtime'],
                y=key_df['%CPU'], stackgroup="%CPU", mode="lines+markers", name=key))
        fig.update_layout(title='Stacked Chart',
                          legend_traceorder='normal',
                          legend_title_text='key',
                          xaxis=dict(
                              title='unixtime',
                          ),
                          yaxis=dict(
                              title='%CPU',
                          ),
                          )
        st.plotly_chart(fig)

    # Memory Usage
    mem_fig = px.line(
        df,
        x='unixtime',
        y='%MEM',
        color='key',
        markers=True,
        title='Memory Usage Over Time')
    st.plotly_chart(mem_fig)


def create_component(df, decl):
    # 🌟自動追加のフィールド
    if 'unixtime' in df:
        try:
            df['datetime(utc)'] = pd.to_datetime(
                df['unixtime'], unit='s', utc=True)
        except pd._libs.tslibs.np_datetime.OutOfBoundsDatetime as e:
            df['datetime(utc)'] = pd.to_datetime(
                df['unixtime'], unit='ms', utc=True)
            df['unixtime'] = pd.to_datetime(df['unixtime'], unit='ms')
        df['datetime(jst)'] = df['datetime(utc)'].dt.tz_convert(
            'Asia/Tokyo')
    # df['Total'] = df.sum(axis=1)
    # NOTE: 移動平均線
    # field名を見て自動追加できると嬉しい
    title = decl['title'] if 'title' in decl else 'data'

    # dst: optional if None, {src}(MA_{window})
    def prepro_MA(df, src=None, window=5, dst=None):
        if not src:
            print(f"🔥[prepro_MA] Required arg 'src'")
            return
        if not dst:
            dst = f'{src}(MA_{window})'
        df[dst] = df[src].rolling(window=window).mean()
    funcs = decl['funcs']
    fig = None
    try:
        for func in funcs:
            func_name = func['name']
            if func_name == "prepro.MA":
                prepro_MA(df, **func['args'])
            elif func_name == "st.write":
                st.write(df)
            elif func_name == "st.dataframe":
                st.dataframe(df, **func["args"])
            elif func_name == "st.subheader":
                st.subheader(**func["args"])
            elif func_name == "st.metric":
                st.metric(**func["args"])
            elif func_name == "plotly.subplots.make_subplots":
                fig = plotly.subplots.make_subplots(**func['args'])
            elif func_name == "px.line":
                fig = px.line(df, **func['args'])
            elif func_name == "px.scatter":
                fig = px.scatter(df, **func['args'])
            elif func_name == "update_layout":
                fig.update_layout(**func["args"])
            elif func_name == "add_scatter":
                func["args"]["x"] = df[func["args"]["x"]]
                func["args"]["y"] = df[func["args"]["y"]]
                fig.add_scatter(**func["args"])
            elif func_name == "add_bar":
                func["args"]["x"] = df[func["args"]["x"]]
                func["args"]["y"] = df[func["args"]["y"]]
                fig.add_bar(**func["args"])
            elif func_name == "top":
                create_top_graph(df)
            else:
                st.error(f"🔥Unknown func.name '{func_name}'")
        if fig:
            st.plotly_chart(fig)
        jst_local_time = datetime.now(ZoneInfo("Asia/Tokyo"))
        if 'index' in df.columns:
            df.drop(['index'], axis='columns', inplace=True)
        st.download_button(
            label="Download data",
            data=df.to_json(),
            key=uuid.uuid4(),
            file_name=f"{jst_local_time.strftime('%Y%m%d_%H%M%S')}-{title}.json",
            mime="application/json"
        )
        if len(df.index) < 1000:
            with st.expander("data"):
                st.write(df)
    except Exception as e:
        error_text = f'🔥[Exception]\n{traceback.format_exc()}'
        print(error_text)
        st.error(error_text)


def transform_link_path(filepath):
    filepath = filepath.lstrip("./")
    return filepath.replace("/", "-").replace(".", "-")


async def load_json_data(json_container):
    cnt = 0
    inner_container = json_container.container()
    dashboard_target_path = os.getenv("DASHBOARD_PATH", "./dashboard")
    pattern = f'{dashboard_target_path}/**/*.decl.json'
    file_watcher = FileWatcher(pattern)
    containers = {}
    tasks = {}
    head_placeholder = inner_container.empty()
    head_placeholders = []
    while st.session_state.running:
        files = file_watcher.watch()
        head_placeholder.empty()
        with head_placeholder.container():
            st.write('Graph Hyper Links')
            for file in files:
                st.markdown(
                    f"- [{file}](#{transform_link_path(file)})")
        for file in files:
            status = files[file]['status']
            if status == FileWatcherConst.NEW:
                containers[file] = inner_container.empty()
                tasks[file] = None
            elif status == FileWatcherConst.UPDATED:
                containers[file].empty()
                if tasks[file]:
                    tasks[file].cancel()
                pass
            elif status == FileWatcherConst.UNCHANGED:
                continue
            elif status == FileWatcherConst.DELETED:
                containers[file].empty()
                continue
            else:
                st.error(f"Unknown status '{status}' at '{file}'")
                continue
            container = containers[file].container(border=True)
            with container:
                container.empty()
                st.header(file)
                async with aiofiles.open(file, mode='r') as f:
                    contents = await f.read()
                    json_data = json.loads(contents)
                    show_flag = st.checkbox(
                        "show plots",
                        value=True,
                        label_visibility="collapsed",
                        on_change=cleanup,
                        key=f'{file}')
                    if not show_flag:
                        continue
                    if 'data' in json_data:
                        df = pd.DataFrame(json_data['data'])
                    elif 'ref-data' in json_data:
                        basedir_path = os.path.dirname(file
                                                       if os.path.isabs(file) else os.path.realpath(file))
                        ref_file = json_data['ref-data']['file']
                        ref_file_full_path = os.path.join(
                            basedir_path, ref_file)
                        _, ext = os.path.splitext(ref_file)
                        if ext == '.json':
                            with open(ref_file_full_path) as f:
                                df = pd.DataFrame(json.load(f))
                        elif ext == '.jsonl':
                            task = asyncio.create_task(
                                async_file_load(ref_file_full_path, json_data, container))
                            tasks[file] = task
                            continue
                        else:
                            st.error(
                                f"'{ext}' Extension with unimplemented read function. '{ref_file_full_path}'")
                            continue
                    else:
                        st.error(
                            f'There is no "data" or "ref-data" field at {file}')
                        continue
                    create_component(df, json_data)
        await asyncio.sleep(1.0)
        cnt += 1
    await asyncio.gather(*tasks.values())


async def async_file_load(target_filepath, decl, container=st.empty()):
    try:
        cnt = 0
        data = []
        tmp_data = []
        async with aiofiles.open(target_filepath, mode='r') as f:
            updated = False
            cnt = 0
            while st.session_state.running:
                # NOTE: 1000データごともしくは終端データのタイミングで描画する
                line = await f.readline()
                if line:
                    cnt += 1
                    jsonl = json.loads(line)
                    tmp_data.append(jsonl)
                    updated = True
                    if cnt % 1000 > 0:
                        continue
                if not updated:
                    await asyncio.sleep(0.01)
                    continue

                updated = False
                data += tmp_data
                tmp_data = []

                # 1行1データの場合
                if isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                else:
                    # 1行複数データの場合
                    df_list = []
                    for entry in data:
                        temp_df = pd.DataFrame(entry)
                        df_list.append(temp_df)
                    df = pd.concat(df_list, ignore_index=True)

                # 'index'のカラムを自動的に付与する
                df.reset_index(inplace=True)
                with container:
                    create_component(df, decl)
    except asyncio.CancelledError as e:
        print(
            f"📒[asyncio.CancelledError]Task async_file_load {target_filepath} was cancelled {e}")
    except st.runtime.scriptrunner.script_runner.StopException as e:
        print(
            f"📒[streamlit.StopException]Task async_file_load {target_filepath} was cancelled {e}")
    except Exception as e:
        print(
            f"📒[Exception]Task async_file_load {target_filepath} was cancelled {e}")


def authenticate(config_filepath):
    config = []
    with open(config_filepath) as file:
        config = yaml.load(file, Loader=yaml.loader.SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
    )
    print(f'[📃] pre login')
    name, authentication_status, user_name = authenticator.login()
    print(f'[📃] post login')

    if authentication_status:
        with st.sidebar:
            st.write(f'Welcome *{st.session_state["name"]}*')
            authenticator.logout(location='sidebar')
        return True
    elif authentication_status is False:
        st.error("Username/password is incorrect")
        return False
    elif authentication_status is None:
        st.warning("Please enter your username and password")
        return False


if not authenticate('./streamlit-config.yaml'):
    print(f'[🛑] failed authentication')
    st.stop()

print(f'[✅] authenticated')

st.session_state.message = ''


def setup_sidebar():
    start = st.sidebar.button('start(TODO: implement)')
    stop = st.sidebar.button('stop(TODO: implement)')

    if 'running' not in st.session_state:
        st.session_state.running = True

    if start:
        st.session_state.running = True

    if stop:
        st.session_state.running = False


setup_sidebar()

# disk_col1, disk_col2 = st.columns(2)
# with disk_col1.container(border=True):
# components.create_disk_usage_layout()
#
# with disk_col2.container(border=True):
# base_directory = '.'
# components.create_subdirectories_usage_layout(base_directory)


slate = st.empty()
body = slate.container()


def cleanup():
    print('[🧹] cleanup')
    slate.empty()


json_col = body.empty()
json_container = json_col.container()

app_col = body.empty()
app_container = app_col.container()

# col1, col2 = body.columns(2)
# ls_placeholder = col1.empty()
# col2.subheader("memory usage")
# memory_col = col2.container(border=True)


async def main():
    print('[💡] main called')
    tasks = []
    # e.g.
    # tasks.append(asyncio.create_task( update_table_data( 'memory_usage', memory_col)))
    # tasks.append(asyncio.create_task(load_ls_command()))
    tasks.append(asyncio.create_task(load_json_data(json_container)))
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError as e:
        print('[main]', e)
        pass

if __name__ == '__main__':
    if st.session_state.running:
        asyncio.run(main())
