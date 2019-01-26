from machine import Timer, SPI
from micropython import schedule
from socket import getaddrinfo, socket

_NUM_LEDS = const(162)

_MODE_BLANK = const(0)
_MODE_RAINBOW = const(1)
_MODE_NIGHT = const(2)


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


mode = _MODE_NIGHT
brightness = 0b100

next_mode = _MODE_NIGHT
next_brightness = 0b100

timer = Timer(-1)

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
  rainbow(t % 240, p0)
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

def on_frame(x):
  global mode, brightness

  strip = x[0]
  pdata = x[1]
  v = x[2]
  t = x[3]

  if mode != next_mode or brightness != next_brightness:
    t = 0
    mode = next_mode
    brightness = next_brightness

  anim = True

  if mode == _MODE_BLANK:
    anim = blank_frame(v, t)
  elif mode == _MODE_RAINBOW:
    anim = rainbow_frame(v, t)
  elif mode == _MODE_NIGHT:
    anim = night_frame(v, t)

  if anim:
    strip.write(pdata)
    x[3] = (t + 1) % 24000

  timer.init(mode=Timer.ONE_SHOT, period=1, callback=lambda t: schedule(on_frame, x))


def server():
  global next_mode, next_brightness
  strip = SPI(1, baudrate=2000000, polarity=0, phase=1)
  pdata = bytearray([0x00] * 4 + [0x00] * 4 * _NUM_LEDS + [0xff] * 16)
  v = memoryview(pdata)[4:-4]
  on_frame([strip, pdata, v, 0])

  addr = getaddrinfo('0.0.0.0', 80)[0][-1]

  s = socket()
  s.bind(addr)
  s.listen(1)

  while True:
    cl, addr = s.accept()
    cl_file = cl.makefile('rwb', 0)
    response = False
    while True:
        line = cl_file.readline().decode()
        if not line or line == '\r\n':
            break
        if line.startswith('POST /mode/'):
          next_mode = int(line.split('/')[2])
          response = True
        if line.startswith('POST /brightness/'):
          next_brightness = int(line.split('/')[2])
          response = True
    if response:
      cl.send('200 OK')
    else:
      cl.send('500 Server Error')
    cl.close()
