# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import gc

def connect_sta():
    import network
    import config
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.config(dhcp_hostname='stairs')
    print('Connecting to network...')
    sta_if.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    while not sta_if.isconnected():
        pass
    print('Network config:', sta_if.ifconfig())

connect_sta()

import webrepl
webrepl.start()
gc.collect()
