import pyb
import utime

_BRIGHTNESS = const(0b11100100)

_STRIP = pyb.SPI('X', pyb.SPI.MASTER, baudrate=1000000, crc=None, bits=8, firstbit=pyb.SPI.MSB, phase=1)

_BUTTON = pyb.Switch()

_NUM_LEDS = 170

pixeldata = bytearray([0x00] * 4 + [0x00] * 4 * _NUM_LEDS + [0xff] * 4)
view = memoryview(pixeldata)[4:-4]

@micropython.native
def rainbow(h, xbgr):
  # h is hue between 0-239.
  if h < 40:
    xbgr[3] = 255
    xbgr[2] = (h * 255) // 40
    xbgr[1] = 0
  elif h < 80:
    xbgr[3] = ((80-h) * 255) // 40
    xbgr[2] = 255
    xbgr[1] = 0
  elif h < 120:
    xbgr[3] = 0
    xbgr[2] = 255
    xbgr[1] = ((h-80) * 255) // 40
  elif h < 160:
    xbgr[3] = 0
    xbgr[2] = ((160-h) * 255) // 40
    xbgr[1] = 255
  elif h < 200:
    xbgr[3] = ((h-160) * 255) // 40
    xbgr[2] = 0
    xbgr[1] = 255
  else:
    xbgr[3] = 255
    xbgr[2] = 0
    xbgr[1] = ((240-h) * 255) // 40

t = 0
mode = 0
last_mode = -1

def on_switch():
  global mode
  mode = (mode + 1) % 3

_BUTTON.callback(on_switch)

while True:
  if mode == 0:
    if last_mode != 0:
      for i in range(_NUM_LEDS):
        pixel = view[i * 4:i * 4 + 4]
        pixel[0] = _BRIGHTNESS
        pixel[1] = 0
        pixel[2] = 0
        pixel[3] = 0
      _STRIP.send(pixeldata)
    utime.sleep_ms(50)
  else:
    delay = 1

    for i in range(_NUM_LEDS):
      pixel = view[i * 4:i * 4 + 4]
      pixel[0] = _BRIGHTNESS

      if mode == 1:
        # Rainbow demo
        rainbow((i + t) % 240, pixel)
      elif mode == 2:
        # Night-time warm white?
        pixel[1] = 40
        pixel[2] = 120
        pixel[3] = 255
        delay = 50

      # Gamma
      pixel[1] = pixel[1] * pixel[1] * pixel[1] // 65535
      pixel[2] = pixel[2] * pixel[2] * pixel[2] // 65535

    _STRIP.send(pixeldata)

    utime.sleep_ms(delay)
  last_mode = mode
  t += 1
