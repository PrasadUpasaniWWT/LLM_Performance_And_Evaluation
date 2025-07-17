import subprocess
import streamlit as st
import time
import os
import pandas as pd
from datetime import datetime
import numpy as np
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="LLM Performance and Evaluation", page_icon="assets/WWT_Monogram_1.png", layout="wide")

# --- Colors ---
RED = "#EE282A"
LIGHT_BLUE = "#0086EA"
DARK_BLUE = "#1C0087"
NAVY = "#1D1E4B"

# --- Initialize Page State ---
if "page" not in st.session_state:
    st.session_state.page = "Home"

# --- Sidebar with Logo and Navigation ---
st.sidebar.image("assets/WWT_Logo_RGB_Color.png", width=200)
selection = st.sidebar.radio("Navigation", ["Home", "Dashboard"], index=["Home", "Dashboard"].index(st.session_state.page))
if selection != st.session_state.page:
    st.session_state.page = selection
    st.rerun()

# --- Time Parsing Function ---
def parse_run_time(rt_str):
    rt_str = rt_str.lower().strip()
    minutes, seconds = 0, 0
    if "m" in rt_str and "s" in rt_str:
        parts = rt_str.replace("m", " ").replace("s", "").split()
        minutes = int(parts[0])
        seconds = int(parts[1])
    elif "m" in rt_str:
        minutes = int(rt_str.replace("m", ""))
    elif "s" in rt_str:
        seconds = int(rt_str.replace("s", ""))
    return minutes * 60 + seconds

# --- Page: Home ---
if st.session_state.page == "Home":
    # Centered layout
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.title(":blue[LLM Load Test]")

        # --- Input Form ---
        with st.form("load_test_form"):
            users = st.number_input("Number of Users", min_value=1, value=10)
            spawn_rate = st.number_input("Spawn Rate (users/sec)", min_value=1, value=2)
            run_time = st.text_input("Run Time (e.g., 1m, 30s, 2m30s)", value="1m")
            target_url = st.text_input("Target URL", value="https://your-model-endpoint.com")

            submitted = st.form_submit_button("Start Load Test")

        # --- Launch Test & Show Progress ---
        if submitted:
            st.markdown(f"<h4 style='color:{DARK_BLUE};'>Running Load Test...</h4>", unsafe_allow_html=True)

            # Parse duration
            duration = parse_run_time(run_time)

            # --- Start Locust first ---
            command = [
                "locust",
                "-f", "locust_load_test.py",
                "--host", target_url,
                "--users", str(users),
                "--spawn-rate", str(spawn_rate),
                "--headless",
                "--run-time", run_time,
            ]
            subprocess.Popen(command)

            # --- Show progress bar while test runs ---
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i in range(duration):
                time.sleep(1)
                percent = int((i + 1) / duration * 100)
                progress_bar.progress(percent)
                status_text.markdown(f"<p style='color:{NAVY};'>Progress: {percent}%</p>", unsafe_allow_html=True)

            st.success("Load test completed. Redirecting to Dashboard...")
            time.sleep(1.5)
            st.session_state.page = "Dashboard"
            st.rerun()



