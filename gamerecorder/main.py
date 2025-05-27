import subprocess
import colorlog
import psutil
import signal
import os.path
import re
import datetime
import time
import glob
import json
from pydantic import BaseModel, ValidationError
import tomllib
from xdg_base_dirs import xdg_config_home
from typing import Optional, NamedTuple

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s  %(levelname)s  %(name)s  %(message)s',
        log_colors={
            'DEBUG':    'thin_white',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
	    }))

log_main = colorlog.getLogger('main')
log_main.addHandler(handler)
log_main.setLevel(colorlog.DEBUG)

log_gsr = colorlog.getLogger('GSR')
log_gsr.addHandler(handler)
log_gsr.setLevel(colorlog.DEBUG)

class Config(BaseModel):
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


class ProcessInfo(NamedTuple):
    pid: int
    name: str
    args: list[str]

class GameInfo(NamedTuple):
    pid: int
    title: str
    pipewire_name: str

def get_all_processes() -> list[ProcessInfo]:
    processes = []
    for x in psutil.process_iter():
        try:
            processes.append(ProcessInfo(pid=x.pid, name=x.name(), args=x.cmdline()))
        except psutil.NoSuchProcess: ...
    return processes

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

    def find_steam_game() -> GameInfo:
        processes = get_all_processes()
        for process in processes:
            if process.name == 'steam-runtime-launch-client':
                for idx,cmd_arg in enumerate(process.args):
                    if cmd_arg =='--directory':
                        next_cmd_arg =  process.args[idx+1]
                        if 'steamapps/common' in next_cmd_arg:
                            if m := re.search(r'steamapps/common/(.+)', next_cmd_arg):
                                game_title = m.group(1)
                                log_main.debug('game_title: %s', game_title)

                                if game_title:
                                    log_main.debug('sentinel process ID: %s', process.pid)

                                    # TODO
                                    # This will only work if Steam client is running in a flatpak
                                    def get_pipewire_clients() -> list[dict]:
                                        objects = json.loads(subprocess.check_output('pw-dump'))
                                        def is_steam_game_client_obj(obj) -> bool:
                                            return (
                                                    obj['type'] == 'PipeWire:Interface:Client'
                                                and 'pipewire.access.portal.app_id' in obj['info']['props']
                                                and obj['info']['props']['pipewire.access.portal.app_id'] == 'com.valvesoftware.Steam'
                                                and 'application.name' in obj['info']['props']
                                                and obj['info']['props']['application.name'] != 'Steam'
                                                and obj['info']['props']['application.name'] != 'Steam Voice Settings'
                                            )
                                        return list(filter(is_steam_game_client_obj, objects))
                                    log_main.debug('waiting for pipewire client to appear')
                                    pipewire_application_name = None
                                    while True:
                                        matching_pipewire_clients = get_pipewire_clients()
                                        if len(matching_pipewire_clients) > 0:
                                            pipewire_application_name = matching_pipewire_clients[0]['info']['props']['application.name']
                                            log_main.debug('pipewire client app name: %s', pipewire_application_name)
                                            break
                                        else:
                                            log_main.debug('still waiting')
                                            time.sleep(0.5)

                                    return GameInfo(
                                        title=game_title,
                                        pipewire_name=pipewire_application_name,
                                        pid=process.pid
                                        )

    detected_game = find_steam_game()
    if detected_game is None:
        log_main.info('game was not detected')
        return
    log_main.info('found game: %s ', detected_game)

    def strip_extra_characters(s: str) -> str:
        return s.replace('\'', '').replace(' ', '')

    game_title = strip_extra_characters(detected_game.title)

    log_main.info('video file prefix: "%s"', game_title)


    # generate output file name
    save_directory = f"{os.environ['HOME']}/Videos"
    existing_chapter_files = sorted(glob.glob(f'{save_directory}/{game_title}_*'))
    if len(existing_chapter_files):
        last_chapter_file = existing_chapter_files[-1]
        if m := re.match(f'^{save_directory}/{game_title}_([0-9]+)', last_chapter_file):
            last_chapter_nr = int(m.group(1))
            new_chapter_nr = last_chapter_nr + 1
    else:
        new_chapter_nr = 1
    save_file = f"{save_directory}/{game_title}_{new_chapter_nr:02d}_{datetime.datetime.now().strftime('%Y%m%d')}.mkv"
    assert not os.path.exists(save_file) # defensive postcondition check: since the name is unique, the file can't exist
    log_main.info('new chapter number: %d', new_chapter_nr)
    log_main.info('new chapter output file: %s', save_file)

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
