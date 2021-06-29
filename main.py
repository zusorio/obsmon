import logging
import time
from os import getenv

from obswebsocket.exceptions import ConnectionFailure
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


logging.basicConfig(level=logging.INFO)

from obswebsocket import obsws, events

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


def on_stream_status(message: events.StreamStatus):
    if message.getStreaming():
        bitrate.set(message.getKbitsPerSec())
        frames_dropped_percent.set(message.getStrain())
        total_stream_time.set(message.getTotalStreamTime())
        num_total_frames.set(message.getNumTotalFrames())
        frames_dropped_count.set(message.getNumDroppedFrames())
        fps.set(message.getFps())
        render_total_frames.set(message.getRenderTotalFrames())
        render_missed_frames.set(message.getRenderMissedFrames())
        output_total_frames.set(message.getOutputTotalFrames())
        output_skipped_frames.set(message.getOutputSkippedFrames())
        average_frame_time.set(message.getAverageFrameTime())
        cpu_usage_percent.set(message.getCpuUsage())
        memory_usage.set(message.getMemoryUsage())
        free_disk_space.set(message.getFreeDiskSpace())
    else:
        reset_data()


def stream(ws: obsws):
    ws.connect()
    time.sleep(60*60*24*7)


start_http_server(8000)

ws = obsws(host, port, password)
ws.register(on_stream_status, events.StreamStatus)
ws.register(reset_data, events.StreamStopping)
ws.register(reset_data, events.Exiting)

while True:
    try:
        ws.connect()
        logging.info(f"Connected to OBS at {host}:{port} with password {password or 'NO PASSWORD'}")
    except ConnectionFailure:
        logging.warning(f"Could not connect to OBS at {host}:{port} with password {password or 'NO PASSWORD'}")
        time.sleep(1)
        continue

    while ws.ws.connected:
        time.sleep(1)

    logging.warning(f"Disconnected from OBS at {host}:{port} with password {password or 'NO PASSWORD'}")
    ws.disconnect()
    reset_data()
