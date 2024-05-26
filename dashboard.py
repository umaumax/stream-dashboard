#!/usr/bin/env python3

from datetime import datetime
import asyncio
import json
import os

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

from file_watcher import FileWatcher
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


async def get_memory_usage():
    memory_interval = st.sidebar.slider(
        'memory usage update interval[s]', 1, 60, 1)
    memory_usage_table = db.table('memory_usage')
    cnt = 0
    progress_bar = memory_col.progress(0, text='')
    memory_chart = memory_col.empty()
    while st.session_state.running:
        progress_text = "[{}] at {}".format(
            cnt, datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        progress_bar.progress(0, text=progress_text)
        try:
            data = memory_usage_table.all()
            update_memory_chart(memory_chart, data)
        except Exception as e:
            print('🔥 get_memory_usage: ', e)
            st.error(f'🔥 get_memory_usage: {e}')
        await wait_with_progress_bar(progress_bar, progress_text, memory_interval)
        cnt += 1

print('🌟', st.query_params)


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


async def load_json_data():
    cnt = 0
    inner_container = json_container.empty()
    inner_container2 = json_container.empty()
    pattern = './dashboard/**/*.json'
    file_watcher = FileWatcher(pattern)
    while st.session_state.running:
        files = file_watcher.watch()
        with inner_container.container(border=True):
            for file in files:
                st.write(file)
                async with aiofiles.open(file, mode='r') as f:
                    contents = await f.read()
                    json_data = json.loads(contents)
                    # lines = await f.readlines()
                    # st.text_area("Output", lines)
                    # st.code("".join(lines))
                    df = pd.DataFrame(json_data['data'])
                    # 🌟自動追加のフィールド
                    if 'unixtime' in df:
                        df['datetime(utc)'] = pd.to_datetime(
                            df['unixtime'], unit='s', utc=True)
                        df['datetime(jst)'] = df['datetime(utc)'].dt.tz_convert(
                            'Asia/Tokyo')
                    # df['Total'] = df.sum(axis=1)
                    # NOTE: 移動平均線
                    # field名を見て自動追加できると嬉しい

                    # dst: optional if None, {src}(MA_{window})
                    def prepro_MA(df, src=None, window=5, dst=None):
                        if not src:
                            print(f"🔥[prepro_MA] Required arg 'src'")
                            return
                        if not dst:
                            dst = f'{src}(MA_{window})'
                        df[dst] = df[src].rolling(window=window).mean()
                    funcs = json_data['funcs']
                    fig = None
                    for func in funcs:
                        func_name = func['name']
                        # print(func_name)
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
                        else:
                            print(f"🔥Unknown func.name '{func_name}'")
                    if fig:
                        st.plotly_chart(fig)
                    with st.expander("data"):
                        st.write(df)
        # with inner_container2.container(border=True):
            # json_data = {
            # "data": [
            # {"x": [1, 2, 3, 4, 5], "y": [2, 13, 5, 7, 11], "z": [1, 2, 5, 6, 7],
            # "mode": "markers", "name": "Series 1"},
            # {"x": [2, 3, 4, 5, 6], "y": [3, 4, 36, 8, 12], "z": [10, 12, 15, 16, 17],
            # "mode": "lines", "name": "Series 2"}
            # ],
            # "args": {
            # "x": 'x',
            # "y": ['y', 'z'],
            # "title": "Plotly Chart",
            # }
            # }
            # df = json_data['data']
            # fig = px.line(
            # df,
            # **json_data['args'])
            # st.plotly_chart(fig)

            # table
            # df = pd.DataFrame({
            # 'line': ['hoge', 'fuga'],
            # 'link': ['a', 'b'],
            # })
            # st.write(df)

            # json_data = {
            # "data": {
            # "unixtime": [1716125388.0, 1716125389.0, 1716125390.0, 1716125391.0, 1716125392.0],
            # "memory_percent": [60.0, 10.0, 15.0, 0.0, -15.0],
            # "hoge": [12.0, 23.0, 10.0, 8.0, 20.0],
            # },
            # "px.line": {
            # "x": "unixtime",
            # "y": ["memory_percent", "hoge", "MA_2"],
            # "title": "メモリ使用量の推移"
            # },
            # "update_layout": {
            # "yaxis": {"title": "usage"}
            # }
            # }
            # st.write(json_data['data'])
            # df = pd.DataFrame(json_data['data'])
            # df['unixtime'] = pd.to_datetime(
            # df['unixtime'], unit='s', utc=True).dt.tz_convert('Asia/Tokyo')
            # # df['Total'] = df.sum(axis=1)
            # # NOTE: 移動平均線
            # df['MA_2'] = df['memory_percent'].rolling(window=2).mean()
            # fig = px.line(
            # df,
            # **json_data["px.line"])
            # fig.update_layout(**json_data["update_layout"])
            # st.plotly_chart(fig)

            # df = px.data.iris()
            # print(df)
            # df = pd.DataFrame({
            # 'sepal_length': [0.1, 0.4, 1.2, 2.1, -1.9, 1],
            # 'sepal_width': [1, 2, 4, 8, 10, 3],
            # 'species': ['a', 'b', 'a', 'c', 'b', 'b'],
            # })
            # fig = px.scatter(df, x="sepal_length", y="sepal_width", color="species",
            # title="Automatic Labels Based on Data Frame Column Names")
            # st.plotly_chart(fig)

        print(files)
        await asyncio.sleep(1.0)
        cnt += 1


async def load_app_log():
    cnt = 0
    app_chart = app_container.empty()
    data = []
    tmp_data = []
    # 🔥初回は読み取れるまで全部読み取る???
    # 🌟配列のappendではなく、グラフの作成などに時間がかかっている疑惑....
    # 🌟jsonl拡張子のほうがよさそう
    async with aiofiles.open('app.log', mode='r') as f:
        updated = False
        cnt = 0
        while st.session_state.running:
            # 💡: ファイルのopen状態に限らず、新しい行が読めない場合は''(空の文字列)が返される
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

            df = pd.DataFrame(data)
            # print(df)
            # UTC
            df['time'] = pd.to_datetime(df['unixtime'], unit='s')
            # JTC
            df['time'] = pd.to_datetime(
                df['unixtime'], unit='s', utc=True).dt.tz_convert('Asia/Tokyo')
            # 🔥軸をcntにする場合とtimeにする場合で切り替えができるとよい???

            # 'index'のカラムが自動的に付与される
            df.reset_index(inplace=True)
            print(df)

            # total_fizz = df['fizz'].sum()
            # total_buzz = df['buzz'].sum()
            # total_fizzbuzz = df['fizzbuzz'].sum()

            fig = plotly.subplots.make_subplots()

            fig.add_trace(
                go.Bar(
                    name='Fizz',
                    x=df['index'],  # x=df['time'], とする?
                    y=df['fizz'],
                    marker=dict(
                        color='rgba(50, 171, 96, 0.6)')))
            fig.add_trace(
                go.Bar(
                    name='Buzz',
                    x=df['index'],
                    y=df['buzz'],
                    marker=dict(
                        color='rgba(55, 128, 191, 0.6)')))
            fig.add_trace(
                go.Bar(
                    name='FizzBuzz',
                    x=df['index'],
                    y=df['fizzbuzz'],
                    marker=dict(
                        color='rgba(219, 64, 82, 0.6)')))

            fig.add_trace(
                go.Scatter(
                    x=df['index'],
                    y=df['fizz'],
                    mode='lines+markers',
                    name='Fizz',
                    line=dict(
                        color='green')))
            fig.add_trace(
                go.Scatter(
                    x=df['index'],
                    y=df['buzz'],
                    mode='lines+markers',
                    name='Buzz',
                    line=dict(
                        color='blue')))
            fig.add_trace(
                go.Scatter(
                    x=df['index'],
                    y=df['fizzbuzz'],
                    mode='lines+markers',
                    name='FizzBuzz',
                    line=dict(
                        color='red')))

            fig.update_layout(title='FizzBuzz Data Visualization',
                              xaxis_title='Time',
                              yaxis_title='Count',
                              barmode='stack')

            app_chart.plotly_chart(fig)


def authenticate():
    # ユーザーの資格情報取得
    config = []
    with open('streamlit-config.yaml') as file:
        config = yaml.load(file, Loader=yaml.loader.SafeLoader)

    # 認証
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
    )
    name, authentication_status, user_name = authenticator.login()

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


