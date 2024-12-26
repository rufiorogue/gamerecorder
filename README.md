# gamerecorder

A smart auto-recording solution for Steam games using gpu-screen-recorder as backend.

## Installation
```
poetry install
```

## Usage

First create a config file in `~/.config/gamerecorder/config.toml`
```
fps=60
mon=DP-1
```

Then:

```
poetry run gamerecorder
```

Leave the program running in the background, then open Steam game. It will detect the game and start GSR automatically.

## Typical session

```
2024-12-26 03:43:46,604  INFO  main  game was not detected
2024-12-26 03:43:47,661  INFO  main  detecting game...
2024-12-26 03:43:47,661  INFO  main  game was not detected
2024-12-26 03:43:48,723  INFO  main  detecting game...
2024-12-26 03:43:48,723  INFO  main  game title: "SIGNALIS"  PID 432099
2024-12-26 03:43:48,723  INFO  main  video file prefix: "SIGNALIS"
2024-12-26 03:43:48,723  INFO  main  chapter number: 1
2024-12-26 03:43:48,723  INFO  main  chapter output file: /home/user/Videos/SIGNALIS_01_20241226.mkv
2024-12-26 03:43:48,723  DEBUG  main  gsr_exec with params: gpu-screen-recorder -w DP-2 -f 60 -k hevc_10bit -a default_output -o /home/user/Videos/SIGNALIS_01_20241226.mkv
2024-12-26 03:43:48,724  INFO  main  GSR started, PID 432212
2024-12-26 03:43:48,724  INFO  main  watching for game process to exit
gsr info: gsr_kms_client_init: setting up connection to /usr/bin/gsr-kms-server
gsr info: gsr_kms_client_init: waiting for server to connect
kms server info: connecting to the client
gsr info: gsr_kms_client_init: server connected
gsr info: replacing file-backed unix domain socket with socketpair
kms server info: connected to the client
gsr info: using socketpair
[hevc_nvenc @ 0x5af2e7dd1500] ignoring invalid SAR: 0/0
update fps: 60, damage fps: 60
update fps: 60, damage fps: 60
update fps: 61, damage fps: 61
...
...
update fps: 61, damage fps: 61
update fps: 60, damage fps: 60
update fps: 61, damage fps: 61
2024-12-26 03:45:13,599  INFO  main  game process exited, shutting down the recorder
2024-12-26 03:45:13,984  INFO  main  recorder terminated (code -15)
2024-12-26 03:45:15,046  INFO  main  detecting game...
2024-12-26 03:45:15,046  INFO  main  game was not detected
2024-12-26 03:45:16,106  INFO  main  detecting game...
2024-12-26 03:45:16,106  INFO  main  game was not detected
