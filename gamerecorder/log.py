import colorlog

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