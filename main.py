import logging
import time
from os import getenv

from obswebsocket.exceptions import ConnectionFailure
from prometheus_client import Gauge, start_http_server

frames_dropped_count = Gauge('dropped_frames', 'Total frames dropped')
bitrate = Gauge('bitrate', 'Bitrate in kbits')
frames_dropped_percent = Gauge('frames_dropped_percent', 'Percent of frames dropped')
cpu_usage_percent = Gauge('cpu_usage_percent', 'CPU usage percent')


logging.basicConfig(level=logging.INFO)

from obswebsocket import obsws, events

host = getenv("OBS_URL", "localhost")
port = getenv("OBS_PORT", 4444)
password = getenv("OBS_PASSWORD", "")


def reset_data(*_):
    frames_dropped_count.set(0)
    bitrate.set(0)
    frames_dropped_percent.set(0)
    cpu_usage_percent.set(0)


def on_stream_status(message: events.StreamStatus):
    if message.getStreaming():
        frames_dropped_count.set(message.getNumDroppedFrames())
        bitrate.set(message.getKbitsPerSec())
        frames_dropped_percent.set(message.getStrain())
        cpu_usage_percent.set(message.getCpuUsage())
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
