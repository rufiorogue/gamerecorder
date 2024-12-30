import subprocess
import colorlog
import psutil
import os.path
import re
import datetime
import time
import glob
from pydantic import BaseModel, ValidationError
import tomllib
from xdg_base_dirs import xdg_config_home

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


def build_process_list() -> list[dict]:
    processes = []
    for x in psutil.process_iter():
        try:
            processes.append({
                'pid': x.pid,
                'name': x.name(),
                'cmd': x.cmdline()
            })
        except psutil.NoSuchProcess: ...
    return processes


def gsr_exec(output_file: str) -> subprocess.Popen:
    args = [
        'gpu-screen-recorder',
        '-w', conf.mon,
        '-f', str(conf.fps),
        '-k', 'hevc_10bit',
        '-a', 'default_output',
        '-o', output_file,
        ]
    log_main.debug('gsr_exec with params: %s', ' '.join(args))
    return subprocess.Popen(args=args)


def cycle():
    process_list = build_process_list()

    log_main.info('detecting game...')

    def find_game_title() -> tuple[str, int]:
        for process in process_list:
            if process['name'] == 'steam-runtime-launch-client':
                for idx,cmd_arg in enumerate(process['cmd']):
                    if cmd_arg =='--directory':
                        next_cmd_arg =  process['cmd'][idx+1]
                        if 'steamapps/common' in next_cmd_arg:
                            if m := re.search(r'steamapps/common/(.+)', next_cmd_arg):
                                return m.group(1), process['pid']
        return None,None

    game_title,game_pid = find_game_title()
    if game_title and game_pid:
        log_main.info('game title: "%s"  PID %d', game_title, game_pid)

        def strip_extra_characters(s: str) -> str:
            return s.replace('\'', '').replace(' ', '')

        game_title = strip_extra_characters(game_title)

        log_main.info('video file prefix: "%s"', game_title)
    else:
        log_main.info('game was not detected')
        return

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


    proc = gsr_exec(save_file)
    log_main.info('GSR started, PID %d', proc.pid)
    log_main.info('watching for game process to exit')
    psutil.wait_procs([psutil.Process(game_pid)])
    log_main.info('game process exited, shutting down the recorder')
    proc.terminate()
    recorder_exitcode = proc.wait()
    log_main.info('recorder terminated (code %d)', recorder_exitcode)

def main():
    while True:
        cycle()
        time.sleep(1)
