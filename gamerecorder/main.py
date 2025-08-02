import subprocess
import psutil
import signal
import os.path
from pathlib import Path
import datetime
import time
from pydantic import BaseModel, ValidationError
import tomllib
from xdg_base_dirs import xdg_config_home

from gamerecorder.log import log_main
from gamerecorder.detect import detect_steam_game


class Config(BaseModel):
    """ directory to store video files """
    out_dir: str = Path.home() / 'Videos'

    """  monitor output. Anything that can be "-w" parameter of gsr.  Example: DP-2  """
    mon: str

    """ video frame rate. Example: 144  """
    fps: int


conf_path = os.path.join(xdg_config_home(), 'gamerecorder', 'config.toml')
if os.path.exists(conf_path):
    log_main.info('reading config file %s', conf_path)
    with open(conf_path, 'rb') as f:
        config_data = tomllib.load(f)
    try:
        conf = Config(**config_data)
        log_main.debug('config: %s', conf)
    except ValidationError as e:
        log_main.error('invalid configuration: %s', e)
        quit(1)
else:
    log_main.error('config not found, create config file %s', conf_path)
    quit(1)



def gsr_exec(output_file: str,
             pipewire_name: str,
             ) -> subprocess.Popen:
    args = [
        'gpu-screen-recorder',
        '-w', conf.mon,
        '-f', str(conf.fps),
        '-k', 'hevc_10bit',
        '-a', 'app:'+ pipewire_name,
        '-o', output_file,
        ]
    log_main.info('gsr_exec with params: %s', ' '.join(args))
    return subprocess.Popen(args=args)


def cycle():
    log_main.info('detecting game...')


    detected_game = detect_steam_game()
    if detected_game is None:
        log_main.info('game was not detected')
        return
    log_main.info('found game: %s ', detected_game)

    def strip_extra_characters(s: str) -> str:
        return s.replace('\'', '').replace(' ', '')

    game_title = strip_extra_characters(detected_game.title)

    log_main.info('video file prefix: "%s"', game_title)


    # generate output file name
    save_file_base = str(Path(conf.out_dir) / f"{game_title}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    save_file_ext = '.mkv'
    save_file = save_file_base + save_file_ext
    if os.path.exists(save_file): # this is very unlikely to happen but let's handle
        save_file = save_file_base + '_1' + save_file_ext
        assert os.path.exists(save_file) # confused, bail out!
    log_main.info('output file: %s', save_file)

    proc = gsr_exec(
        output_file=save_file,
        pipewire_name=detected_game.pipewire_name
        )
    log_main.info('GSR started, PID %d', proc.pid)
    log_main.info('watching for game process to exit')
    psutil.wait_procs([psutil.Process(detected_game.pid)])
    log_main.info('game process exited, shutting down the recorder')
    proc.send_signal(signal.SIGINT)
    recorder_exitcode = proc.wait()
    log_main.info('recorder terminated (code %d)', recorder_exitcode)

def main():
    while True:
        cycle()
        time.sleep(1)
