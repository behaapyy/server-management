import streamlit as st
import subprocess
import pandas as pd
from collections import defaultdict
import altair as alt
from datetime import datetime

st.set_page_config(page_title="GPU Monitor", layout="wide")
st.title(":rocket: GPU Usage Dashboard: Server 96")


def get_gpu_process_info():
    try:
        proc_output = subprocess.check_output([
            'nvidia-smi',
            '--query-compute-apps=gpu_uuid,pid',
            '--format=csv,noheader,nounits'
        ]).decode().strip().split('\n')
    except subprocess.CalledProcessError:
        return defaultdict(list)

    gpu_proc_info = defaultdict(list)

    # UUID :left_right_arrow: index 매핑
    uuid_map_output = subprocess.check_output([
        'nvidia-smi',
        '--query-gpu=index,uuid',
        '--format=csv,noheader,nounits'
    ]).decode().strip().split('\n')
    uuid_to_index = {uuid: int(idx) for idx, uuid in (line.split(', ') for line in uuid_map_output)}

    for line in proc_output:
        if not line.strip():
            continue
        uuid, pid = line.split(', ')
        try:
            user = subprocess.check_output(['ps', '-o', 'user=', '-p', pid]).decode().strip()
            start_str = subprocess.check_output(['ps', '-o', 'lstart=', '-p', pid]).decode().strip()
            start_dt = datetime.strptime(start_str, "%a %b %d %H:%M:%S %Y")
            start_formatted = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            gpu_idx = uuid_to_index.get(uuid)
            if gpu_idx is not None:
                gpu_proc_info[gpu_idx].append(f"{user} ({start_formatted})")
        except Exception:
            continue

    return {idx: '\n'.join(sorted(infos)) for idx, infos in gpu_proc_info.items()}


# NVIDIA SMI로 GPU 정보 가져오기
def get_gpu_info():
    user_info_map = get_gpu_process_info()

    result = subprocess.check_output([
        'nvidia-smi',
        '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu',
        '--format=csv,noheader,nounits'
    ]).decode('utf-8').strip().split('\n')

    data = []
    for line in result:
        idx, name, util, mem_used, mem_total, temp = line.split(', ')
        idx = int(idx)
        data.append({
            'GPU': f"{idx} - {name}",
            'Utilization (%)': int(util),
            'Memory Used (MB)': int(mem_used),
            'Memory Total (MB)': int(mem_total),
            'Temperature (°C)': int(temp),
            'User (Start Time)': user_info_map.get(idx, '—')  # 유저 + 시작 시간
        })

    return pd.DataFrame(data)


df = get_gpu_info()
st.dataframe(df, use_container_width=True)

# 시각화
# st.subheader(":bar_chart: GPU Utilization")
# st.bar_chart(df.set_index("GPU")["Utilization (%)"])

# st.subheader(":floppy_disk: Memory Usage")
# st.bar_chart(df.set_index("GPU")[["Memory Used (MB)", "Memory Total (MB)"]])

st.subheader(":bar_chart: GPU Utilization")
util_chart = alt.Chart(df).mark_bar(
    color='red',
    size=40  # 막대 너비 조절 (기본값보다 작게)
).encode(
    x=alt.X('GPU:N', sort=None),
    y=alt.Y('Utilization (%):Q')
).properties(
    width=500,   # 전체 차트 폭 줄이기
    height=300
)
st.altair_chart(util_chart, use_container_width=True)


# Bar chart
st.subheader(":floppy_disk: Memory Usage")
mem_df = df.melt(id_vars='GPU', value_vars=["Memory Used (MB)", "Memory Total (MB)"],
                 var_name="Type", value_name="Memory (MB)")

mem_chart = alt.Chart(mem_df).mark_bar(size=40).encode(
    x=alt.X('GPU:N', title="GPU"),
    y=alt.Y('Memory (MB):Q'),
    color=alt.Color('Type:N', scale=alt.Scale(
        domain=["Memory Used (MB)", "Memory Total (MB)"],
        range=["#1F77B4", "#DDDDDD"]  # 파랑 / 회색
    )),

).properties(
    width=500,
    height=300
).configure_axis(
    labelAngle=0
)

st.altair_chart(mem_chart, use_container_width=True)