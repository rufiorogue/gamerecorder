from typing import NamedTuple
import subprocess
import psutil
import time
import re
import json
from gamerecorder.log import log_main


class ProcessInfo(NamedTuple):
    pid: int
    name: str
    args: list[str]

def get_all_processes() -> list[ProcessInfo]:
    processes = []
    for x in psutil.process_iter():
        try:
            processes.append(ProcessInfo(pid=x.pid, name=x.name(), args=x.cmdline()))
        except psutil.NoSuchProcess: ...
    return processes

class GameInfo(NamedTuple):
    pid: int
    title: str
    pipewire_name: str


# TODO
# This will only work if Steam client is running in a flatpak
def _get_pipewire_clients() -> list[dict]:
    objects = json.loads(subprocess.check_output('pw-dump'))
    def is_steam_game_client_obj(obj) -> bool:
        app_id = obj['info']['props']['pipewire.access.portal.app_id'] if ('info' in obj and 'props' in obj['info'] and 'pipewire.access.portal.app_id' in obj['info']['props']) else None
        app_name = obj['info']['props']['application.name'] if ('info' in obj and 'props' in obj['info'] and 'application.name' in obj['info']['props']) else None

        accepted_app_names = [
            'UDKGame-Linux',
        ]
        ignore_app_names = [
            'Steam',
            'Steam Voice Settings',
            'Chromium',
            'Chromium input',
            'upc.exe',
        ]
        return (
            obj['type'] == 'PipeWire:Interface:Client'
            and app_id == 'com.valvesoftware.Steam'
            and (
                    app_name in accepted_app_names
                or  app_name not in ignore_app_names
                )
        )
    return list(filter(is_steam_game_client_obj, objects))

def detect_steam_game() -> GameInfo:
    processes = get_all_processes()
    for process in processes:
        if process.name == 'steam-runtime-launch-client':
            for idx,cmd_arg in enumerate(process.args):
                if cmd_arg =='--directory':
                    next_cmd_arg =  process.args[idx+1]
                    if 'steamapps/common' in next_cmd_arg:
                        if m := re.search(r'steamapps/common/(.+)', next_cmd_arg):
                            game_title = m.group(1).replace('Linux','').replace('Binaries','').replace('/','').strip()
                            log_main.debug('game_title: %s', game_title)

                            if game_title:
                                log_main.debug('sentinel process ID: %s', process.pid)

                                log_main.info('waiting for pipewire client to appear')
                                pipewire_application_name = None
                                while True:
                                    matching_pipewire_clients = _get_pipewire_clients()
                                    if len(matching_pipewire_clients) > 0:
                                        pipewire_application_name = matching_pipewire_clients[0]['info']['props']['application.name']
                                        log_main.debug('pipewire client app name: %s', pipewire_application_name)
                                        break
                                    else:
                                        log_main.info('  waiting...')
                                        time.sleep(0.5)
                                        if not psutil.pid_exists(process.pid):
                                            log_main.warning('sentinel process exited early')
                                            return None

                                return GameInfo(
                                    title=game_title,
                                    pipewire_name=pipewire_application_name,
                                    pid=process.pid
                                    )