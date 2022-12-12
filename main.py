import logging

from obsws_python.error import OBSSDKError

logging.basicConfig(level=logging.INFO)
import time
from os import getenv

import obsws_python as obs
from prometheus_client import Gauge, start_http_server

bitrate = Gauge('bitrate', 'Bitrate in kbits')
fps = Gauge('fps', 'Current framerate')

frames_dropped_percent = Gauge('frames_dropped_percent', 'Percent of frames dropped')
total_stream_time = Gauge('total_stream_time', 'Total time (in seconds) since the stream started')

num_total_frames = Gauge('num_total_frames', 'Total number of frames transmitted since the stream started')
frames_dropped_count = Gauge('dropped_frames', 'Total frames dropped')

render_total_frames = Gauge('render_total_frames', 'Number of frames rendered')
render_missed_frames = Gauge('render_missed_frames', 'Number of frames missed due to rendering lag')

output_total_frames = Gauge('output_total_frames', 'Number of frames outputted')
output_skipped_frames = Gauge('output_skipped_frames', 'Number of frames skipped due to encoding lag')

average_frame_time = Gauge('average_frame_time', 'Average frame time in milliseconds')
cpu_usage_percent = Gauge('cpu_usage_percent', 'CPU usage percent')
memory_usage = Gauge('memory_usage', 'Current RAM usage in megabytes')
free_disk_space = Gauge('free_disk_space', 'Free recording disk space in megabytes')

host = getenv("OBS_URL", "localhost")
port = getenv("OBS_PORT", 4444)
password = getenv("OBS_PASSWORD", "")


def reset_data(*_):
    bitrate.set(0)
    frames_dropped_percent.set(0)
    total_stream_time.set(0)
    num_total_frames.set(0)
    frames_dropped_count.set(0)
    fps.set(0)
    render_total_frames.set(0)
    render_missed_frames.set(0)
    output_total_frames.set(0)
    output_skipped_frames.set(0)
    average_frame_time.set(0)
    cpu_usage_percent.set(0)
    memory_usage.set(0)
    free_disk_space.set(0)


def on_stream_state_changed(data):
    if not data.output_active:
        reset_data()


def on_exit_started(_):
    reset_data()


def update_data():
    stats = cl.get_stats()

    cpu_usage_percent.set(stats.cpu_usage)
    memory_usage.set(stats.memory_usage)
    free_disk_space.set(stats.available_disk_space)
    fps.set(stats.active_fps)
    average_frame_time.set(stats.average_frame_render_time)
    render_missed_frames.set(stats.render_skipped_frames)
    render_total_frames.set(stats.render_total_frames)
    output_skipped_frames.set(stats.output_skipped_frames)
    output_total_frames.set(stats.output_total_frames)

    outputs = cl.get_output_list()
    output = outputs.outputs[0].get("outputName")

    status = cl.get_output_status(output)
    frames_dropped_count.set(status.output_skipped_frames)
    num_total_frames.set(status.output_total_frames)
    total_stream_time.set(status.output_duration / 1000)
    frames_dropped_percent.set(status.output_skipped_frames / status.output_total_frames * 100 if status.output_total_frames > 0 and status.output_skipped_frames > 0 else 0)

    # bitrate not currently support by obs-ws v5 (yayyyyy)
    # bitrate.set(message.getKbitsPerSec())


start_http_server(8000)

while True:
    try:
        cl = obs.ReqClient(host=host, port=port, password=password)
        event_client = obs.EventClient(host=host, port=port, password=password)
        event_client.callback.register(on_stream_state_changed)
        event_client.callback.register(on_exit_started)
        logging.info(f"Connected to OBS at {host}:{port} with password {password or 'NO PASSWORD'}")
    except OBSSDKError:
        logging.warning(f"Could not connect to OBS at {host}:{port} with password {password or 'NO PASSWORD'}")
        time.sleep(1)
        continue

    while cl.base_client.ws.connected and event_client.base_client.ws.connected:
        update_data()
        time.sleep(1)

    logging.warning(f"Disconnected from OBS at {host}:{port} with password {password or 'NO PASSWORD'}")
    reset_data()
