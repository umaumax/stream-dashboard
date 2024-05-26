#!/usr/bin/env python3
import psutil
import pandas as pd
import streamlit as st
import plotly
import plotly.subplots
import plotly.express as px
import plotly.graph_objects as go


def create_disk_usage_layout():
    @ st.cache_data(ttl=60)
    def get_disk_usage():
        print('🔥: call get_disk_usage')
        usage = psutil.disk_usage('/')
        return usage.total, usage.used, usage.free

    if st.button("🔄", key='get_disk_usage',
                 on_click=get_disk_usage.clear):
        get_disk_usage.clear()

    total, used, free = get_disk_usage()

    used_percentage = (used / total) * 100
    free_percentage = (free / total) * 100

    # 75%, 50GB
    if used_percentage > 75.0 or free < 50.0 * 1024**3:
        message = ':warning: Disk space is under pressure.'
        st.warning(message)
        st.toast(message, icon='🔥')

    total_text = f"total disk usage: {total / (1024**3):.2f} GB"
    used_text = f"used: {used / (1024**3):.2f} GB ({used_percentage:.2f}%)"
    free_text = f"free: {free / (1024**3):.2f} GB ({free_percentage:.2f}%)"

    labels = ['Used', 'Free']
    values = [used, free]
    colors = ['#ff9999', '#66b3ff']

    # fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=colors,
    # hoverinfo='label+percent', textinfo='value')])
    # st.plotly_chart(fig)

    df = pd.DataFrame([
        {'index': 0,
         'value': used / (1024**3),
         'text': used_text,
         'type': 'used'},
        {'index': 0,
         'value': free / (1024**3),
         'text': free_text,
         'type': 'free'},
        {'index': 1,
         'value': total / (1024**3),
         'text': total_text,
         'type': 'total'},
    ])
    # print(df)
    fig = px.bar(
        df,
        orientation="h",
        x='value',
        y='index',
        text='text',
        color='type',
        color_discrete_map={
            'used': '#ff9999',
            'free': '#66b3ff',
            'total': '#000000'
        },
        title="disk usage")
    # fig.update_traces(width=0.3)
    fig.update_layout(
        height=320,
        # bargap=0.01,
        # bargroupgap=0.0,
        xaxis=dict(
            title='usage[GB]',
        ),
        yaxis=dict(
            title='',
            showticklabels=False,
        ),
    )
    # fig.data[0].marker.line.width = 4
    # fig.data[0].marker.line.color = "black"
    st.plotly_chart(fig)
