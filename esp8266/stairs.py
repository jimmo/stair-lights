from machine import Timer, SPI
from micropython import schedule
from socket import getaddrinfo, socket
from network import WLAN, STA_IF
from random import getrandbits

import math

_NUM_LEDS = const(162)

def rainbow(h, p):
  # h is hue between 0-239.
  if h < 40:
    p[3] = 255
    p[2] = (h * 255) // 40
    p[1] = 0
  elif h < 80:
    p[3] = ((80-h) * 255) // 40
    p[2] = 255
    p[1] = 0
  elif h < 120:
    p[3] = 0
    p[2] = 255
    p[1] = ((h-80) * 255) // 40
  elif h < 160:
    p[3] = 0
    p[2] = ((160-h) * 255) // 40
    p[1] = 255
  elif h < 200:
    p[3] = ((h-160) * 255) // 40
    p[2] = 0
    p[1] = 255
  else:
    p[3] = 255
    p[2] = 0
    p[1] = ((240-h) * 255) // 40

def purple(h, p):
  t = 2*math.pi*h/24000
  p[3] = int(100 + 40*math.sin(t * 100))
  p[2] = 0
  p[1] = int(150 + 30*math.sin(t * 20))

def green(h, p):
  t = 2*math.pi*h/24000
  p[3] = int(15 + 15*math.sin(t * 100))
  p[2] = int(150 + 80*math.sin(t * 100) + 10*math.sin(t * 400))
  p[1] = int(15 + 15*math.sin(t * 240))

def bloop(p):
  if getrandbits(6) == 0:
    rainbow(getrandbits(10) % 240, p)
  else:
    p[1] = 0
    p[2] = 0
    p[3] = 0

@micropython.native
def gamma(p):
  p[1] = p[1] * p[1] * p[1] // 65535
  p[2] = p[2] * p[2] * p[2] // 65535

@micropython.native
def shift_frame(v):
  i = (_NUM_LEDS - 1) * 4
  while i >= 4:
    v[i] = v[i - 4]
    v[i + 1] = v[i - 3]
    v[i + 2] = v[i - 2]
    v[i + 3] = v[i - 1]
    i -= 4

def blank_frame(v, t):
  shift_frame(v)
  p0 = v[0:4]
  p0[0] = 0b11100000 | brightness
  p0[1] = 0
  p0[2] = 0
  p0[3] = 0
  return t < _NUM_LEDS

def rainbow_frame(v, t):
  shift_frame(v)
  p0 = v[0:4]
  p0[0] = 0b11100000 | brightness
  rainbow((t * 4) % 240, p0)
  gamma(p0)
  return True

def purple_frame(v, t):
  shift_frame(v)
  p0 = v[0:4]
  p0[0] = 0b11100000 | brightness
  purple(t, p0)
  gamma(p0)
  return True

def green_frame(v, t):
  shift_frame(v)
  p0 = v[0:4]
  p0[0] = 0b11100000 | brightness
  green(t, p0)
  gamma(p0)
  return True

def bloop_frame(v, t):
  shift_frame(v)
  p0 = v[0:4]
  p0[0] = 0b11100000 | brightness
  bloop(p0)
  gamma(p0)
  return True

def night_frame(v, t):
  if t >= 170:
    return False
  if brightness == 1 and (t < 25 or t % 2 == 0):
    return blank_frame(v, t)

  shift_frame(v)
  p0 = v[0:4]
  p0[0] = 0b11100000 | brightness
  p0[1] = 0
  p0[2] = 3
  p0[3] = 32
  return True

stop = False

mode = purple_frame
brightness = 0b100

next_mode = mode
next_brightness = 0b100

timer = Timer(-1)

data = None

def on_frame(t):
  global mode, brightness
  x = data

  strip = x[0]
  pdata = x[1]
  v = x[2]
  t = x[3]

  if mode != next_mode or brightness != next_brightness:
    t = 0
    mode = next_mode
    brightness = next_brightness

  if mode(v, t):
    strip.write(pdata)
    x[3] = (t + 1) % 24000

  if not stop:
    timer.init(mode=Timer.ONE_SHOT, period=1, callback=on_frame)

_MODES = [blank_frame, night_frame, rainbow_frame, purple_frame, green_frame, bloop_frame]

def mode_index():
  for i in range(len(_MODES)):
    if _MODES[i] == mode:
      return i
  return 0

def server():
  global next_mode, next_brightness, stop, data
  strip = SPI(1, baudrate=2000000, polarity=0, phase=1)
  pdata = bytearray([0x00] * 4 + [0x00] * 4 * _NUM_LEDS + [0xff] * 16)
  v = memoryview(pdata)[4:-4]
  data = [strip, pdata, v, 0]
  on_frame(None)

  addr = getaddrinfo('0.0.0.0', 80)[0][-1]

  print('Running server on', WLAN(STA_IF).ifconfig())

  s = socket()
  s.bind(addr)
  s.listen(1)

  try:
    stop = False
    while True:
      cl, addr = s.accept()
      cl_file = cl.makefile('rwb', 0)
      response = False
      while True:
          line = cl_file.readline().decode()
          if not line or line == '\r\n':
              break
          if line.startswith('POST'):
            print(line.strip())
          if line.startswith('POST /mode/'):
            next_mode = globals()[line.split('/')[2] + '_frame']
            response = True
          elif line.startswith('POST /next/'):
            next_mode = _MODES[(mode_index() + 1) % len(_MODES)]
            response = True
          elif line.startswith('POST /brightness/'):
            next_brightness = int(line.split('/')[2])
            response = True
      if response:
        cl.send('200 OK')
      else:
        cl.send('500 Server Error')
      cl.close()
  except:
    stop = True