if not authenticate():
    st.stop()

st.session_state.message = ''


def setup_sidebar():
    start = st.sidebar.button('start')
    stop = st.sidebar.button('stop')

    if 'running' not in st.session_state:
        st.session_state.running = True

    if start:
        st.session_state.running = True

    if stop:
        st.session_state.running = False


setup_sidebar()

top_col = st.container()
with top_col:
    def load_jsonl(file_path):
        data = []
        with open(file_path, 'r') as file:
            for line in file:
                data.append(json.loads(line))
        return data

    file_path = 'top.jsonl'  # 🔥適切なパスに変更
    data = load_jsonl(file_path)

    df_list = []
    for entry in data:
        temp_df = pd.DataFrame(entry)
        df_list.append(temp_df)
    df = pd.concat(df_list, ignore_index=True)

    df['unixtime'] = pd.to_datetime(df['unixtime'], unit='ms')
    keys = df['key'].unique()

    tab1, tab2 = st.tabs(["普通のグラフ", "積み上げグラフ"])
    with tab1:
        # cpu_fig = go.Figure()
        # for key in keys:
        # print('🔑', key)
        # key_df = df[df['key'] == key]
        # cpu_fig.add_trace(go.Scatter(
        # x=key_df['unixtime'],
        # y=key_df['%CPU'], mode="lines+markers", name=key))
        cpu_fig = px.line(
            df,
            x='unixtime',
            y='%CPU',
            color='key',
            markers=True,
            title='CPU Usage Over Time')
        # cpu_fig.update_layout(title='CPU Usage Over Time')
        st.plotly_chart(cpu_fig)

    # 積み上げ
    with tab2:
        fig = go.Figure()
        # for key in keys[::-1]:  # reverse
        for key in keys:
            print('🔑', key)
            key_df = df[df['key'] == key]
            fig.add_trace(go.Scatter(
                x=key_df['unixtime'],
                y=key_df['%CPU'], stackgroup="%CPU", mode="lines+markers", name=key))
        fig.update_layout(title='Stacked Line Chart')
        fig.update_layout(legend_traceorder='normal')
        fig.update_layout(legend_title_text='key')
        fig.update_layout(
            xaxis=dict(
                title='unixtime',
            ),
            yaxis=dict(
                title='%CPU',
            ),
        )
        st.plotly_chart(fig)

    mem_fig = px.line(
        df,
        x='unixtime',
        y='%MEM',
        color='key',
        markers=True,
        title='Memory Usage Over Time')
    st.plotly_chart(mem_fig)