# --- Page: Dashboard ---
elif st.session_state.page == "Dashboard":

    BLUE = "#0086EA"
    RED = "#EE282A"
    VIOLET = "#330072"
    NAVY = "#1D1E4B"

    DATA_DIR = "data"
    today_str = datetime.today().strftime("%Y-%m-%d")

    metric_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith("_metrics.csv") and f.startswith(today_str)],
        reverse=True
    )

    if not metric_files:
        st.warning("No metrics files found for today in the data folder.")
    else:
        selected_file = st.selectbox("Select a Test File:", metric_files)
        file_path = os.path.join(DATA_DIR, selected_file)

        try:
            df = pd.read_csv(file_path)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            start_time = df["timestamp"].min()
            end_time = df["timestamp"].max()
            duration_sec = max((end_time - start_time).total_seconds(), 1)

            # --- Metrics ---
            metrics = [
                ("Total Requests", len(df)),
                ("Failures", len(df[df["status"] != "success"])),
                ("RPS", round(len(df) / duration_sec, 2)),
                ("Avg Latency", f"{round(df['total_latency'].mean(), 2)} s"),
                ("P50 Latency", f"{round(np.percentile(df['total_latency'], 50), 2)} s"),
                ("P95 Latency", f"{round(np.percentile(df['total_latency'], 95), 2)} s"),
                ("Min Latency", f"{round(df['total_latency'].min(), 2)} s"),
                ("Max Latency", f"{round(df['total_latency'].max(), 2)} s"),
            ]

            # --- Optimized CSS ---
            st.markdown("""
            <style>
            .metric-card {
                position: relative;
                padding: 20px;
                margin-bottom: 20px;
                background-color: white;
                border-radius: 15px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                font-family: sans-serif;
                z-index: 1;
                overflow: hidden;
            }

            .metric-card::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                border-radius:15px;
                padding: 3px;
                background: linear-gradient(to right, #EE282A, #330072, #0086EA);
                -webkit-mask: 
                    linear-gradient(#fff 0 0) content-box, 
                    linear-gradient(#fff 0 0);
                -webkit-mask-composite: destination-out;
                mask-composite: exclude;
                z-index: -1;
            }

            .metric-label {
                font-size: 16px;
                font-weight: 600;
                color: #1D1E4B;
                margin-bottom: 5px;
            }

            .metric-value {
                font-size: 26px;
                font-weight: bold;
                color: #000;
            }
            </style>
            """, unsafe_allow_html=True)

            # --- First Row: Metrics 0–3 ---
            top_cols = st.columns(4)
            for i in range(4):
                with top_cols[i]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{metrics[i][0]}</div>
                        <div class="metric-value">{metrics[i][1]}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # --- Second Row: Metrics 4–7 ---
            bottom_cols = st.columns(4)
            for i in range(4, 8):
                with bottom_cols[i - 4]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{metrics[i][0]}</div>
                        <div class="metric-value">{metrics[i][1]}</div>
                    </div>
                    """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Failed to load or process file: {e}")

        # --- Bar Chart ---
        st.markdown("---")  # Horizontal divider

        try:
            comparison_data = []

            for file in metric_files:
                compare_df = pd.read_csv(os.path.join(DATA_DIR, file))
                compare_df["timestamp"] = pd.to_datetime(compare_df["timestamp"])
                duration_sec = max((compare_df["timestamp"].max() - compare_df["timestamp"].min()).total_seconds(), 1)
                test_rps = round(len(compare_df) / duration_sec, 2)

                test_id = file.replace("_metrics.csv", "")
                comparison_data.append({
                    "Test": test_id,
                    "Max TTFT": compare_df["ttft"].max(),
                    "Max TPOT": compare_df["tpot"].max(),
                    "Max Total Latency": compare_df["total_latency"].max(),
                    "Max RPS": test_rps,
                    "Max TPS": compare_df["tps"].max()
                })

            comp_df = pd.DataFrame(comparison_data)

            # --- Add hover-specific columns ---
            melted_latency = comp_df.melt(id_vars="Test", value_vars=["Max TTFT", "Max TPOT", "Max Total Latency"],
                                          var_name="Metric", value_name="Value")
            melted_latency["Hover"] = melted_latency.apply(
                lambda row: f"{row['Metric']}: {row['Value']:.2f} s<br>Test: {row['Test']}", axis=1)

            melted_throughput = comp_df.melt(id_vars="Test", value_vars=["Max RPS", "Max TPS"],
                                             var_name="Metric", value_name="Value")
            melted_throughput["Hover"] = melted_throughput.apply(
                lambda row: f"{row['Metric']}: {row['Value']:.2f} req/sec" if "RPS" in row["Metric"]
                else f"{row['Metric']}: {row['Value']:.2f} tokens/sec<br>Test: {row['Test']}", axis=1)

            # --- Layout container ---
            with st.container():
                col1, spacer, col2 = st.columns([5, 0.5, 5])  # spacer for vertical divider

                # --- Latency Chart ---
                with col1:
                    fig_lat = px.bar(
                        melted_latency,
                        x="Test",
                        y="Value",
                        color="Metric",
                        barmode="group",
                        custom_data=["Hover"],
                        title="Latency Metrics Across Tests",
                        labels={"Value": "Latency (s)", "Metric": "Metric"},
                        color_discrete_sequence=["#FB550E", "#E31C79", "#1C0087"]
                    )
                    fig_lat.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
                    st.plotly_chart(fig_lat, use_container_width=True)

                # --- Vertical Divider (fake) ---
                with spacer:
                    st.markdown("<div style='border-left: 1px solid #DDD; height: 100%;'></div>", unsafe_allow_html=True)

                # --- Throughput Chart ---
                with col2:
                    fig_tp = px.bar(
                        melted_throughput,
                        x="Test",
                        y="Value",
                        color="Metric",
                        barmode="group",
                        custom_data=["Hover"],
                        title="Throughput Metrics Across Tests",
                        labels={"Value": "Rate", "Metric": "Metric"},
                        color_discrete_sequence=["#8202C4", "#0086EA"]
                    )
                    fig_tp.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
                    st.plotly_chart(fig_tp, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading comparison data: {e}")

        # --- Interactive Graphs for Selected File ---
        try:
            st.markdown("---")
            st.subheader("Interactive Graphs for Selected Test")

            available_metrics = ["ttft", "tpot", "total_latency", "tps"]

            unit_map = {
                "ttft": "s",
                "tpot": "s",
                "total_latency": "s",
                "tps": "tokens/sec"
            }

            plot_col1, plot_col2 = st.columns(2)

            with plot_col1:
                y_metric_1 = st.selectbox("Y-Axis (vs Concurrent Requests):", available_metrics, key="select_concurrent")
                fig_concurrent = px.scatter(
                    df,
                    x="concurrent_requests",
                    y=y_metric_1,
                    title=f"{y_metric_1} vs Concurrent Requests",
                    labels={
                        "concurrent_requests": "Concurrent Requests",
                        y_metric_1: f"{y_metric_1} ({unit_map.get(y_metric_1, '')})"
                    },
                    color_discrete_sequence=[RED]
                )
                fig_concurrent.update_traces(mode="markers+lines")
                st.plotly_chart(fig_concurrent, use_container_width=True)

            with plot_col2:
                y_metric_2 = st.selectbox("Y-Axis (vs Timestamp):", available_metrics, key="select_time")
                fig_time = px.line(
                    df,
                    x="timestamp",
                    y=y_metric_2,
                    title=f"{y_metric_2} over Time",
                    labels={
                        "timestamp": "Timestamp",
                        y_metric_2: f"{y_metric_2} ({unit_map.get(y_metric_2, '')})"
                    },
                    color_discrete_sequence=[VIOLET]
                )
                st.plotly_chart(fig_time, use_container_width=True)

        except Exception as e:
            st.error(f"Error generating interactive graphs: {e}")







        

    

