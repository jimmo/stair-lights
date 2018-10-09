# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import gc

def connect_sta():
    import network
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Connecting to network...')
        sta_if.active(True)
        sta_if.connect('Rainbows', '0417913600')
        while not sta_if.isconnected():
            pass
    print('Network config:', sta_if.ifconfig())

connect_sta()

import webrepl
webrepl.start()
gc.collect()