json_col = st.empty()

with json_col:
    st.subheader("json")
    json_container = st.container(border=True)

app_col = st.empty()

with app_col:
    st.subheader("app")
    app_container = st.container(border=True)

col1, col2 = st.columns(2)

with col1:
    ls_placeholder = st.empty()

with col2:
    st.subheader("メモリ使用量")
    memory_col = st.container(border=True)


disk_col1, disk_col2 = st.columns(2)
with disk_col1.container(border=True):
    components.create_disk_usage_layout()


def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


@ st.cache_data(ttl=60)
def get_subdirectories_size(directory):
    print('🔥: call get_subdirectories_size')
    subdirs = [
        os.path.join(
            directory,
            d) for d in os.listdir(directory) if os.path.isdir(
            os.path.join(
                directory,
                d))]
    sizes = {os.path.basename(subdir): get_directory_size(subdir)
             for subdir in subdirs}
    return sizes


if st.button("🔄", key='get_subdirectories_size',
             on_click=get_subdirectories_size.clear):
    get_subdirectories_size.clear()


with disk_col2.container(border=True):
    main_directory = "/Users/uma/Pictures/"
    dir_sizes = get_subdirectories_size(main_directory)

    dir_sizes_gb = {k: v / (1024**3) for k, v in dir_sizes.items()}

    fig = go.Figure(
        data=[
            go.Bar(
                x=list(
                    dir_sizes_gb.keys()), y=list(
                        dir_sizes_gb.values()))])

    fig.update_layout(
        title="ディレクトリごとのディスク使用量",
        xaxis_title="ディレクトリ",
        yaxis_title="使用量 (GB)",
        template="plotly_white"
    )
    st.plotly_chart(fig)

with st.container():
    expand = st.expander("My label")
    expand.write("Inside the expander.")
    pop = st.popover("Button label")
    pop.checkbox("Show all")


async def main():
    print('[💡] main called')
    tasks = []
    tasks.append(asyncio.create_task(get_memory_usage()))
    tasks.append(asyncio.create_task(load_ls_command()))
    tasks.append(asyncio.create_task(load_app_log()))
    tasks.append(asyncio.create_task(load_json_data()))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    if st.session_state.running:
        asyncio.run(main())
