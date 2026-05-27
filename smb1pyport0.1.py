#!/usr/bin/env python3.14
# pyright: basic
# ============================================================
#  AC Holdings SMB14k Mac Port — Super Mario Bros. (SMB1)
#  Python 3.14+ | pygame | FILES=OFF
# ============================================================
#  files = off  (single-file, zero external assets)
#  60 FPS Famicom-accurate speed
#  HD Mario Maker-style sprites (2x subpixel, crisp upscale)
#  SMB1 audio loops (overworld / underground / castle)
#  All 32 stages: 1-1 .. 8-4 (SMBDIS object streams → tile rows)
#  Everything procedural: sprites, audio, tiles, palettes
# ============================================================
#  Controls:
#    Arrows / WASD = move + duck
#    Z / Space     = jump  (hold for higher jump)
#    X / LShift    = run / fire flower shot
#    P            = pause
#    Esc          = back to title
#    Enter        = confirm menu
# ============================================================

from __future__ import annotations

import pygame
import sys
import math
import random
import base64
import gzip
from array import array

FILES_OFF = True  # Procedural only — no file I/O for sprites/sound/levels.

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
NES_W, NES_H = 256, 240
SPRITE_HD = 2          # Mario Maker crisp subpixels (16-grid → 32px art)
SCALE = 4              # HD window upscale (256×240 → 1024×960)
SCREEN_W, SCREEN_H = NES_W * SCALE, NES_H * SCALE
FPS = 60
FAMICOM_FPS = 60          # NTSC Famicom frame rate (1 physics step / frame)
TIME_FRAMES_PER_TICK = 24 # SMB1 stage timer (~24 frames per count @ 60 Hz)
TILE = 16
GRAVITY = 0.32
MAX_FALL = 7.0
WALK_ACCEL = 0.075
RUN_ACCEL  = 0.115
WALK_MAX   = 1.55
RUN_MAX    = 2.65
FRICTION   = 0.06
JUMP_BASE  = -4.6
JUMP_RUN   = -5.35
JUMP_HOLD_FORCE = -0.32
JUMP_HOLD_MAX_FRAMES = 18
PIPE_DESCEND_SPEED = 1.4
STAR_FRAMES = 600
INVUL_FRAMES = 120

# ------------------------------------------------------------
# NES Palette (canon subset)
# ------------------------------------------------------------
P = {
    'sky':       (92,148,252),
    'sky_night': (0,0,0),
    'underground':(0,0,128),
    'castle_bg': (0,0,0),
    'water':     (40,80,200),
    'black':     (0,0,0),
    'white':     (252,252,252),
    'red':       (216,40,0),
    'redhat':    (216,40,0),
    'darkred':   (140,28,0),
    'brown':     (172,124,0),
    'tan':       (252,216,168),
    'flesh':     (252,188,176),
    'orange':    (228,92,16),
    'green':     (0,168,0),
    'lgreen':    (60,228,60),
    'darkgreen': (0,104,0),
    'gray':      (124,124,124),
    'darkgray':  (60,60,60),
    'ltgray':    (188,188,188),
    'blue':      (0,108,228),
    'darkblue':  (0,0,188),
    'yellow':    (252,228,40),
    'gold':      (228,164,0),
    'pink':      (252,160,180),
    'purple':    (140,0,160),
}

# ------------------------------------------------------------
# Tile char map
#   . = empty       X = ground      B = brick     ? = ? (coin)
#   ! = ? (power)   U = used block  [ ] = pipe top   { } = pipe body
#   S = solid stair F = pole bot    T = pole top  C = castle
#   o = coin        L = lava        = = bridge    A = axe
#   - = invisible block (1up)
#   ~ = water       # = underwater  block
# ------------------------------------------------------------
SOLID_CHARS = set('XB?!U[]{}SF=C#')
PIPE_CHARS = set('[]{}')
BREAKABLE = set('B')
HIT_BLOCK = set('?!-')

SMBDIS_LEVEL_BLOB_B64 = (
    "H4sIAAAAAAAC/7VdS6/mNnLd+1fcxSzbGVF8SfbKmRgBgpsECCYIsgr0nBiwu41uO8Hk1+fq1FenWJJu+7aB2TR0+YkiWazHqQfZ"
    "337/L9//838+/evf/9P3f/rz0z989+fvvvrq2x+3/9l+fApfpz+Wr9NX3//Xn6ZPv/y4ffdxm8I3Xz393To//aGWd09/WNeXf+b5"
    "5Z+0vPyzTS//hKMtHG3L0ZaP9/L66BWOv8bjjaXou9HaRm3r0vH1+dErsX1I/PiI7x5tw9E/H73245/h0St2Oq96vNEf707HWD06"
    "HL/O+fHuvnPV6bTiXlcsX4+6JpsFnuTXqusJOvdp0jfSaZ7HDz1/zfjIotTljF+dZ/+yO/k018i5Hl8bjrUn7k49JpePoTcZ6/jw"
    "2tI5jLoTNSvF66qTW7kLEb10T0e299zJjMVhEng6xlqmli59p9SoWP6CiehcjX+iPF3o8oadjCfqpCt18HXhLD5NpM4qbZf9L6RO"
    "mbn/Wdfeze06pX1mO8fquE7MpB6rCLqK6ueApwd33/Gz7sRrlKgnSmSlRH/wxDQqn2Ccgq+PHLEo79iadl1OkVlr/8FL26vzGU7z"
    "KVcZGzYl9BZUycTjywXrPp7i8cqGV6rrP+j0ul7ZEE/55pvd9ugqhN60HeNb225dbS+UM5L/rvx4tOEHDL11+kPo9HMy9aDCh1Ep"
    "ENgKyJ0IyW8TNX4dX4j6jx8//Pp+dap6Oj4wHNu4JRWaMCgVE34FW2PP46MXFDTYANyLN6C+p6RKtz+etrFlQbA7votV9HxtONa+"
    "DLq929COlYr2AgHQYZGud8zj10kFvXHfjI12ymao+vlV3nMsA91Y9d1qEo13O2oz0p1vmDAE36u7NS7BzZ0Kuz+mvRycUrBRx1MI"
    "zq50pzbViUHar4OVr3s3mOk/Dgaai8LrHOdDsQ3HK+umv06dWtaoDJWiaggI45zw2vF1Ct1jAarYIBa9qi5wVfPapDoZbfhI9LIN"
    "nBFbwXUi4MlLPTdyYbBCIMDGqaSksoZFYbvnwcnl0ZTRPqkMz5VmuzP+Uo4mL0DU4zFCYi8MAwED7WRopa7Q5Hh37VTpZc5/4PxB"
    "wE57zVRVS9YJ77F9o6FTONGJ+jeQMzABcAGmOJA6JeoqZEN0xR1ZoecTqIB3Z9IpS1srR7HqtjffpUSRAdwC4gv48XqgUpaAVioZ"
    "JeqaBoqWGDVoHZ3/FFVLdWRvfAlqQYzicNF3G7WnablIbSbcEe/AW/xjPc1/8EawV60PtgF4XGCJ8BTt6aLHoL0gmWCxlaYHvAO9"
    "mru7OXmmGHU+A+1HR1kI3M+VOwiQQDbe2A4JACl7U6SdTjRSBVHkKmVkp4yiKxyBgfyIXRyd8FQKSiY/jd6y40l7fbu9X58+7E/r"
    "9Mv09Mv28acf3k+/fPj49N/bx+3ph09P04+fPjz9+mlbn+a/Pv38w88vje9/+fjhaXohkLe23TdXkuYTSUPwELRTCAUiiFbBpnYq"
    "EN5WJb6xs5etePL9Sc59Ng2ub0Sqe1ODsOkP4WtFCQQr9aJzlx8//Lo+yUpBoh/ey1+fDl56ml4om08mKJg3dfDiRGUmQIF/xoD5"
    "3BnQE8ihBV2qSiJEH0IsyzpWVCdtE4SSnEORCKUzUZKB2miaxKEcCPyo/Wcil27UX0tuMczCdw2mCt7Jd8b7tFBa7wUAOOuQUDSQ"
    "e4Fd9IvgPvHThVOeOI2NUw6csjfXwJ6i9sr1XRAaEFGA4fjolelBjPLG3fJOkpGv2q97HQS1H/zf6ePPT//34f0GofSc+MIvJwYs"
    "39whytNkvCkBDJqoq1YKjKC0WWVqU6lpJLdTXYU3Aj+3s61qLzHZGIbYf15Uwpv+sNFzi+XCCfmuqmbFqDYzxPgtRkG7eVfxZLEJ"
    "zUJs8VBHjDcQJ8zLnQI8kZ9GrrLzRIBp1MJaxEcAhhK9/6RToH0A30GG0uZMy2SAyeGyhSpg4F6MXOnEJ0HCRXvR2qxEFNFjZYFk"
    "tdXWjsNOdKBxhZiIwSK7CwL0jszonNXemznBfWzbzW11Gz5yyba5ZmG3wXkAD0Cu6MgPIx8f9QmWAxsioLQ4nxoDllcoU0+y19OO"
    "YkhAHpO4hXy3bA4WS8BoazkbbAGzlbLTIT05uDqfbqzepztMxiiK6I1mLz7M3tnz6sNrZg9+AVyKTZHzNN05NqcP0o6ae2JCnKg6"
    "NioBWVJydr1zem07CbbxT9fuCBRG4aimsEbqmuzVwezcCYEvMuodsD8W+u/v1+3jX66RjI5eSJgokSab5rz0hEhz6x9hxhs72OdG"
    "uizSa3TGqChMa5RwIZwaVWP2ajURVe3JahDnKWiAVOxvUegFoGGAC6o33QGfG8L0V6MpfLTrjBF3ipMiBiio1W1qpFIYbpQC/J5K"
    "9urlIzrZRdc597qmmauz0IlEdlSIBChVZVF5Mga26cArVFIYrcrcUudXo8jT/OH9r5+ePn748NMnjwV+mt7/9SGjVyJG5/yCTBKb"
    "N1xa9U9EPpbqNDO6AZkTNsm7oH/jKHN3ksYcTCfJD6D41H5ENIIJ8MgBg+6OdJ0Ya7duvZsOdPzkkdOLx3ODmj4ddrtRZP9xvOcE"
    "UXapargKBFq4m5tBeP4pM6qX/iK+9c4d7V9cZDf8id0DV5vpYG4Ouif+CZVW3FhQ96mqSz/wT+yvOAyYIYI1tXUYJM8zaC/sT7KA"
    "A53OwceuRt2yxJUvDH0s9S1b8widkyRk3sRBxUDD8WY+bqBAQhdwXshk4d2Bqk2mvyo14TjsLl7w3b99/91nM4bPdxnD0VEf4hAZ"
    "i4kkHEJlsO6QrhVYOLRaQIIcUbVbTSqxCC5KUGBrwcvCdrh2sEUCLidVdibxw9hG9WEiMkcIiWEUtkVpawOcXaGamJRTJQPQa1uq"
    "7QyHoAp74BtNf+JY+brK9USPaGYcdWXbZrHV2urfwPbIuVYmKiZSeHc0hE+BRcP/lPDSply9klZICScCJn4XqVrj8dXlW5/v8q35"
    "C/glcw8hX0Wtxih/qQ0qxluMLgmFkLgLrSEA0Y0uY2Lsk0+rPOma2A4uAfl7finzS5hEVNAJuavYQ77bMQU+sZfMemhjAFBx5zVk"
    "pQH0b3V7OBZtBwbBXCWThtVkGi3HZfD8C2ABVhh0cnPQKEbc1aJFpYbRC6ECjLrxSfrv1l93+dz+rl2rZI4SyRRb+9YFpwFm0mU9"
    "7fffnKM1M/98l5n/Ei240zMWkBTaWA56VaKVGpjEqaQyYL3KQqAECH8njW1bkEB0XG31GUaG0YDGlbH47kodtcl7zr5PGgFq9Kwl"
    "BKlxmaGIRFKRcy27rmvkE/Y2MVFJTb6Qq5eTFiOAG0jDQog76VMd9UszKb84fbJzXg/acg2mnSPtD/0Bs2Zn7ao/COwEpyUn4yeu"
    "XHWuxp+7k9ZXuTKeODL9fo4smogjNSMph0IOyOLAtolt69hK4L44GCd+UtU2yQV1tIQ61rp5juoV6KE/Kk8w/xLbscroUUJPPRcV"
    "KcmqY8v9HXuF39cr6X5Z/8r5ey4545Di7Npw0mzTBRFFo8Edl4m2U2wTNOCU+fQZLaiUJ/e9QQvWE7/l32PXbf7T1gbk5tMKzf71"
    "qi3xTRQWFOWcnNWSZdpa7MtAVxeRDCBK6rJK+4Ne2Ahrq+yP2rTSO/sXnP2b2euCQVqbJIRgr2jYJp30fhtLbcaKDjmsXKtwiI7V"
    "fG3QJ2Ab5C+h9yKL/BJr8ZK6+5m9zrZ+0zx57NrUB2ZoK189NYbrWLa3Z4nona33NAx8N26u8ueEdEX6ykX63oQLfo9EDCeJKF4i"
    "yhci3emGc8AvI431ymD1yLywo7Bho8Digsk8GHJTEDK3BUXVS99OOZBRq81Eew0qWht3HgldBAM3/upRWm/ySc8GklYnxogCR71y"
    "jrQvji7GDYvUAShvw9XdTceSIwdn+1D/yAxMIltNq0ZzjRoYFYUY09hmexLpPb6urY0HnSd7i0/fxoNHkdjzXZEYZJiJNcQresoW"
    "MtNSbMm0Jqr+EEsNxMaTBqZABLgbmZUvE20hLDsTSoi+IKm487uSBunUTxZ0Ftpe8mPQDiNTcWFniA3lJrmdYWH7KO2cF0oZem1D"
    "HV/qWo8ZqQdEPAGQEWLFu1KdHNX4shfwKgDAFHUEdMVcpZ4u6p9JKY/4KXotnOHCMpCVc4X4jH0blcLyx0V3ScYH6uJMZDdDa9mW"
    "oDwoGRaQr7vTXp5z6KdLQeKVcyQBTK/MODQZN/WtNCRqetA6M8yDpJ2E8VycHTHFgUoKJSKGP6GgYJXgY5tlpi1CHkYC++zVVIXJ"
    "TFr8GPxqVq5G/IKeOTJGaPjGytlsfIoEvNGtS6rqksZUZV6kxgN5q31L3gJMqt8w6im6IHm+2kYAbUegqYTx6f1g1RKXwqy71gKg"
    "HXsDDbwz6lvIV7Ob4fYabx1lkc93ZZEApr3nLcyLswYK2XvmcAJ9Th3H6CUR307TlNAeC9seURdXzhZYdxBY2BYUYcq+LG0kAp7O"
    "Tp7FRyCbG3ESNhdabdde9dQ+v2vboHP2oKXxjDcl+keQlD547l9058UCMYK60GciXVZy78b+Qg1X+w6nXHyxSivOEDP2O4v0X3f4"
    "SCQ839Wiwj70V+0BsUBCJBpNKOWSIVceHogMRr6xmLwkpZ8Yb+ezwqhkPpmUYdSJFoh8AWAJ4qJ6xnoJVjcQLN9UvuAIKCAQRiLn"
    "BhYlCF/17bkX9ALexz8bJbpU5bXRjYXZgAaI1+HdnTMMXNdDZ16oIVQeqBWz8ZDGSGxdRTlvia5EAuMjdg8OFU+fEok5cOU9OQeo"
    "d2AvRG/r1BZ4SdyVGlxiJ4xxg1+qrLqtJYynveVqMqlZa4tVV2vfNdI5sj+KGQptdNFYrsSDiwZ/bYPwNFBKltekJJ70YHZ6ML6i"
    "B4slcYI6bZDh4iqETaKM8wrrRVfqhVF+1TWRm4xqQBaR2RkwreRpvGWOrJ4FERYNNwxse9jitgRXYhzki0oi7mwDN/dTi84G6mes"
    "MLOGurANOJMegliF6HgQXo7oHCsT2ttovelHcXc7pSEoVKPDHoxYDaa3+O7MtpltIkOh5XcpsTWJ4ruFcixjOV3Ys55H4vaZoH1R"
    "v6TubQXGG3gznHjTvNfOaXDyIfRmzyiz7cYNhRZqn0LeNHkdaQGkFl2l1KzdaqvmWB3RVVlarTobR0SHrjpmgCdaVXrlFpdcrT6/"
    "OowgSbzaatWRY8lsou5BoS4G55W9zZ00ms4sM3XeTtSaoJtiu/MiVYuLoUpEnF9ancxt/JrJ98B5naKx3lrsprcHh/qm13lIyvaf"
    "78r24Ud83gOd1MRjhmLKJOGme9sryrXqLbiWgnCL+kG5a30uCERgwf/Icv7EY2LohfIf6lNUGiViPagRccGS8oF4b6k92QfNBCqt"
    "PT3YXtt68yXlzFJb5SWrYbYiVe93cr/oI0ulO9vt5IZwBLXC6q0Ycd3nrdjksP36GrbXow7Pd0cdXtvzwj2Xc5lVuQoIYXX+XKPn"
    "Fs0ZIhIDlm8yNjjwurU+Voo3b+yqdsSDSs6njz6aQU3eeIFJA0bMvGWGnwa+O3L3L/11hswwWX8bIfBUC5Aqdw+ovmdAVnBU1Z1e"
    "WBWP0NFYW78FtL3QS61p4gHXNFyyYZBM+DgIoIM1Mw+IIRbM/TqPwOoTtAFzAq9JrCO3uSLB2IsisspecpiX5z5Hno2bGMEcVH/2"
    "fIr0brPwfJtTscJzqfoj30crjnud572tHN+E44QHaOHFpiTaCR0HWl+qZOx4Ez2glRZHSrFiq7GLx8Hgq+1koZcWBzfWkNjMENXE"
    "L+2uV2DBo+GoFJ2PCmwtcR1avYUeM+39RFRqFmfySJ0unnlGm9GgqBs0Owww0PedqD0k710512T2zxWPJ4egR7OVrKtZHNJESKVw"
    "+nj6LN46HzN6vj1mJEeGbhznlebutSBwPrGnHUtCVPQmlme5tYVUDhaHGlqPy+pQRmYtRlJ5ig4BE18t5rmTD3ZGEHuOlZzul7FG"
    "akHGULro4iKD231YPjiyC73DnfG9htPGlsSQdiTIVl4CsPHJYqnzdUffeFLq+f6kFIgSWv3e0btPu9udjvhH7Nve6p3FH+dFplxA"
    "zOu1WadsQXSGO18ZZaPh7giFYnSZ8ORccznBUVgR29M2TvorJMZ68WsoGrYCAaAo8B3Cx2FxAIrBcAGBPBiGL42BAXqZtcoYQ/CR"
    "0xfk3RPDs1SZSQbkPQQkcK6YDaTAZpJ8r11zGRAAeeK7zbr2Fk6CWTEHxKRAr8peALaJoZTgwJokWpjng/oTcJz0mygNCcrKlgBa"
    "WHAVLfS3uQN3d2axnNnJalDqb2J/IuDMzR5c9mlhRmgnMs7sJfUfrHRir5llAnL7SXS1VJKvSSQvjw2SxCOx90yiwhpi/H1v14Wc"
    "EVRsJhNlMhFiUYFHEW2zZn0j0DtJxFaVv8KmJK1enbmd5pOkMw1srizvpSDRT+m5LgwoOa+57VVJ79Fiwpl+QmCsPbpsoVXtfUke"
    "qpyNV35bsoCA00LpHZNADPDAOYawS9V6p8Z+ZlA4Ur0yKCx15kFhkgSDFpeO6K2kiQXoNGobk5x517FGGrTparwkyTpqWXEmpK0M"
    "TQ7OqRsZmoTj0vMGho7BAbStbiwLxowslxOPk4BJiob39qjGzqCwhH2LSvNAJ75PFqhsIZkYNgm5aSJqYhrXAoJkjIGBGzmJyxLm"
    "nrssZ/zcDJs0BzNywbu4YGLBUo6jJmfYf/Ps6fPt2dPgrKeZdLNjC+ndRTuG1trBnpq/UCwLzX9hGnlyCXBLwsvh1cScX1LnDyYB"
    "nE7QMTDIY4cj+0GLMAqfJhewB2uiunLnkwSJ8l16+STWFhf6TZ/J8E+0owHLNQfYqfdono74x3ySopCujcPVaHFHLttEojOPSjem"
    "qKkeLLpOb9/Q5eLi7COPj0zMEG2nWn5GYnrtFdnL1jDzabN1Le7IF9sHiurE20hmnvTOrle9oVfPnPHKXNFeWqFZSXnzzywj25PC"
    "D4XcVufKwY6VwI1qYWb2VvwCUoM7Uuk3DmzbR+f38+IlUa+JQhfeuewA2wa3X01GzKjJEYxCj8ibWmUTdYu+2X6d421vj85f3AeG"
    "2PIrLt2yu+Iy4CCrvclO14wEDuaQr3SSV+oqCcPnS3nGaSysM5BY1WsNvts4fbRqmWQrzr5trNtMVXV+ZvChMPhQXLHNyITPyNIl"
    "cz9nup8+hS5fKwz2VyYFyru2qDlI4r9FFh2Pm3XEIwP1bW8p7NTaN9DQKL/0DlD1TIkyLWtzaNKXZ5a0RKYLwLDM6LcSmdrrNZYc"
    "ziw5uozRDUvunEAgDMqmr92GV05x4MRGPq2L0yvUYZZ1W8jSC5PxwtK7yWR7znXgdZIi64vPzm1WEeE2gXmiKbj6isRvZhdlWAdW"
    "bfGmqUstgmZOg8/5Bz2qMZ7ykkW/VF0Vj4EnGfUUZzO95JjLbGnPNxK1/0Kbd1d30rlIS0d4VhjT3F1YaycNhJF7N68mD++sx+/M"
    "vtcTBLGrCKAN59cgCAskRobzO4Zn6Y8s3NiFi0pWIkeG3ZynLpebBq0VDYQbPaMCIxOQLLcO3Ni+uruTQnDpwcUF7uSILs/z9v6+"
    "i5Uob5BZX0olLoEzjc3tTJhTrxUmhy3F2XOtPdeaS0tDHEQHbSvFtykXSUqX0SXtewbxLVpRvyhI197r8Hx/r0P5giBd4VVYqQ3S"
    "AdtMTFT2DLvD/CFJJ0UAxaVikyoX0XejGsLeaNJp5JK91uSKhGQ2m1NJ6bOhwXgmhdWDliteL64aPTDnXOn4ynnarhUWMMVsCNMq"
    "jMjeu8tlG66E4wizN/CpqfFM7RVollm3/lZLObAOb7yJcvMu0Di8rQ4ugGyv3W+R5AauNn3bBXfoYaoO5leSc+suiZ5MIloprEUV"
    "ZhdIX1lDZKWsgaRH5Vlu4HRrQDLLqTPxS+KZNikOk1/bsZIvZ0ExnRzRLhoVk+MqWoKYeewKuiNzXbm/OdYR2wK1xEqQ3g7hZVcw"
    "L8cfYnvBpVSuc67JiiwLj0+6IxgDe4EGmU6inKgnrWY3w4Xzag4t0DAmpl6Tu0ss0UkbGaKSPSCi3nlAs8aL0zJY/GvQuc588ub0"
    "LiY1Mo0gh9OtfCq1LhyoNPBdC/kJ3mLBNNNAAAJyl8HmrtIFNXABrmyE8xkuEQgeYwnc7/1z0Yd0J5b928XSdEtzptH5pnbiLvH0"
    "rRhBntiWrP3YEnFmtcdC5GcnP2bmHvwJKIy8cQ6VdUlN5RXjExaA4zZtXCF8+c5OOGbekORuE7DqOTt/Z+e2ut4q0R3Td06XQytX"
    "ysvE+DuZI3FzKw3kaJWaVFenen9fDVVZtygrtOqRraVGx6rtzqrh7eyZhXlrm8MeCP6sEnk6sb/d6NBfam8ny2Hf1PtLGM6dLWi+"
    "m8ggrC3DnzC+zAv0vLNvpaPdnKNNuul1ufJG0SxH4rUuEKsHSLisq3ypMH7xZT7Pr17mIzIbLjJrqU+7/UL0a+Fpo9LWaqXk579r"
    "cPi86tDma7Odbk907wf1zzC5x4Cu2rMyubZ/4Vhismh7c7gaLyKeTC5FOCURaMM8Fdqd4mqfChNXlRmdyrEGPo2+Yoq9ENeUp+zO"
    "YWRWAzAkPhd3X3JmdSymfqFLu8uD32XTQJEbHGsLR2RHRloW3pOV7T6VZKMqf5135Ia37G7pcOGozEugMm/hBIrPDb8pNejY2MoF"
    "MNV7iP62i52eby52kuinGzjyNnYQZGfWMjHwVdwhGDCKuLY82jhTgJryDnf8vbP/AYTvFiu37jX4W4QNVDExbmeXDMxkFED7zJvX"
    "eFeyHBCPrBghs0crV2OQiO7FQsMrxB+dEpQk5sTD4bcXg8iVVs83V1qdCE9yb1ygXbQ2s4oPNnclKCRamAgFJ1a4NHFKF5gMjKL0"
    "jITLNYK9Tyh6h+F0apVek9xyGzVRiqHJ/yPXZe+as1m4caW2PqQch6QM281ieDcwpNy77YpUZpLv4JJE/FkV/Lj/ow11p2bz3dk9"
    "WOqVzhV1yGKRR56HW5n83Onl7m4sUAm+aWJ/OU+XWJtEg27pwkgWIBuPk97dM3HW3sGb7bxw9meIGZx4jXk/exfZ891dZGOLl02c"
    "zyewKzXdbDcxqBLhvaLj6Sy33bky825Pf2fXzlisreP/ARchdrToaAAA"
)


# ------------------------------------------------------------------
#  SMB1 disassembly import (doppelganger SMBDIS.ASM via gist 4048722)
#  Embedded gzip of ENEMY OBJECT DATA + AREA OBJECT DATA (.db hex only).
#  No filesystem reads — single-file build ("files = off").
#  Raw streams: LEVELS[k]["smbdis_object"], .get("smbdis_label").
#  See: https://gist.github.com/1wErt3r/4048722
# ------------------------------------------------------------------

def _parse_smbdis_db_sections(asm: str) -> dict[str, bytes]:
    """Parse `Label:\n .db $xx, ...` blocks into label -> raw bytes (NES object stream)."""
    out: dict[str, bytes] = {}
    cur: str | None = None
    buf: list[int] = []
    for raw in asm.splitlines():
        ls = raw.strip()
        if ls.startswith(";") or not ls:
            continue
        if ls.endswith(":") and not ls.startswith(".") and "(" not in ls:
            name = ls[:-1].strip()
            if name and name[0].isalpha():
                if cur is not None and buf:
                    out[cur] = bytes(buf)
                cur, buf = name, []
            continue
        if cur is None:
            continue
        if not ls.startswith(".db"):
            continue
        rest = ls[3:].strip().split(";")[0].strip()
        for tok in rest.split(","):
            tok = tok.strip()
            if not tok:
                continue
            if tok.startswith("$"):
                buf.append(int(tok[1:], 16))
            elif len(tok) == 2 and tok not in ("db",):
                try:
                    buf.append(int(tok, 16))
                except ValueError:
                    pass
    if cur is not None and buf:
        out[cur] = bytes(buf)
    return out


# Area object stream labels per SMBDIS.ASM comments (1-1 .. 8-4 main areas).
SMBDIS_LEVEL_OBJECT_LABEL = {
    "1-1": "L_GroundArea6",
    "1-2": "L_UndergroundArea1",
    "1-3": "L_GroundArea7",
    "1-4": "L_CastleArea1",
    "2-1": "L_GroundArea9",
    "2-2": "L_WaterArea2",
    "2-3": "L_GroundArea8",
    "2-4": "L_CastleArea3",
    "3-1": "L_GroundArea5",
    "3-2": "L_GroundArea22",
    "3-3": "L_GroundArea1",
    "3-4": "L_CastleArea4",
    "4-1": "L_GroundArea3",
    "4-2": "L_UndergroundArea2",
    "4-3": "L_GroundArea13",
    "4-4": "L_CastleArea2",
    "5-1": "L_GroundArea11",
    "5-2": "L_WaterArea1",
    "5-3": "L_GroundArea7",
    "5-4": "L_CastleArea3",
    "6-1": "L_GroundArea15",
    "6-2": "L_GroundArea4",
    "6-3": "L_GroundArea14",
    "6-4": "L_CastleArea1",
    "7-1": "L_GroundArea20",
    "7-2": "L_WaterArea2",
    "7-3": "L_GroundArea8",
    "7-4": "L_CastleArea5",
    "8-1": "L_GroundArea17",
    "8-2": "L_GroundArea19",
    "8-3": "L_GroundArea2",
    "8-4": "L_CastleArea6",
}


def _load_smbdis_object_blobs() -> dict[str, bytes]:
    raw = gzip.decompress(base64.b64decode(SMBDIS_LEVEL_BLOB_B64.encode("ascii")))
    return _parse_smbdis_db_sections(raw.decode("utf-8"))


_SMBDIS_OBJECT_CACHE: dict[str, bytes] | None = None


def smbdis_object_bytes(level_key: str) -> bytes | None:
    """Return NES area object byte stream for `level_key`, or None if unavailable."""
    global _SMBDIS_OBJECT_CACHE
    if _SMBDIS_OBJECT_CACHE is None:
        _SMBDIS_OBJECT_CACHE = _load_smbdis_object_blobs()
    lab = SMBDIS_LEVEL_OBJECT_LABEL.get(level_key)
    if not lab:
        return None
    return _SMBDIS_OBJECT_CACHE.get(lab)


# Per-stage presentation (SMB1). Layout bytes come from SMBDIS area object streams (decoded below).
SMB1_STAGE_META: dict[str, dict[str, object]] = {
    "1-1": dict(theme="over", music="over", end="flag", default_time=400),
    "1-2": dict(theme="under", music="under", end="flag", default_time=400),
    "1-3": dict(theme="over", music="over", end="flag", default_time=300),
    "1-4": dict(theme="castle", music="castle", end="axe", default_time=400),
    "2-1": dict(theme="over", music="over", end="flag", default_time=400),
    "2-2": dict(theme="under", music="under", end="flag", default_time=400),
    "2-3": dict(theme="over", music="over", end="flag", default_time=300),
    "2-4": dict(theme="castle", music="castle", end="axe", default_time=400),
    "3-1": dict(theme="over", music="over", end="flag", default_time=300),
    "3-2": dict(theme="over", music="over", end="flag", default_time=400),
    "3-3": dict(theme="over", music="over", end="flag", default_time=300),
    "3-4": dict(theme="castle", music="castle", end="axe", default_time=300),
    "4-1": dict(theme="over", music="over", end="flag", default_time=400),
    "4-2": dict(theme="under", music="under", end="flag", default_time=400),
    "4-3": dict(theme="over", music="over", end="flag", default_time=300),
    "4-4": dict(theme="castle", music="castle", end="axe", default_time=300),
    "5-1": dict(theme="over", music="over", end="flag", default_time=300),
    "5-2": dict(theme="under", music="under", end="flag", default_time=400),
    "5-3": dict(theme="over", music="over", end="flag", default_time=300),
    "5-4": dict(theme="castle", music="castle", end="axe", default_time=300),
    "6-1": dict(theme="over", music="over", end="flag", default_time=400),
    "6-2": dict(theme="over", music="over", end="flag", default_time=400),
    "6-3": dict(theme="over", music="over", end="flag", default_time=300),
    "6-4": dict(theme="castle", music="castle", end="axe", default_time=400),
    "7-1": dict(theme="over", music="over", end="flag", default_time=400),
    "7-2": dict(theme="under", music="under", end="flag", default_time=400),
    "7-3": dict(theme="over", music="over", end="flag", default_time=300),
    "7-4": dict(theme="castle", music="castle", end="axe", default_time=400),
    "8-1": dict(theme="over", music="over", end="flag", default_time=400),
    "8-2": dict(theme="over", music="over", end="flag", default_time=400),
    "8-3": dict(theme="over", music="over", end="flag", default_time=300),
    "8-4": dict(theme="castle", music="castle", end="bowser", default_time=400),
}


def _decode_smb1_area_object_stream(stream: bytes) -> tuple[list[str], int] | None:
    """Decode SMB1 area object bytes (after SMBDIS `L_*` / `E_*` label) into 14 ASCII tile rows.

    Object encoding follows the SMB1 area object format (see nesdev / MushROMs SMB1 Level Format).
    Returns (data_rows, timer) or None if stream is too short / invalid.
    """
    if len(stream) < 3:
        return None
    hdr1, hdr2 = stream[0], stream[1]
    t_code = (hdr1 >> 6) & 0x03
    timer_map = {0: 400, 1: 400, 2: 300, 3: 200}
    timer = int(timer_map.get(t_code, 400))
    floor_pat = hdr2 & 0x0F

    H, W0 = 14, 240
    rows: list[list[str]] = [['.' for _ in range(W0)] for _ in range(H)]
    page = 0
    max_x = 0

    def grow(cx: int) -> None:
        nonlocal rows
        need = cx + 24
        if need <= len(rows[0]):
            return
        for r in rows:
            r.extend(['.'] * (need - len(r)))

    def put(tx: int, ty: int, ch: str) -> None:
        nonlocal max_x
        if not (0 <= ty < H):
            return
        grow(tx)
        if 0 <= tx < len(rows[ty]):
            rows[ty][tx] = ch
            max_x = max(max_x, tx)

    def tile_x(xn: int) -> int:
        return page * 16 + (xn & 0x0F)

    def apply_floor_base() -> None:
        """Baseline solid terrain from header floor pattern (simplified)."""
        w = len(rows[0])
        if floor_pat in (0x0F,):
            for x in range(w):
                put(x, 13, 'X')
            return
        if floor_pat in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0x0A, 0x0B, 0x0C):
            for x in range(w):
                put(x, 12, 'X')
                put(x, 13, 'X')
            return
        for x in range(w):
            put(x, 13, 'X')

    def static_obj(tx: int, ty: int, v: int) -> None:
        m = {
            0: '!', 1: '?', 2: '?', 3: '-', 4: 'B', 5: 'B', 6: 'B', 7: 'B',
            8: 'B', 9: 'B', 0x0A: 'U', 0x0B: '.', 0x0C: '.', 0x0D: 'T',
            0x0E: '=', 0x0F: '.',
        }
        c = m.get(v, 'B')
        if c == 'T':
            for yy in range(2, 12):
                put(tx, yy, 'T')
            put(tx, 1, 'T')
            put(tx, 12, 'F')
        elif c != '.':
            put(tx, ty, c)

    def pipe(tx: int, ty: int, v: int) -> None:
        h = ((v >> 1) & 0x07) + 1
        enter = v & 1
        for k in range(h):
            yy = ty + k
            if yy >= H:
                break
            put(tx, yy, '[' if k == 0 else '{')
            put(tx + 1, yy, ']' if k == 0 else '}')

    def row_extend(tx: int, ty: int, s: int, v: int) -> None:
        ln = max(1, (v & 0x0F) + 1)
        ch = 'B' if s == 2 else 'X'
        for dx in range(ln):
            put(tx + dx, ty, ch)

    def col_extend(tx: int, ty: int, s: int, v: int) -> None:
        ln = max(1, (v & 0x0F) + 1)
        # End-of-level vertical stacks → flagpole (not brown ground/brick towers)
        if ln >= 6 and ty <= 2 and s in (5, 6):
            for yy in range(2, 12):
                put(tx, yy, 'T')
            put(tx, 1, 'T')
            put(tx, 12, 'F')
            put(tx, 13, 'X')
            return
        if s == 6 and ln >= 4 and ty >= 6:
            return  # skip mid-air ground columns (decode artifact)
        ch = 'B' if s == 5 else 'X'
        for dy in range(ln):
            put(tx, ty + dy, ch)

    def misc_c(tx: int, b2: int) -> None:
        s = (b2 >> 4) & 0x07
        hlen = (b2 & 0x0F) + 1
        if s == 0:
            for dx in range(hlen):
                put(tx + dx, 12, '.')
                put(tx + dx, 13, '.')
        elif s in (2, 3, 4):
            yy = {2: 7, 3: 8, 4: 10}.get(s, 10)
            for dx in range(hlen):
                put(tx + dx, yy, '=')

    def misc_d(tx: int, b2: int) -> None:
        Sf = (b2 >> 6) & 1
        vv = b2 & 0x3F
        if Sf:
            nonlocal page
            page = vv & 0x1F
            return
        if vv == 1:
            for yy in range(2, min(13, H)):
                put(tx, yy, 'T')
            put(tx, 12, 'F')
        elif vv == 2:
            put(tx, 12, 'A')
        elif vv == 4:
            for dx in range(8):
                put(tx + dx, 11, '=')
                put(tx + dx, 12, 'L')
                put(tx + dx, 13, 'L')

    def misc_f(tx: int, b2: int, b3: int) -> None:
        if b3 & 0x80:
            pass
        sub = b3 & 0x7F
        y2 = (b2 >> 4) & 0x0F
        Ln = b2 & 0x0F
        ty = min(y2, H - 1)
        if sub == 0x30:
            for i in range(max(1, Ln + 1)):
                put(tx + i, 12 - i, 'S')
        elif sub == 0x20:
            put(tx + 1, 10, 'C')
            put(tx, 11, 'C')
            put(tx + 1, 11, 'C')
            put(tx + 2, 11, 'C')
            put(tx, 12, 'C')
            put(tx + 1, 12, 'C')
            put(tx + 2, 12, 'C')

    apply_floor_base()

    i = 2
    while i < len(stream):
        b1 = stream[i]
        if b1 == 0xFD:
            break
        lo = b1 & 0x0F
        if lo == 0x0F and i + 2 < len(stream):
            xn = (b1 >> 4) & 0x0F
            b2, b3 = stream[i + 1], stream[i + 2]
            if b3 & 0x80:
                page += 1
            tx = tile_x(xn)
            misc_f(tx, b2, b3)
            i += 3
            continue
        if i + 1 >= len(stream):
            break
        b2 = stream[i + 1]
        if lo == 0x0C:
            xn = (b1 >> 4) & 0x0F
            if b2 & 0x80:
                page += 1
            tx = tile_x(xn)
            misc_c(tx, b2)
            i += 2
            continue
        if lo == 0x0D:
            xn = (b1 >> 4) & 0x0F
            if b2 & 0x80:
                page += 1
            tx = tile_x(xn)
            misc_d(tx, b2)
            i += 2
            continue
        if lo == 0x0E:
            i += 2
            continue
        xn = (b1 >> 4) & 0x0F
        yn = b1 & 0x0F
        if b2 & 0x80:
            page += 1
        tx = tile_x(xn)
        ty = min(yn, H - 1)
        S = (b2 >> 4) & 0x07
        V = b2 & 0x0F
        if S == 0:
            static_obj(tx, ty, V)
        elif S in (2, 3):
            row_extend(tx, ty, S, V)
        elif S in (5, 6):
            col_extend(tx, ty, S, V)
        elif S == 7:
            pipe(tx, ty, V)
        elif S == 1:
            ln = max(1, V + 1)
            for dx in range(ln):
                put(tx + dx, ty, 'X')
        elif S == 4:
            ln = max(1, V + 1)
            for dx in range(ln):
                put(tx + dx, ty, 'o')
        i += 2

    mw = max(len(rows[0]), max_x + 32)
    for r in rows:
        while len(r) < mw:
            r.append('.')
    out = [''.join(r) for r in rows]
    return out, timer


def _level_has_flagpole(rows: list[str]) -> bool:
    return any('T' in row for row in rows) and any('F' in row for row in rows)


def _find_brick_tower_x(rows: list[str]) -> int | None:
    """Rightmost tall brick column — SMBDIS emits this instead of a flagpole."""
    h = len(rows)
    w = len(rows[0])
    best_x = None
    best = 0
    for x in range(w - 1, max(w // 4, 0), -1):
        ys = [y for y in range(h - 1) if rows[y][x] == 'B']
        if len(ys) >= 6 and len(ys) > best:
            best = len(ys)
            best_x = x
    return best_x


def _flagpole_target_x(rows: list[str]) -> int:
    w = len(rows[0])
    h = len(rows)
    # End-of-level flagpole is always the rightmost F / T column (not mid-level decode junk)
    for x in range(w - 1, max(w // 4, 0), -1):
        if any(rows[y][x] == 'F' for y in range(h)):
            return x
    for x in range(w - 1, max(w // 4, 0), -1):
        if sum(1 for y in range(h - 2) if rows[y][x] == 'T') >= 6:
            return x
    tx = _find_brick_tower_x(rows)
    if tx is not None:
        return tx
    for scan in range(w - 8, w):
        if scan < w and rows[12][scan] in 'X':
            return scan
    return max(16, w - 18)


def _scrub_flagpole_runway(grid: list[list[str]], fx: int) -> None:
    """Remove end-of-level ground stacks / block stairs (look like brick towers)."""
    h = len(grid)
    w = len(grid[0])
    junk = set('XBSC?![]{}=U#')
    x0 = max(0, fx - 32)
    for cx in range(x0, w):
        if cx == fx:
            continue
        for y in range(h - 2):
            if grid[y][cx] in junk:
                grid[y][cx] = '.'
    for cx in range(x0, w):
        grid[12][cx] = 'X'
        grid[13][cx] = 'X'


def _install_smb1_flagpole(rows: list[str], x: int | None = None) -> list[str]:
    """SMB1 finish: flat runway + single flagpole (no block/ground towers)."""
    h = len(rows)
    w = len(rows[0])
    x = _flagpole_target_x(rows) if x is None else x
    grid = [list(r) for r in rows]
    # Drop stray flagpole tiles decoded mid-level (keep only the finish-line pole)
    for cx in range(w):
        if cx == x:
            continue
        for y in range(h - 1):
            if grid[y][cx] in ('T', 'F'):
                grid[y][cx] = '.'
    _scrub_flagpole_runway(grid, x)
    for y in range(h - 1):
        grid[y][x] = '.'
    grid[12][x] = 'F'         # flag base (collision / grab anchor)
    grid[13][x] = 'X'
    # Pole shaft is drawn as a composite sprite — keep rows 1-11 empty (no fake brick towers)
    for y in range(1, 12):
        grid[y][x] = '.'
    return [''.join(r) for r in grid]


def _ensure_smb1_flagpole(rows: list[str]) -> list[str]:
    """Always normalize end-of-level geometry to a single SMB1 flagpole."""
    return _install_smb1_flagpole(rows, _flagpole_target_x(rows))


def _fallback_minimal_level(end: str) -> list[str]:
    w = 64
    rows = [['.' for _ in range(w)] for _ in range(14)]
    for x in range(w):
        rows[12][x] = 'X'
        rows[13][x] = 'X'
    rows[7][w - 12] = 'T'
    for yy in range(8, 12):
        rows[yy][w - 12] = 'T'
    rows[12][w - 12] = 'F'
    if end == "axe":
        rows[12][w - 6] = 'A'
        for x in range(w - 14, w - 6):
            rows[11][x] = '='
            rows[12][x] = 'L'
            rows[13][x] = 'L'
    elif end == "bowser":
        rows[12][w - 6] = 'A'
    return [''.join(r) for r in rows]


def _init_levels_from_smbdis() -> None:
    global LEVELS
    blobs = _load_smbdis_object_blobs()
    LEVELS = {}
    for key, lab in SMBDIS_LEVEL_OBJECT_LABEL.items():
        meta = SMB1_STAGE_META[key]
        blob = blobs.get(lab)
        decoded = _decode_smb1_area_object_stream(blob) if blob else None
        if decoded:
            data, tdec = decoded
            time = int(tdec) if tdec else int(meta["default_time"])
        else:
            data = _fallback_minimal_level(str(meta["end"]))
            time = int(meta["default_time"])
        if meta["end"] == "flag":
            data = _ensure_smb1_flagpole(data)
            fp_x = _flagpole_target_x(data)
        else:
            fp_x = None
        LEVELS[key] = dict(
            theme=str(meta["theme"]),
            time=time,
            music=str(meta["music"]),
            end=str(meta["end"]),
            data=data,
            flagpole_x=fp_x,
            smbdis_object=blob,
            smbdis_label=lab,
        )


# ============================================================
#  LEVEL DATA — all 32 SMB1 stages from disassembly object streams
#  Row 0 = top; row 13 = ground reference (see Level class).
# ============================================================

_init_levels_from_smbdis()

# ============================================================
#  AUDIO  — Ricoh 2A03 (Famicom / NES APU) style
#  Pulse: 12.5% / 25% / 50% / 75% duty; phase accumulator; 4-bit-ish quantize
#  Noise: 15-bit LFSR (APU Noise channel), not white noise
# ============================================================
SR = 44100
_sound_cache = {}

# 2A03 pulse duty cycles (fraction of period high)
DUTY_12 = 0.125
DUTY_25 = 0.25
DUTY_50 = 0.5
DUTY_75 = 0.75


def _apu_pulse(phase, duty):
    """phase in [0,1). Return -1..+1 square with NES-compatible duty."""
    d = duty
    if d >= 0.75:
        d = DUTY_75
    elif d >= 0.5:
        d = DUTY_50
    elif d >= 0.25:
        d = DUTY_25
    else:
        d = DUTY_12
    return 1.0 if (phase % 1.0) < d else -1.0


def _apu_quantize(x, steps=16):
    """Coarse output like APU master (~4-bit effective per channel feel)."""
    t = max(-1.0, min(1.0, x))
    q = round(t * (steps - 1)) / (steps - 1)
    return int(q * 32767 * 0.85)


def _make_sfx(freq_list, duration, vol=0.25, duty=DUTY_12):
    """freq_list: list of (start_t, freq) in seconds and Hz. duty = NES pulse duty."""
    n = int(SR * duration)
    buf = array('h', [0] * n)
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = freq_list[0][1]
        for st, fr in freq_list:
            if t >= st:
                f = fr
        phase += f / SR
        phase %= 1.0
        v = _apu_pulse(phase, duty) * vol
        env = 1.0
        if t < 0.01:
            env = t / 0.01
        if t > duration - 0.05:
            env = max(0.0, (duration - t) / 0.05)
        buf[i] = _apu_quantize(v * env)
    return buf


def _make_noise(duration, vol=0.2, freq=8000, short_mode=False):
    """NES APU Noise: 15-bit shift register, XOR feedback (long/short mode)."""
    n = int(SR * duration)
    buf = array('h', [0] * n)
    reg = 1  # non-zero seed (hardware avoids all-zero)
    timer_period = max(2, int(SR / freq))
    timer = 0
    for i in range(n):
        timer -= 1
        if timer <= 0:
            timer = timer_period
            b0 = reg & 1
            tap = (reg >> (6 if short_mode else 1)) & 1
            fb = b0 ^ tap
            reg >>= 1
            if fb:
                reg |= 0x4000
            reg &= 0x7FFF
        # Mixer uses inverted bit 0 (classic NES timbre)
        bit = reg & 1
        v = vol if bit == 0 else -vol
        t = i / SR
        env = 1.0
        if t < 0.005:
            env = t / 0.005
        if t > duration - 0.05:
            env = max(0.0, (duration - t) / 0.05)
        buf[i] = _apu_quantize(v * env)
    return buf

def _to_sound(buf):
    # convert mono int16 to stereo for pygame
    out = array('h', [0] * (len(buf)*2))
    for i, v in enumerate(buf):
        out[i*2] = v
        out[i*2+1] = v
    return pygame.mixer.Sound(buffer=bytes(out))

def _build_sounds():
    s = {}
    s['jump']     = _to_sound(_make_sfx([(0.0,520),(0.05,720),(0.10,900)], 0.18, 0.22, DUTY_12))
    s['bigjump']  = _to_sound(_make_sfx([(0.0,420),(0.05,640),(0.12,860),(0.18,1020)], 0.22, 0.22, DUTY_12))
    s['coin']     = _to_sound(_make_sfx([(0.0,988),(0.04,1318)], 0.18, 0.20, DUTY_50))
    s['stomp']    = _to_sound(_make_sfx([(0.0,180),(0.05,90)], 0.10, 0.24, DUTY_25))
    s['kick']     = _to_sound(_make_sfx([(0.0,260),(0.04,140),(0.08,80)], 0.13, 0.22, DUTY_12))
    s['bump']     = _to_sound(_make_sfx([(0.0,260),(0.05,160)], 0.10, 0.22, DUTY_25))
    s['break']    = _to_sound(_make_noise(0.15, 0.24, 8000, short_mode=True))
    s['powerup']  = _to_sound(_make_sfx([(0.0,523),(0.05,659),(0.10,784),(0.15,1047),(0.20,1318)], 0.30, 0.20, DUTY_25))
    s['powerget'] = _to_sound(_make_sfx([(0.0,659),(0.04,784),(0.08,988),(0.12,1318),(0.16,1568)], 0.30, 0.22, DUTY_50))
    s['1up']      = _to_sound(_make_sfx([(0.0,1318),(0.06,1568),(0.12,1976),(0.18,2637)], 0.32, 0.20, DUTY_50))
    s['die']      = _to_sound(_make_sfx([(0.0,196),(0.10,233),(0.20,165),(0.30,98)], 0.80, 0.22, DUTY_12))
    s['fireball'] = _to_sound(_make_sfx([(0.0,880),(0.04,440)], 0.10, 0.18, DUTY_25))
    s['pause']    = _to_sound(_make_sfx([(0.0,988)], 0.08, 0.18, DUTY_50))
    s['warp']     = _to_sound(_make_sfx([(0.0,180),(0.10,140),(0.20,100),(0.30,80)], 0.45, 0.18, DUTY_12))
    s['clear']    = _to_sound(_make_sfx([(0.0,523),(0.10,659),(0.20,784),(0.30,1047)], 0.50, 0.20, DUTY_50))
    s['flag']     = _to_sound(_make_sfx([(0.0,659),(0.06,523),(0.12,440),(0.20,587),(0.28,523)], 0.50, 0.22, DUTY_25))
    s['fireworks']= _to_sound(_make_noise(0.20, 0.22, 5000, short_mode=True))
    s['bowserfall']= _to_sound(_make_sfx([(0.0,200),(0.15,120),(0.30,80),(0.5,50)], 0.7, 0.20, DUTY_12))
    return s

def play(name):
    """Play SFX on channels 1+ so channel 0 BGM loop is never stolen."""
    if not snd_enabled:
        return
    snd = SFX.get(name)
    if not snd:
        return
    nch = pygame.mixer.get_num_channels()
    for cid in range(1, nch):
        ch = pygame.mixer.Channel(cid)
        if not ch.get_busy():
            ch.play(snd)
            return
    pygame.mixer.Channel(1).play(snd)


# ============================================================
#  KOJI KONDO SMB1 MUSIC — multi-channel 2A03 chiptune
#  Source: SMB1 score / MuseScore community transcription (chords)
#  Channels: Pulse 1 (lead 12.5%), Pulse 2 (harmony 25%), Triangle (bass)
#  Famicom-faithful at 60 FPS (NES APU clocking emulated by sample rate)
# ============================================================

# Note frequencies — extended down to bass octaves for triangle channel
NOTE_FREQS = {
    '-': 0.0, 'r': 0.0,
    # Bass octave 1–2
    'A1':55.00,'Bb1':58.27,'B1':61.74,
    'C2':65.41,'C#2':69.30,'D2':73.42,'Eb2':77.78,'E2':82.41,'F2':87.31,
    'F#2':92.50,'G2':98.00,'G#2':103.83,'A2':110.00,'Bb2':116.54,'B2':123.47,
    # Octave 3
    'C3':130.81,'C#3':138.59,'D3':146.83,'Eb3':155.56,'E3':164.81,'F3':174.61,
    'F#3':185.00,'G3':196.00,'G#3':207.65,'A3':220.00,'Bb3':233.08,'B3':246.94,
    # Octave 4
    'C4':261.63,'C#4':277.18,'D4':293.66,'Eb4':311.13,'E4':329.63,'F4':349.23,
    'F#4':369.99,'G4':392.00,'G#4':415.30,'A4':440.00,'Bb4':466.16,'B4':493.88,
    # Octave 5
    'C5':523.25,'C#5':554.37,'D5':587.33,'Eb5':622.25,'E5':659.25,'F5':698.46,
    'F#5':739.99,'G5':783.99,'G#5':830.61,'A5':880.00,'Bb5':932.33,'B5':987.77,
    # Octave 6
    'C6':1046.50,'D6':1174.66,'E6':1318.51,'F6':1396.91,'G6':1567.98,'A6':1760.00,
}


def _apu_triangle(phase: float) -> float:
    """4-bit-stepped triangle wave (NES APU triangle channel feel)."""
    p = phase % 1.0
    v = (p * 4.0) - 1.0 if p < 0.5 else 3.0 - (p * 4.0)
    return round(v * 7.5) / 7.5


def _render_track(notes, tempo, sr, voice='pulse', duty=DUTY_12, vol=0.30):
    """Render a single voice (pulse or triangle) to mono int16 samples.

    `notes`: list of (pitch_str, length_in_16ths). `tempo`: quarter-note BPM.
    """
    sixteenth_sec = (60.0 / tempo) / 4.0
    out = array('h')
    phase = 0.0
    for note, length in notes:
        freq = NOTE_FREQS.get(note, 0.0)
        dur = max(1, int(sr * sixteenth_sec * length))
        if freq <= 0.0:
            out.extend([0] * dur)
            phase = 0.0
            continue
        inc = freq / sr
        attack = min(int(sr * 0.003), max(1, dur // 8))
        release = min(int(sr * 0.020), max(1, dur // 4))
        for i in range(dur):
            phase += inc
            if phase >= 1.0:
                phase -= 1.0
            if voice == 'triangle':
                s = _apu_triangle(phase) * vol
            else:
                s = _apu_pulse(phase, duty) * vol
            env = 1.0
            if i < attack:
                env = i / attack
            elif i > dur - release:
                env = max(0.0, (dur - i) / release)
            v = int(max(-32767, min(32767, s * 32767 * env)))
            out.append(v)
    return out


def _pad_track(track: array, length: int) -> array:
    if len(track) >= length:
        return track
    return array('h', list(track) + [0] * (length - len(track)))


def _loop_seam_fix(mix: array) -> array:
    """Crossfade loop boundary so pygame channel loops do not click."""
    n = len(mix)
    fade = min(int(SR * 0.006), max(2, n // 32))
    if fade < 2 or n < fade * 2:
        return mix
    for i in range(fade):
        w = i / fade
        a, b = mix[i], mix[n - fade + i]
        mix[i] = int(a * w + b * (1.0 - w))
        mix[n - fade + i] = int(b * w + a * (1.0 - w))
    return mix


def _mix_to_sound(*tracks):
    """Sum-mix int16 mono tracks; output a seamless-loop stereo pygame.Sound."""
    n = max((len(t) for t in tracks), default=0)
    if n == 0:
        return None
    mix = array('h', [0] * n)
    for t in tracks:
        t = _pad_track(t, n)
        for i in range(n):
            v = mix[i] + t[i]
            if v > 32767:
                v = 32767
            elif v < -32768:
                v = -32768
            mix[i] = v
    mix = _loop_seam_fix(mix)
    stereo = array('h', [0] * (n * 2))
    for i, v in enumerate(mix):
        stereo[i * 2] = v
        stereo[i * 2 + 1] = v
    return pygame.mixer.Sound(buffer=stereo.tobytes())


# ------------------------------------------------------------
# SMB1 OVERWORLD THEME — Koji Kondo (MuseScore community SMB1 score)
# Tempo ≈ 200 BPM eighth-pulse (≈ 100 BPM quarter); lengths in 16th notes
# Chord progression: | Am | Am | F  Dm | G  Em | F  Dm | G G G G |
# ------------------------------------------------------------
TEMPO_OVER = 200

# Pulse 1 — Lead melody (12.5% duty)
OVER_LEAD = [
    # Bar 1 — Am
    ('E5',2),('E5',2),('-',2),('E5',2),('-',2),('C5',2),('E5',2),('-',2),
    # Bar 2 — Am
    ('G5',2),('-',6),('G4',2),('-',6),
    # Bar 3 — F → Dm
    ('C5',2),('-',4),('G4',2),('-',4),('E4',2),('-',4),
    # Bar 4 — G → Em
    ('A4',2),('-',2),('B4',2),('-',2),('Bb4',2),('A4',2),('-',2),
    # Bar 5 — F → Dm
    ('G4',2),('E5',2),('-',2),('G5',2),('A5',2),('-',2),('F5',2),('G5',2),
    # Bar 6 — G7 → C
    ('-',2),('E5',2),('-',2),('C5',2),('D5',2),('B4',2),('-',4),
]

# Pulse 2 — Harmony (25% duty), parallel thirds / chord tones
OVER_HARM = [
    # Bar 1 — Am (C E A)
    ('C5',2),('C5',2),('-',2),('C5',2),('-',2),('A4',2),('C5',2),('-',2),
    # Bar 2
    ('E5',2),('-',6),('E4',2),('-',6),
    # Bar 3 — F (F A C) → Dm (D F A)
    ('A4',2),('-',4),('E4',2),('-',4),('C4',2),('-',4),
    # Bar 4 — G (G B D) → Em (E G B)
    ('F4',2),('-',2),('G4',2),('-',2),('F#4',2),('F4',2),('-',2),
    # Bar 5 — F → Dm
    ('E4',2),('C5',2),('-',2),('E5',2),('F5',2),('-',2),('D5',2),('E5',2),
    # Bar 6 — G7 → C
    ('-',2),('C5',2),('-',2),('A4',2),('B4',2),('G4',2),('-',4),
]

# Triangle — Walking bass (6 bars, 16 sixteenths each — sync with lead/harm)
OVER_BASS = [
    # Bar 1 — Am pedal
    ('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),
    # Bar 2 — Am pedal
    ('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),('A2',2),
    # Bar 3 — F | Dm
    ('F2',4),('F2',4),('D2',4),('D2',4),
    # Bar 4 — G | Em
    ('G2',4),('G2',4),('E2',4),('E2',4),
    # Bar 5 — F | Dm
    ('F2',4),('F2',4),('D2',4),('D2',4),
    # Bar 6 — G7 → C
    ('G2',4),('G2',4),('C3',4),('C3',4),
]

# ------------------------------------------------------------
# SMB1 UNDERGROUND THEME — Koji Kondo
# Sparse pulse pair; classic descending semitone "C-A-Bb" figure
# ------------------------------------------------------------
TEMPO_UNDER = 200

UNDER_LEAD = [
    ('C5',1),('-',1),('C4',1),('-',1),('-',4),
    ('A4',1),('-',1),('A3',1),('-',1),('-',4),
    ('Bb4',1),('-',1),('Bb3',1),('-',1),('-',12),
    ('-',16),
    ('C5',1),('-',1),('C4',1),('-',1),('-',4),
    ('A4',1),('-',1),('A3',1),('-',1),('-',4),
    ('Bb4',1),('-',1),('Bb3',1),('-',1),('-',12),
    ('-',16),
]

UNDER_HARM = [
    ('-',8),('-',8),('-',16),('-',16),
    ('-',8),('-',8),('-',16),('-',16),
]

UNDER_BASS = [
    # Sparse low triangle pulses on the descending C-A-Bb figure
    ('C2',1),('-',7),('A1',1),('-',7),
    ('Bb2',1),('-',7),('-',8),
    ('-',16),
    ('C2',1),('-',7),('A1',1),('-',7),
    ('Bb2',1),('-',7),('-',8),
    ('-',16),
]

# ------------------------------------------------------------
# SMB1 CASTLE THEME — Koji Kondo (Bowser's lair, ostinato)
# Chromatic ostinato in pulses; pedal triangle bass
# ------------------------------------------------------------
TEMPO_CASTLE = 200

CASTLE_LEAD = [
    ('G4',1),('-',1),('G4',1),('-',1),('G4',1),('-',1),('G4',1),('-',1),
    ('C5',1),('-',1),('C5',1),('-',1),('C5',1),('-',1),('C5',1),('-',1),
    ('D5',1),('-',1),('D5',1),('-',1),('D5',1),('-',1),('D5',1),('-',1),
    ('Eb5',1),('-',1),('Eb5',1),('-',1),('D5',1),('-',1),('D5',1),('-',1),
]

CASTLE_HARM = [
    ('Eb4',1),('-',1),('Eb4',1),('-',1),('Eb4',1),('-',1),('Eb4',1),('-',1),
    ('G4',1),('-',1),('G4',1),('-',1),('G4',1),('-',1),('G4',1),('-',1),
    ('Bb4',1),('-',1),('Bb4',1),('-',1),('Bb4',1),('-',1),('Bb4',1),('-',1),
    ('B4',1),('-',1),('B4',1),('-',1),('Bb4',1),('-',1),('Bb4',1),('-',1),
]

CASTLE_BASS = [
    ('C2',2),('C2',2),('C2',2),('C2',2),
    ('F2',2),('F2',2),('F2',2),('F2',2),
    ('G2',2),('G2',2),('G2',2),('G2',2),
    ('A2',2),('A2',2),('A2',2),('A2',2),
]


def _build_music_bank(sr=None):
    """Compile the SMB1 music bank into looping pygame.Sound objects."""
    if sr is None:
        sr = SR
    bank = {}

    over_p1 = _render_track(OVER_LEAD, TEMPO_OVER, sr, 'pulse', DUTY_12, 0.32)
    over_p2 = _render_track(OVER_HARM, TEMPO_OVER, sr, 'pulse', DUTY_25, 0.20)
    over_tr = _render_track(OVER_BASS, TEMPO_OVER, sr, 'triangle', vol=0.40)
    bank['over'] = _mix_to_sound(over_p1, over_p2, over_tr)

    under_p1 = _render_track(UNDER_LEAD, TEMPO_UNDER, sr, 'pulse', DUTY_25, 0.34)
    under_p2 = _render_track(UNDER_HARM, TEMPO_UNDER, sr, 'pulse', DUTY_50, 0.20)
    under_tr = _render_track(UNDER_BASS, TEMPO_UNDER, sr, 'triangle', vol=0.30)
    bank['under'] = _mix_to_sound(under_p1, under_p2, under_tr)

    cast_p1 = _render_track(CASTLE_LEAD, TEMPO_CASTLE, sr, 'pulse', DUTY_12, 0.30)
    cast_p2 = _render_track(CASTLE_HARM, TEMPO_CASTLE, sr, 'pulse', DUTY_25, 0.22)
    cast_tr = _render_track(CASTLE_BASS, TEMPO_CASTLE, sr, 'triangle', vol=0.38)
    bank['castle'] = _mix_to_sound(cast_p1, cast_p2, cast_tr)

    return bank


# Prebuild music (regenerated after pygame.mixer.init in main())
MUSIC = {}
current_music = None
MUSIC_CH: pygame.mixer.Channel | None = None  # channel 0 = BGM only (FILES=OFF loops)


def _init_music_channel():
    """Reserve channel 0 for seamless BGM; SFX use channels 1..N-1."""
    global MUSIC_CH
    pygame.mixer.set_num_channels(16)
    MUSIC_CH = pygame.mixer.Channel(0)


def start_music(kind, *, force=False):
    global current_music
    if not snd_enabled or MUSIC_CH is None:
        return
    if not force and current_music == kind and MUSIC_CH.get_busy():
        return
    stop_music()
    snd = MUSIC.get(kind)
    if snd:
        MUSIC_CH.play(snd, loops=-1)
        current_music = kind


def stop_music():
    global current_music
    if not snd_enabled:
        return
    if MUSIC_CH is not None:
        MUSIC_CH.stop()
    current_music = None


def ensure_music_loop():
    """Restart BGM if the mixer dropped channel 0 (keeps SMB1 loops continuous)."""
    if not snd_enabled or MUSIC_CH is None or not current_music:
        return
    if not MUSIC_CH.get_busy():
        snd = MUSIC.get(current_music)
        if snd:
            MUSIC_CH.play(snd, loops=-1)

# ============================================================
#  SPRITES  (Mario Maker HD procedural pixel art, FILES=OFF)
# ============================================================

def px_surf(grid, palette, hd=SPRITE_HD):
    """ASCII grid → surface; each cell is hd×hd pixels (Maker-style crisp art)."""
    h = len(grid)
    w = len(grid[0])
    surf = pygame.Surface((w * hd, h * hd), pygame.SRCALPHA)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in ('.', ' '):
                continue
            c = palette.get(ch)
            if c is None:
                continue
            pygame.draw.rect(surf, c, (x * hd, y * hd, hd, hd))
    return surf

def fit_sprite(surf, w, h):
    """Nearest-neighbor fit of HD art into logical NES sprite size."""
    sw, sh = surf.get_width(), surf.get_height()
    if sw == w and sh == h:
        return surf
    return pygame.transform.scale(surf, (w, h))

def fit_tile(surf):
    return fit_sprite(surf, TILE, TILE)

def _flip_h(grid):
    return [row[::-1] for row in grid]

# --- Mario Maker SMB1 palette (black overalls, clean outlines) ---
MM_RED = (228, 0, 88)
MM_SKIN = (248, 208, 192)
MM_SHOE = (104, 64, 0)
MM_EARTH = (252, 152, 56)
MM_EARTH_D = (204, 75, 0)
MM_PIPE_C = (0, 168, 0)
MM_PIPE_HI = (140, 252, 140)
MM_BRICK_C = (216, 92, 8)
MM_BRICK_D = (124, 44, 0)
MM_Q_C = (252, 204, 0)
MM_Q_D = (228, 164, 0)

def _mm_tile_pal(theme):
    if theme == "under":
        return {
            'K': P['black'], 'E': (104, 84, 36), 'D': (60, 48, 16),
            'G': MM_PIPE_C, 'W': P['white'], 'Y': MM_Q_C, 'O': MM_Q_D,
            'B': MM_BRICK_C, 'L': MM_BRICK_D,
        }
    if theme == "castle":
        return {
            'K': P['black'], 'E': P['gray'], 'D': P['darkgray'],
            'G': P['darkgreen'], 'W': P['ltgray'], 'Y': P['ltgray'], 'O': P['gray'],
            'B': P['gray'], 'L': P['darkgray'],
        }
    return {
        'K': P['black'], 'E': MM_EARTH, 'D': MM_EARTH_D,
        'G': MM_PIPE_C, 'W': P['white'], 'Y': MM_Q_C, 'O': MM_Q_D,
        'B': MM_BRICK_C, 'L': MM_BRICK_D,
    }

MARIO_PAL = {
    'R': MM_RED, 'K': P['black'], 'S': MM_SKIN, 'B': P['black'],
    'D': MM_SHOE, 'Y': (248, 216, 0), 'W': P['white'],
}
MARIO_FIRE_STAND_PAL = {
    'R': P['white'], 'K': P['darkred'], 'S': MM_SKIN, 'B': MM_RED,
    'D': P['darkred'], 'Y': P['white'], 'W': P['white'],
}

# --- Mario Maker SMB1 character sprites (16×16 small, 16×32 big) ---
MARIO_SMALL_STAND = [
    "....RRRRR.......",
    "...RRRRRRRRR....",
    "...KKKSSSKS.....",
    "..KKSKSSSKS.....",
    "..KKSKKSSSKS....",
    "..KKSSSKSKK.....",
    "....SSSSSS......",
    "...RRBRRR.......",
    "..RRRBRRBRR.....",
    ".RRRRBBBBBRR....",
    ".SSSBBBBBBSSS...",
    "..SSBBBBBBSS....",
    "...BBBBBBBB.....",
    "....BBB..BBB....",
    "....DD....DD....",
    "....DD....DD....",
]
MARIO_SMALL_WALK = [
    "....RRRRR.......",
    "...RRRRRRRRR....",
    "...KKKSSSKS.....",
    "..KKSKSSSKS.....",
    "..KKSKKSSSKS....",
    "..KKSSSKSKK.....",
    "....SSSSSS......",
    "..RRRRBRRRRR....",
    ".RRRRRBRRBRRRRR.",
    ".SSRRRBBBBRRSSS.",
    "..SSSBBBBBBSS...",
    "...BBBBBBBBB....",
    "..BBB.....BBB...",
    ".DDD........DDD.",
    "DDD..........DDD",
    "DDD..........DDD",
]
MARIO_SMALL_JUMP = [
    "....RRRRR.......",
    "...RRRRRRRRR....",
    "...KKKSSSKS.....",
    "..KKSKSSSKS.....",
    "..KKSKKSSSKS....",
    "..KKSSSKSKK.....",
    "...RSSSSSSSSR...",
    "..RRRBRRRRBRRR..",
    ".RRRRBBRRBBRRRR.",
    ".RSSSBBBBBBSSS.",
    "..SSSBBBBBBSS...",
    "...BBBBBBBB.....",
    "..BBB....BBB....",
    "..DDD...........",
    "..DDD....DDD....",
    ".........DDD....",
]
MARIO_BIG_STAND = [
    "....RRRRR.......",
    "...RRRRRRRRR....",
    "...KKKSSSKS.....",
    "..KKSKSSSKS.....",
    "..KKSKKSSSKS....",
    "..KKSSSKSKK.....",
    "....SSSSSS......",
    "....RRBRRR......",
    "...RRRBRRRBRR...",
    "..RRRRBBBBRRRR..",
    "..RRRBBBBBBRRR..",
    "..RRBBBBBBBBRR..",
    "..RRBB....BBRR..",
    "....BB....BB....",
    "....BB....BB....",
    "...BBB....BBB...",
    "...BBB....BBB...",
    "...DDD....DDD...",
    "...DDD....DDD...",
    "..DDDD....DDDD..",
    "..DDDD....DDDD..",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]

# --- Enemies (Mario Maker SMB1 style) ---
GOOMBA_A = [
    "....DDDDDDDD....",
    "...DLLLLLLLLD...",
    "..DDLLLLLLLLDD..",
    "..DDLLLLLLLLDD..",
    ".DDLLLLLLLLLLDD.",
    ".DDLKWLLLLWKLDD.",
    ".DDKWBBLLBBWKDD.",
    ".DDKWBBLLBBWKDD.",
    ".DDLKWLLLLWKLDD.",
    ".DDLLLLLLLLLLDD.",
    "..LLLLLLLLLLLL..",
    "...LDDDDDDDDL...",
    "..LL........LL..",
    "..LL........LL..",
    ".LLL........LLL.",
    "DDD..........DDD",
]
GOOMBA_B = [
    "....DDDDDDDD....",
    "...DLLLLLLLLD...",
    "..DDLLLLLLLLDD..",
    "..DDLLLLLLLLDD..",
    ".DDLLLLLLLLLLDD.",
    ".DDLKWLLLLWKLDD.",
    ".DDKWBBLLBBWKDD.",
    ".DDKWBBLLBBWKDD.",
    ".DDLKWLLLLWKLDD.",
    ".DDLLLLLLLLLLDD.",
    "..LLLLLLLLLLLL..",
    "...LDDDDDDDDL...",
    "...LL......LL...",
    "..LLL......LLL..",
    "DDDL........LDDD",
    "................",
]
GOOMBA_DEAD = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "....DDDDDDDD....",
    "...DLLLLLLLLD...",
    "..DDLKWLLWKLDD..",
    "..DDKWBBLLWKDD..",
    "..DDLKWLLWKLDD..",
    "..DDLLLLLLLLDD..",
    "...LDDDDDDDDL...",
    "..DD........DD..",
    "................",
    "................",
    "................",
]
GOOMBA_PAL = {'D': MM_SHOE, 'L': (255, 181, 107), 'K': P['black'], 'W': P['white'], 'B': P['black']}
GOOMBA_UND_PAL = {'D': P['darkblue'], 'L': P['blue'], 'K': P['black'], 'W': P['white'], 'B': P['black']}
GOOMBA_CASTLE_PAL = {'D': P['darkgray'], 'L': P['gray'], 'K': P['black'], 'W': P['white'], 'B': P['black']}

KOOPA_A = [
    "................",
    ".....BBBBBB.....",
    "....BWWWWWWB....",
    "...BWWBBBBWWB...",
    "...BWBWWWWBWB...",
    "...BWWWWWWWWB...",
    "...BBBBBBBBBB...",
    "..GGGGGGGGGGGG..",
    ".GGGGYYYYYYGGGG.",
    ".GGYYGGGGGGYYGG.",
    ".GGYGGYYYYGGYGG.",
    ".GGYGYGGGGYGYGG.",
    "..GGGGGGGGGGGG..",
    "...GG......GG...",
    "...YY......YY...",
    "..YYY......YYY..",
]
KOOPA_B = [
    "................",
    ".....BBBBBB.....",
    "....BWWWWWWB....",
    "...BWWBBBBWWB...",
    "...BWBWWWWBWB...",
    "...BWWWWWWWWB...",
    "...BBBBBBBBBB...",
    "..GGGGGGGGGGGG..",
    ".GGGGYYYYYYGGGG.",
    ".GGYYGGGGGGYYGG.",
    ".GGYGGYYYYGGYGG.",
    ".GGYGYGGGGYGYGG.",
    "..GGGGGGGGGGGG..",
    "....GG..GG......",
    "....YY..YY......",
    "...YYY..YYY.....",
]
KOOPA_SHELL = [
    "................",
    "................",
    "................",
    "....GGGGGGGG....",
    "...GGGGGGGGGG...",
    "..GGYYYYYYYYGG..",
    ".GGYGGGGGGGGYGG.",
    ".GYGYYYYYYYYGYG.",
    ".GYGYGGGGGGYGYG.",
    ".GYGYGYYYYGYGYG.",
    ".GYGYGGGGGGYGYG.",
    ".GYGYYYYYYYYGYG.",
    ".GGYGGGGGGGGYGG.",
    "..GGYYYYYYYYGG..",
    "...GGGGGGGGGG...",
    "....GGGGGGGG....",
]
KOOPA_GREEN_PAL = {'B':P['black'], 'W':P['white'], 'G':P['green'], 'Y':P['yellow']}
KOOPA_RED_PAL   = {'B':P['black'], 'W':P['white'], 'G':P['red'],   'Y':P['yellow']}

PIRANHA_A = [
    "....GGGGGGGG....",
    "...GGGGGGGGGG...",
    "..GGWGGGGGGWGG..",
    "..GWBGGGGGGBWG..",
    "..GGWGGGGGGWGG..",
    "..GGGGRRRRGGGG..",
    "..GGRRRRRRRRGG..",
    "..GRRWRRRRWRRG..",
    "..GRRWRRRRWRRG..",
    "..GGRRRRRRRRGG..",
    "...GGGRRRRGGG...",
    "....GGGGGGGG....",
    "....GG....GG....",
    "....GG....GG....",
    "................",
    "................",
]
PIRANHA_PAL = {'G':P['green'], 'R':P['red'], 'W':P['white'], 'B':P['black']}

HAMMER_BRO = [
    "....BBBBBBBB....",
    "...BGGGGGGGGB...",
    "...BGYYYYYYGB...",
    "..BGGGGGGGGGGB..",
    "..BGFFWWWWFFGB..",
    "..BGFBWWWWBFGB..",
    "..BGFFWWWWFFGB..",
    "..BGGGGFFGGGGB..",
    "...BGGGGGGGGB...",
    "..GGGFFFFFFGGG..",
    "..GGFFFFFFFFGG..",
    "..GGFFGGGGFFGG..",
    "..GGGGGGGGGGGG..",
    "....FF....FF....",
    "....FF....FF....",
    "...FFF....FFF...",
]
HAMMER_PAL = {'B':P['black'],'G':P['green'],'Y':P['yellow'],'F':P['flesh'],'W':P['white']}

# --- Power-ups ---
MUSHROOM = [
    "....RRRRRRRR....",
    "...RWWWWWWWWR...",
    "..RWWWRRRRWWWR..",
    "..RWRRRRRRRRWR..",
    ".RRRRWWRRRRWRRR.",
    ".RWWWWWRRWWWWRR.",
    ".RWWWWWWWWWWWRR.",
    ".RRRRRRRRRRRRRR.",
    "...WWWWFFWWWW...",
    "..WWWFFFFFFWWW..",
    "..WFFFFFFFFFFW..",
    "..WFFWFFFFWFFW..",
    "..WFFWFFFFWFFW..",
    "..WFFFFFFFFFFW..",
    "...WWFFFFFFWW...",
    "....WWWWWWWW....",
]
MUSHROOM_PAL = {'R':P['red'],'W':P['white'],'F':P['flesh']}

FLOWER_A = [
    "................",
    "....RRRRRR......",
    "...RYYYYYYR.....",
    "..RYRRRRRRYR....",
    "..RYRYYYYRYR....",
    "..RYRYBBYRYR....",
    "..RYRYYYYRYR....",
    "..RYRRRRRRYR....",
    "...RYYYYYYR.....",
    "....RRRRRR......",
    ".....GGGG.......",
    "....GGGGGG......",
    "...GGGGGGGG.....",
    "....GGGGGG......",
    ".....GGGG.......",
    ".....GGGG.......",
]
FLOWER_PAL = {'R':P['red'],'Y':P['yellow'],'B':P['black'],'G':P['green']}

STAR_SPR = [
    "................",
    ".......YY.......",
    "......YYYY......",
    "......YYYY......",
    "..YYYYYWWYYYYY..",
    "...YYYYWWYYYY...",
    "....YYYWWYYY....",
    ".....YYWWYY.....",
    ".....YYWWYY.....",
    "....YYYWWYYY....",
    "...YYYY..YYYY...",
    "..YYYY....YYYY..",
    ".YYY........YYY.",
    "................",
    "................",
    "................",
]
STAR_PAL = {'Y':P['yellow'],'W':P['white']}

COIN_SPR = [
    "....YYYYYY......",
    "...YOOOOYY......",
    "..YOOOOOOYY.....",
    "..YOOYYOOYY.....",
    "..YOOYYOOYY.....",
    "..YOOYYOOYY.....",
    "..YOOYYOOYY.....",
    "..YOOYYOOYY.....",
    "..YOOOOOOYY.....",
    "...YOOOOYY......",
    "....YYYYYY......",
    "................",
    "................",
    "................",
    "................",
    "................",
]
COIN_PAL = {'Y':P['gold'],'O':P['yellow']}

FIREBALL = [
    "....OYYYO.......",
    "..OYYWWWYYO.....",
    ".OYWWYYYWWYO....",
    ".OYWYYYYYWYO....",
    ".OYWWYYYWWYO....",
    "..OYYWWWYYO.....",
    "....OYYYO.......",
    "................",
]
FIREBALL_PAL = {'O':P['red'],'Y':P['orange'],'W':P['yellow']}

# --- Mario Maker tile grids (16×16, HD baked via px_surf) ---
MM_GROUND = [
    "EEEEEEEEEEEEEEEE",
    "EEEEEEEEEEEEEEEE",
    "EEKKEEEEEEKKEEEE",
    "EEEEEEKKEEEEEEKK",
    "EEEEEEEEEEEEEEEE",
    "EKKEEEEEEEEEKKEE",
    "EEEEEEKKEEEEEEEE",
    "EEKKEEEEEEEEEEEE",
    "EEEEEEEEEEEEEEEE",
    "EEEEEEEEEEEEEEEE",
    "EEKKEEEEEEKKEEEE",
    "EEEEEEKKEEEEEEKK",
    "EEEEEEEEEEEEEEEE",
    "EKKEEEEEEEEEKKEE",
    "EEEEEEKKEEEEEEEE",
    "EEKKEEEEEEEEEEEE",
]
MM_BRICK = [
    "KKKKKKKKKKKKKKKK",
    "KLLLLLLKLKLLLLLK",
    "KLLLLLLKLKLLLLLK",
    "KKKKKKKKKKKKKKKK",
    "LLLLKLLLLLLLKLLL",
    "LLLLKLLLLLLLKLLL",
    "KKKKKKKKKKKKKKKK",
    "KLLLLLLKLKLLLLLK",
    "KLLLLLLKLKLLLLLK",
    "KKKKKKKKKKKKKKKK",
    "LLLLKLLLLLLLKLLL",
    "LLLLKLLLLLLLKLLL",
    "KKKKKKKKKKKKKKKK",
    "KLLLLLLKLKLLLLLK",
    "KLLLLLLKLKLLLLLK",
    "KKKKKKKKKKKKKKKK",
]
MM_Q_BLOCK = [
    "KKKKKKKKKKKKKKKK",
    "KYYYYYYYYYYYYYYK",
    "KYKKKKKKKKKKKKKY",
    "KYKKYYYKKKYYYKKK",
    "KYKKYYKKKKKYYKKK",
    "KYKKYYYKKKYYYKKK",
    "KYKKKKKYYYKKKKKK",
    "KYKKKKYYYKKKKKKK",
    "KYKKKKYYYKKKKKKK",
    "KYKKKKKKKKKKKKKK",
    "KYKKKKYYYKKKKKKK",
    "KYKKKKYYYKKKKKKK",
    "KYKKKKKKKKKKKKKK",
    "KYYYYYYYYYYYYYYK",
    "KKKKKKKKKKKKKKKK",
    "KKKKKKKKKKKKKKKK",
]
MM_Q_USED = [
    "KKKKKKKKKKKKKKKK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KEEEEEEEEEEEEEEK",
    "KKKKKKKKKKKKKKKK",
    "KKKKKKKKKKKKKKKK",
]
MM_PIPE_TL = [
    "GGGGGGGGGGGGGGGG", "GWWWWWWWWWWWWWWG", "GWKKKKKKKKKKKKKG", "GWKKGGGGGGGGGGKG",
    "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG",
    "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG",
    "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GGGGGGGGGGGGGGGG",
]
MM_PIPE_BL = [
    "GGGGGGGGGGGGGGGG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG",
    "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG",
    "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG",
    "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GWKKGGGGGGGGGGKG", "GGGGGGGGGGGGGGGG",
]

# --- Tiles (Mario Maker HD procedural) ---
def _ground_tile(theme):
    return fit_tile(px_surf(MM_GROUND, _mm_tile_pal(theme)))

def _brick_tile(theme):
    return fit_tile(px_surf(MM_BRICK, _mm_tile_pal(theme)))

def _question_tile(frame, used=False):
    pal = _mm_tile_pal("over")
    if used:
        return fit_tile(px_surf(MM_Q_USED, pal))
    pulse = (frame // 3) % 4
    tint = {0: MM_Q_C, 1: MM_Q_D, 2: (252, 228, 40), 3: MM_Q_D}
    pal = dict(pal)
    pal['Y'] = tint[pulse]
    return fit_tile(px_surf(MM_Q_BLOCK, pal))

def _pipe_tile(pos, theme):
    """pos: 'tl','tr','bl','br'"""
    pal = _mm_tile_pal(theme)
    if pos == 'tl':
        return fit_tile(px_surf(MM_PIPE_TL, pal))
    if pos == 'tr':
        return fit_tile(px_surf(_flip_h(MM_PIPE_TL), pal))
    if pos == 'bl':
        return fit_tile(px_surf(MM_PIPE_BL, pal))
    return fit_tile(px_surf(_flip_h(MM_PIPE_BL), pal))

def _flag_top():
    """SMB1 flag ball + cloth (pixel-accurate, not brick-like)."""
    grid = [
        "................",
        "......GG........",
        ".....GGGG.......",
        "..GGGGGGGGGG....",
        "..GGGGGGGGGG....",
        "....WWWW........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "................",
    ]
    pal = {
        'G': P['lgreen'], 'W': P['white'], 'K': P['black'],
        'R': P['red'], 'D': P['darkgreen'],
    }
    return fit_tile(px_surf(grid, pal))

def _flag_pole():
    grid = [
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
        "....WW..........",
    ]
    return fit_tile(px_surf(grid, {'W': P['white'], 'K': (160, 160, 160)}))

def _flag_base():
    grid = [
        "KKKKKKKKKKKKKKKK",
        "KLLLLLLLLLLLLLLK",
        "KLWWWWWWWWWWWWLK",
        "KLWWWWWWWWWWWWLK",
        "KLWWWWWWWWWWWWLK",
        "KLWWWWWWWWWWWWLK",
        "KLWWWWWWWWWWWWLK",
        "KLWWWWWWWWWWWWLK",
        "KLLLLLLLLLLLLLLK",
        "KKKKKKKKKKKKKKKK",
        "KKKKKKKKKKKKKKKK",
        "KKKKKKKKKKKKKKKK",
        "KKKKKKKKKKKKKKKK",
        "KKKKKKKKKKKKKKKK",
        "KKKKKKKKKKKKKKKK",
        "KKKKKKKKKKKKKKKK",
    ]
    return fit_tile(px_surf(grid, {'K': P['black'], 'L': P['gray'], 'W': P['white']}))

def _build_flagpole_composite():
    """Single SMB1 flagpole sprite (flag + pole + base) — never mistaken for bricks."""
    h = TILE * 12
    s = pygame.Surface((TILE, h), pygame.SRCALPHA)
    cx = 8
    pygame.draw.line(s, P['white'], (cx - 1, 18), (cx - 1, h - 18), 2)
    pygame.draw.line(s, (210, 210, 210), (cx, 18), (cx, h - 18), 1)
    pygame.draw.circle(s, P['lgreen'], (cx, 10), 5)
    pygame.draw.circle(s, P['green'], (cx, 10), 5, 1)
    pygame.draw.polygon(s, P['green'], [(cx + 1, 2), (cx + 13, 6), (cx + 12, 14), (cx + 1, 11)])
    pygame.draw.rect(s, P['gray'], (3, h - 15, 10, 13))
    pygame.draw.rect(s, P['black'], (3, h - 15, 10, 13), 1)
    pygame.draw.line(s, P['white'], (4, h - 14), (12, h - 14))
    return s

def _castle_tile():
    s = pygame.Surface((TILE, TILE))
    s.fill((200,200,200))
    pygame.draw.rect(s, P['darkgray'], s.get_rect(), 1)
    pygame.draw.line(s, P['darkgray'], (0, TILE//2), (TILE, TILE//2))
    pygame.draw.line(s, P['darkgray'], (TILE//2,0),(TILE//2,TILE//2))
    return s

def _solid_tile():
    s = pygame.Surface((TILE, TILE))
    s.fill((228,164,0))
    pygame.draw.rect(s, (124,84,0), s.get_rect(), 2)
    pygame.draw.line(s, (252,228,40), (2,2),(TILE-3,2))
    pygame.draw.line(s, (252,228,40), (2,2),(2,TILE-3))
    return s

def _bridge_tile():
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    s.fill((0,0,0,0))
    pygame.draw.rect(s, P['orange'], (0, 4, TILE, 6))
    pygame.draw.rect(s, P['darkbrown' if 'darkbrown' in P else 'brown'], (0,4,TILE,6), 1)
    return s

def _lava_tile(frame):
    s = pygame.Surface((TILE, TILE))
    base = P['orange']
    s.fill(base)
    for x in range(TILE):
        y = (TILE//2 + int(2*math.sin((x + frame*0.3) * 0.5)))
        pygame.draw.line(s, P['yellow'], (x, y), (x, TILE))
    return s

def _coin_collectible(frame):
    f = frame % 4
    pal = COIN_PAL.copy()
    if f == 1: pal['Y'] = (228,164,0)
    if f == 2: pal['Y'] = (172,124,0); pal['O'] = (124,84,0)
    if f == 3: pal['Y'] = (228,164,0)
    return fit_sprite(px_surf(COIN_SPR, pal), TILE, TILE)

# ============================================================
#  GLOBAL ASSETS
# ============================================================
ASSETS = {}

def _asset(grid, pal, w=None, h=None):
    if w is None:
        w = len(grid[0])
    if h is None:
        h = len(grid)
    return fit_sprite(px_surf(grid, pal), w, h)

def build_assets():
    A = {}
    # Mario Maker HD Mario
    A['mario_small_stand'] = _asset(MARIO_SMALL_STAND, MARIO_PAL, 16, 16)
    A['mario_small_walk']  = _asset(MARIO_SMALL_WALK,  MARIO_PAL, 16, 16)
    A['mario_small_jump']  = _asset(MARIO_SMALL_JUMP,  MARIO_PAL, 16, 16)
    A['mario_big_stand']   = _asset(MARIO_BIG_STAND,   MARIO_PAL, 16, 32)
    fp = dict(MARIO_FIRE_STAND_PAL)
    A['mario_fire_small_stand'] = _asset(MARIO_SMALL_STAND, fp, 16, 16)
    A['mario_fire_small_walk']  = _asset(MARIO_SMALL_WALK,  fp, 16, 16)
    A['mario_fire_small_jump']  = _asset(MARIO_SMALL_JUMP,  fp, 16, 16)
    A['mario_fire_big_stand']   = _asset(MARIO_BIG_STAND,   fp, 16, 32)
    # Enemies
    A['goomba_a'] = _asset(GOOMBA_A, GOOMBA_PAL, 16, 16)
    A['goomba_b'] = _asset(GOOMBA_B, GOOMBA_PAL, 16, 16)
    A['goomba_dead'] = _asset(GOOMBA_DEAD, GOOMBA_PAL, 16, 16)
    A['goomba_a_u'] = _asset(GOOMBA_A, GOOMBA_UND_PAL, 16, 16)
    A['goomba_b_u'] = _asset(GOOMBA_B, GOOMBA_UND_PAL, 16, 16)
    A['goomba_a_c'] = _asset(GOOMBA_A, GOOMBA_CASTLE_PAL, 16, 16)
    A['goomba_b_c'] = _asset(GOOMBA_B, GOOMBA_CASTLE_PAL, 16, 16)
    A['koopa_a']    = _asset(KOOPA_A, KOOPA_GREEN_PAL, 16, 16)
    A['koopa_b']    = _asset(KOOPA_B, KOOPA_GREEN_PAL, 16, 16)
    A['koopa_shell']= _asset(KOOPA_SHELL, KOOPA_GREEN_PAL, 16, 16)
    A['koopa_r_a']  = _asset(KOOPA_A, KOOPA_RED_PAL, 16, 16)
    A['koopa_r_b']  = _asset(KOOPA_B, KOOPA_RED_PAL, 16, 16)
    A['koopa_r_shell']= _asset(KOOPA_SHELL, KOOPA_RED_PAL, 16, 16)
    A['piranha']    = _asset(PIRANHA_A, PIRANHA_PAL, 16, 16)
    A['hammer_bro'] = _asset(HAMMER_BRO, HAMMER_PAL, 16, 16)
    A['mushroom']   = _asset(MUSHROOM, MUSHROOM_PAL, 16, 16)
    A['flower']     = _asset(FLOWER_A, FLOWER_PAL, 16, 16)
    A['star']       = _asset(STAR_SPR, STAR_PAL, 16, 16)
    A['fireball']   = _asset(FIREBALL, FIREBALL_PAL, 8, 8)
    A['oneup']      = _asset(MUSHROOM, {'R':P['green'],'W':P['white'],'F':P['flesh']}, 16, 16)
    # Tiles per theme
    for theme in ("over","under","castle"):
        A[f'ground_{theme}']   = _ground_tile(theme)
        A[f'brick_{theme}']    = _brick_tile(theme)
        A[f'pipe_tl_{theme}']  = _pipe_tile('tl', theme)
        A[f'pipe_tr_{theme}']  = _pipe_tile('tr', theme)
        A[f'pipe_bl_{theme}']  = _pipe_tile('bl', theme)
        A[f'pipe_br_{theme}']  = _pipe_tile('br', theme)
    A['question_used'] = _question_tile(0, used=True)
    A['flag_top']  = _flag_top()
    A['flag_pole'] = _flag_pole()
    A['flag_base'] = _flag_base()
    A['flagpole_composite'] = _build_flagpole_composite()
    A['castle_tile'] = _castle_tile()
    A['solid'] = _solid_tile()
    A['bridge'] = _bridge_tile()
    # Decorations
    bush = pygame.Surface((TILE*3, TILE), pygame.SRCALPHA)
    pygame.draw.circle(bush, P['green'], (8,12), 8)
    pygame.draw.circle(bush, P['green'], (24,8), 10)
    pygame.draw.circle(bush, P['green'], (40,12), 8)
    pygame.draw.rect(bush, P['green'], (4,12,42,4))
    A['bush'] = bush
    cloud = pygame.Surface((TILE*3, TILE*2), pygame.SRCALPHA)
    pygame.draw.circle(cloud, P['white'], (10, 24), 10)
    pygame.draw.circle(cloud, P['white'], (24, 18), 12)
    pygame.draw.circle(cloud, P['white'], (38, 24), 10)
    pygame.draw.rect(cloud, P['white'], (8, 22, 36, 8))
    A['cloud'] = cloud
    hill = pygame.Surface((TILE*5, TILE*2), pygame.SRCALPHA)
    pygame.draw.polygon(hill, P['green'], [(0,32),(40,4),(80,32)])
    pygame.draw.circle(hill, P['darkgreen'], (40, 16), 8)
    A['hill'] = hill
    # Axe
    axe = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    pygame.draw.rect(axe, P['brown'], (7, 0, 2, TILE))
    pygame.draw.polygon(axe, P['gray'], [(7,2),(2,4),(2,8),(7,6)])
    pygame.draw.polygon(axe, P['gray'], [(9,2),(14,4),(14,8),(9,6)])
    A['axe'] = axe
    # Princess
    princess = pygame.Surface((16,32), pygame.SRCALPHA)
    pygame.draw.rect(princess, P['pink'], (4, 12, 8, 14))
    pygame.draw.rect(princess, P['flesh'], (5, 4, 6, 8))
    pygame.draw.rect(princess, P['yellow'], (4, 0, 8, 5))
    pygame.draw.rect(princess, P['yellow'], (2, 2, 2, 2))
    pygame.draw.rect(princess, P['yellow'], (12, 2, 2, 2))
    pygame.draw.rect(princess, P['flesh'], (2, 14, 2, 6))
    pygame.draw.rect(princess, P['flesh'], (12, 14, 2, 6))
    pygame.draw.rect(princess, P['pink'], (4, 24, 3, 4))
    pygame.draw.rect(princess, P['pink'], (9, 24, 3, 4))
    A['princess'] = princess
    # Bowser
    bowser = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(bowser, P['green'], (4, 8, 24, 18))
    pygame.draw.rect(bowser, P['darkgreen'], (4, 8, 24, 18), 1)
    pygame.draw.rect(bowser, P['orange'], (8, 0, 16, 10))
    pygame.draw.rect(bowser, P['yellow'], (10, 2, 3, 3))
    pygame.draw.rect(bowser, P['yellow'], (19, 2, 3, 3))
    pygame.draw.rect(bowser, P['black'], (11, 3, 1, 1))
    pygame.draw.rect(bowser, P['black'], (20, 3, 1, 1))
    pygame.draw.rect(bowser, P['white'], (10, 6, 12, 3))
    pygame.draw.rect(bowser, P['red'], (12, 7, 8, 1))
    pygame.draw.rect(bowser, P['yellow'], (0, 14, 4, 12))
    pygame.draw.rect(bowser, P['yellow'], (28, 14, 4, 12))
    pygame.draw.rect(bowser, P['green'], (8, 26, 4, 6))
    pygame.draw.rect(bowser, P['green'], (20, 26, 4, 6))
    A['bowser'] = bowser
    return A

# ============================================================
#  GAME OBJECTS
# ============================================================

class Mario:
    SMALL_H = 16
    BIG_H = 32
    W = 14

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.power = 0   # 0 small, 1 big, 2 fire
        self.anim = 0
        self.walking = False
        self.running = False
        self.jump_hold = 0
        self.duck = False
        self.invul = 0
        self.star = 0
        self.dead = False
        self.dead_timer = 0
        self.entering_pipe = False
        self.pipe_phase = 0
        self.pipe_timer = 0
        self.pipe_dir = (0, 1)
        self.fireballs = []
        self.fire_cd = 0
        self.flag_grab = False
        self.flag_timer = 0
        self.level_done = False
        self.level_done_timer = 0
        self.victory_walk = False
        self.growth_anim = 0
        self.fire_anim = 0

    @property
    def h(self):
        if self.power == 0 or self.duck:
            return self.SMALL_H
        return self.BIG_H

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.h)

    def hurt(self, lvl):
        if self.invul > 0 or self.star > 0:
            return False
        if self.power > 0:
            self.power = 0
            self.invul = INVUL_FRAMES
            play('powerup')
            return False
        else:
            self.die()
            return True

    def die(self):
        if self.dead: return
        self.dead = True
        self.dead_timer = 0
        self.vy = -6.5
        self.vx = 0
        play('die')

    def update(self, keys, lvl, dt=1.0):
        if self.dead:
            self.dead_timer += 1
            if self.dead_timer > 30:
                self.y += self.vy
                self.vy += 0.30
            return
        if self.growth_anim > 0:
            self.growth_anim -= 1
            return
        if self.fire_anim > 0:
            self.fire_anim -= 1
            return
        if self.entering_pipe:
            self.pipe_timer += 1
            self.x += self.pipe_dir[0] * 0.5
            self.y += self.pipe_dir[1] * 0.5
            if self.pipe_timer > 60:
                self.entering_pipe = False
                self.pipe_timer = 0
            return
        if self.flag_grab:
            self.flag_timer += 1
            if not self.victory_walk:
                self.y += 2.0
                if self.y > lvl.flag_y_bottom - self.h:
                    self.y = lvl.flag_y_bottom - self.h
                    if self.flag_timer > 40:
                        self.victory_walk = True
                        self.facing = 1
                        self.x += 14
            else:
                self.x += 1.2
                self.anim += 0.25
                # walking animation
                if self.x > lvl.castle_x + 6:
                    self.level_done = True
                    self.level_done_timer += 1
            return

        left  = keys[pygame.K_LEFT]  or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        down  = keys[pygame.K_DOWN]  or keys[pygame.K_s]
        up    = keys[pygame.K_UP]    or keys[pygame.K_w]
        run   = keys[pygame.K_x]     or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        jump  = keys[pygame.K_z]     or keys[pygame.K_SPACE]

        # duck (only big)
        self.duck = bool(down and self.power > 0 and self.on_ground)

        # horizontal accel
        max_speed = RUN_MAX if run else WALK_MAX
        accel = RUN_ACCEL if run else WALK_ACCEL
        if not self.duck:
            if left and not right:
                self.vx -= accel
                if self.vx < -max_speed: self.vx = -max_speed
                self.facing = -1
                self.walking = True
            elif right and not left:
                self.vx += accel
                if self.vx > max_speed: self.vx = max_speed
                self.facing = 1
                self.walking = True
            else:
                # friction
                if self.vx > 0:
                    self.vx = max(0, self.vx - FRICTION)
                elif self.vx < 0:
                    self.vx = min(0, self.vx + FRICTION)
                self.walking = abs(self.vx) > 0.1
        else:
            if self.vx > 0:
                self.vx = max(0, self.vx - FRICTION*1.5)
            elif self.vx < 0:
                self.vx = min(0, self.vx + FRICTION*1.5)

        # jump
        if jump and self.on_ground:
            self.vy = JUMP_RUN if abs(self.vx) > 1.5 else JUMP_BASE
            self.jump_hold = JUMP_HOLD_MAX_FRAMES
            self.on_ground = False
            play('bigjump' if self.power > 0 else 'jump')
        elif jump and self.jump_hold > 0:
            self.vy += JUMP_HOLD_FORCE
            self.jump_hold -= 1
        else:
            self.jump_hold = 0

        # gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL: self.vy = MAX_FALL

        # fire
        if self.power == 2 and run and self.fire_cd <= 0 and len(self.fireballs) < 2:
            fb_x = self.x + (self.W if self.facing > 0 else -8)
            self.fireballs.append(Fireball(fb_x, self.y + 8, self.facing * 4.5))
            self.fire_cd = 18
            play('fireball')
        if self.fire_cd > 0: self.fire_cd -= 1

        # X movement + collide
        self.x += self.vx
        self._collide_x(lvl)
        # Y movement + collide
        self.y += self.vy
        self._collide_y(lvl)

        # Off-screen fall
        if self.y > NES_H + 50:
            self.die()

        # camera limit left
        if self.x < lvl.cam_x:
            self.x = lvl.cam_x
            self.vx = 0

        # anim
        if self.walking and self.on_ground:
            self.anim += abs(self.vx) * 0.18
        if self.invul > 0:
            self.invul -= 1
        if self.star > 0:
            self.star -= 1

    def _collide_x(self, lvl):
        r = self.rect
        sign = 1 if self.vx > 0 else -1
        if self.vx == 0: return
        col_range_y = range(r.top // TILE, (r.bottom-1) // TILE + 1)
        if sign > 0:
            tx = (r.right - 1) // TILE
        else:
            tx = r.left // TILE
        for ty in col_range_y:
            t = lvl.get_tile(tx, ty)
            if t in SOLID_CHARS:
                if sign > 0:
                    self.x = tx * TILE - self.W
                else:
                    self.x = (tx+1) * TILE
                self.vx = 0
                return

    def _collide_y(self, lvl):
        r = self.rect
        sign = 1 if self.vy > 0 else -1
        col_range_x = range(r.left // TILE, (r.right-1) // TILE + 1)
        if sign > 0:
            ty = (r.bottom-1) // TILE
        else:
            ty = r.top // TILE
        hit = False
        for tx in col_range_x:
            t = lvl.get_tile(tx, ty)
            if t in SOLID_CHARS:
                if sign > 0:
                    self.y = ty * TILE - self.h
                    self.vy = 0
                    self.on_ground = True
                else:
                    self.y = (ty+1) * TILE
                    self.vy = 0.5
                    self.jump_hold = 0
                    # hit block from below
                    lvl.hit_block(tx, ty, self)
                hit = True
                break
        if sign > 0 and not hit:
            self.on_ground = False

    def draw(self, surf, cam_x):
        gx = int(self.x - cam_x); gy = int(self.y)
        # invul flicker
        if self.invul > 0 and self.invul % 4 < 2:
            return
        # star flicker palette
        # pick sprite
        if self.dead:
            spr = ASSETS['mario_small_stand']
            surf.blit(spr, (gx, gy))
            return
        if self.power == 2:
            prefix = "mario_fire_"
        else:
            prefix = "mario_"
        if self.power == 0:
            if not self.on_ground:
                spr = ASSETS[prefix + 'small_jump']
            elif self.walking and (int(self.anim)%2 == 0):
                spr = ASSETS[prefix + 'small_walk']
            else:
                spr = ASSETS[prefix + 'small_stand']
        else:
            if self.duck:
                # squash big mario
                base = ASSETS[prefix + 'big_stand']
                spr = pygame.transform.scale(base, (16, 20))
                gy += 12
            elif not self.on_ground:
                # reuse small_jump for big jump (scaled)
                base = ASSETS[prefix + 'small_jump']
                spr = pygame.transform.scale(base, (16, 32))
            elif self.walking and (int(self.anim)%2 == 0):
                base = ASSETS[prefix + 'small_walk']
                spr = pygame.transform.scale(base, (16, 32))
            else:
                spr = ASSETS[prefix + 'big_stand']
        if self.facing < 0:
            spr = pygame.transform.flip(spr, True, False)
        # star tint (numpy-free: blit a colored copy over the sprite)
        if self.star > 0:
            col = [(255,80,80),(255,255,80),(80,255,80),(80,255,255)][(self.star // 4) % 4]
            tinted = spr.copy()
            overlay = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
            overlay.fill((*col, 110))
            tinted.blit(overlay, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            spr = tinted
        surf.blit(spr, (gx, gy))


class Fireball:
    def __init__(self, x, y, vx):
        self.x = x; self.y = y
        self.vx = vx; self.vy = 1.0
        self.alive = True
        self.bounces = 0
        self.anim = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), 8, 8)

    def update(self, lvl):
        self.anim += 1
        self.x += self.vx
        # check x
        r = self.rect
        tx = r.right//TILE if self.vx > 0 else r.left//TILE
        for ty in range(r.top//TILE, r.bottom//TILE + 1):
            if lvl.get_tile(tx, ty) in SOLID_CHARS:
                self.alive = False
                return
        self.vy += GRAVITY
        if self.vy > 4: self.vy = 4
        self.y += self.vy
        r = self.rect
        for tx in range(r.left//TILE, r.right//TILE + 1):
            ty = r.bottom // TILE
            if lvl.get_tile(tx, ty) in SOLID_CHARS:
                self.y = ty * TILE - 8
                self.vy = -3.5
                self.bounces += 1
                if self.bounces > 4:
                    self.alive = False
                break
        if self.x - lvl.cam_x < -16 or self.x - lvl.cam_x > NES_W + 16:
            self.alive = False
        if self.y > NES_H + 16:
            self.alive = False

    def draw(self, surf, cam_x):
        spr = ASSETS['fireball']
        if self.anim % 4 < 2:
            spr = pygame.transform.flip(spr, True, False)
        spr = pygame.transform.rotate(spr, -self.anim * 30)
        surf.blit(spr, (int(self.x - cam_x)-4, int(self.y)-4))


class Enemy:
    def __init__(self, x, y, kind, theme="over"):
        self.x = x; self.y = y
        self.vx = -0.5
        self.vy = 0.0
        self.kind = kind
        self.theme = theme
        self.alive = True
        self.squished = False
        self.squish_timer = 0
        self.shell = False
        self.shell_moving = False
        self.shell_vx = 0
        self.anim = 0
        self.on_ground = False
        self.flip_dead = False
        self.dead_timer = 0
        self.w = 14
        self.h = 14
        self.spawn_x = x
        self.active = False
        self.fire_immune = False
        self.is_red = (kind == 'koopa_r')
        if kind == 'piranha':
            self.w = 16; self.h = 24
            self.piranha_state = 'down'
            self.piranha_timer = 90
            self.original_y = y
            self.vx = 0
        if kind == 'koopa' or kind == 'koopa_r':
            self.h = 22
        if kind == 'hammer':
            self.h = 22
            self.hammer_cd = 30
            self.hammer_dir = 1

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, lvl, mario):
        if not self.alive:
            self.dead_timer += 1
            if self.flip_dead:
                self.y += self.vy
                self.vy += 0.30
            return
        # activate when within camera+margin
        if not self.active:
            if self.spawn_x - lvl.cam_x < NES_W + 32:
                self.active = True
            else:
                return
        if self.kind == 'piranha':
            self._update_piranha(lvl, mario)
            return
        if self.squished:
            self.squish_timer += 1
            if self.squish_timer > 30:
                self.alive = False
            return
        # gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL: self.vy = MAX_FALL
        # X
        self.x += self.vx
        r = self.rect
        sign = 1 if self.vx > 0 else -1
        if sign != 0:
            tx = (r.right-1)//TILE if sign > 0 else r.left//TILE
            blocked = False
            for ty in range(r.top//TILE, (r.bottom-1)//TILE + 1):
                if lvl.get_tile(tx, ty) in SOLID_CHARS:
                    blocked = True; break
            if blocked:
                if sign > 0: self.x = tx*TILE - self.w
                else:        self.x = (tx+1)*TILE
                self.vx = -self.vx
        # Y
        self.y += self.vy
        r = self.rect
        self.on_ground = False
        if self.vy > 0:
            ty = (r.bottom-1)//TILE
            for tx in range(r.left//TILE, (r.right-1)//TILE + 1):
                if lvl.get_tile(tx, ty) in SOLID_CHARS:
                    self.y = ty*TILE - self.h
                    self.vy = 0
                    self.on_ground = True
                    break
        # red koopa: turn at ledges
        if self.is_red and self.on_ground:
            check_x = self.x + (self.w + 2 if self.vx > 0 else -2)
            ty = (self.y + self.h + 2)//TILE
            tx = int(check_x)//TILE
            if lvl.get_tile(tx, ty) not in SOLID_CHARS:
                self.vx = -self.vx
        # shell moving
        if self.shell and self.shell_moving:
            # damage enemies
            for e in lvl.enemies:
                if e is self or not e.alive: continue
                if self.rect.colliderect(e.rect):
                    e.kill_flip()
                    lvl.add_score(200)
                    play('kick')
        # offscreen
        if self.y > NES_H + 32:
            self.alive = False
        self.anim += 0.18

    def _update_piranha(self, lvl, mario):
        # peek out only when mario isn't near top
        self.piranha_timer -= 1
        # If mario is on top of pipe, stay hidden
        mario_above = abs(mario.x - self.x) < 24 and mario.y < self.original_y + 8
        if self.piranha_state == 'down':
            if self.piranha_timer <= 0 and not mario_above:
                self.piranha_state = 'up'
                self.piranha_timer = 60
            self.y = self.original_y
        elif self.piranha_state == 'up':
            if self.y > self.original_y - 24:
                self.y -= 0.5
            else:
                if self.piranha_timer <= 0:
                    self.piranha_state = 'wait'
                    self.piranha_timer = 60
        elif self.piranha_state == 'wait':
            if self.piranha_timer <= 0:
                self.piranha_state = 'going_down'
        elif self.piranha_state == 'going_down':
            self.y += 0.5
            if self.y >= self.original_y:
                self.y = self.original_y
                self.piranha_state = 'down'
                self.piranha_timer = 120

    def squish(self):
        self.squished = True
        self.squish_timer = 0
        play('stomp')

    def kill_flip(self):
        self.alive = False
        self.flip_dead = True
        self.vy = -4.0
        self.dead_timer = 0
        play('kick')

    def stomp_to_shell(self):
        # koopa stomp -> shell
        self.shell = True
        self.shell_moving = False
        self.vx = 0
        self.h = 14
        play('stomp')

    def kick_shell(self, dir):
        self.shell_moving = True
        self.vx = dir * 4.5
        play('kick')

    def draw(self, surf, cam_x):
        gx = int(self.x - cam_x); gy = int(self.y)
        if not self.alive:
            if self.flip_dead:
                spr = ASSETS['goomba_dead']
                surf.blit(pygame.transform.flip(spr, False, True), (gx, gy))
            return
        if self.kind == 'goomba':
            if self.squished:
                surf.blit(ASSETS['goomba_dead'], (gx, gy))
                return
            suffix = '_u' if self.theme == 'under' else ('_c' if self.theme == 'castle' else '')
            spr = ASSETS[f'goomba_{"a" if int(self.anim)%2==0 else "b"}{suffix}']
            surf.blit(spr, (gx, gy))
        elif self.kind == 'koopa' or self.kind == 'koopa_r':
            r = 'r_' if self.is_red else ''
            if self.shell:
                surf.blit(ASSETS[f'koopa_{r}shell'], (gx, gy))
            else:
                spr = ASSETS[f'koopa_{r}{"a" if int(self.anim)%2==0 else "b"}']
                if self.vx > 0:
                    spr = pygame.transform.flip(spr, True, False)
                surf.blit(spr, (gx, gy-6))
        elif self.kind == 'piranha':
            surf.blit(ASSETS['piranha'], (gx, gy))
        elif self.kind == 'hammer':
            surf.blit(ASSETS['hammer_bro'], (gx, gy))


class PowerUp:
    def __init__(self, x, y, kind):
        self.x = x; self.y = y
        self.kind = kind  # 'mushroom','flower','star','1up'
        self.vx = 1.0 if kind != 'flower' else 0
        self.vy = 0
        self.alive = True
        self.spawn_y = y
        self.emerge_y = y - 16
        self.emerging = True
        self.anim = 0
        self.w = 14; self.h = 14

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, lvl):
        self.anim += 1
        if self.emerging:
            self.y -= 0.4
            if self.y <= self.emerge_y:
                self.y = self.emerge_y
                self.emerging = False
            return
        if self.kind == 'flower':
            return
        # mushroom / star / 1up
        if self.kind == 'star':
            if not hasattr(self, 'star_init'):
                self.vx = 2.0
                self.vy = -3.5
                self.star_init = True
        self.vy += GRAVITY
        if self.vy > MAX_FALL: self.vy = MAX_FALL
        self.x += self.vx
        r = self.rect
        sign = 1 if self.vx > 0 else -1
        if sign != 0:
            tx = (r.right-1)//TILE if sign > 0 else r.left//TILE
            for ty in range(r.top//TILE, (r.bottom-1)//TILE + 1):
                if lvl.get_tile(tx, ty) in SOLID_CHARS:
                    if sign > 0: self.x = tx*TILE - self.w
                    else: self.x = (tx+1)*TILE
                    self.vx = -self.vx
                    break
        self.y += self.vy
        r = self.rect
        if self.vy > 0:
            ty = (r.bottom-1)//TILE
            for tx in range(r.left//TILE, (r.right-1)//TILE + 1):
                if lvl.get_tile(tx, ty) in SOLID_CHARS:
                    self.y = ty*TILE - self.h
                    self.vy = (-5 if self.kind == 'star' else 0)
                    break
        if self.y > NES_H + 32:
            self.alive = False

    def draw(self, surf, cam_x):
        gx = int(self.x - cam_x); gy = int(self.y)
        if self.kind == 'mushroom':
            surf.blit(ASSETS['mushroom'], (gx, gy))
        elif self.kind == 'flower':
            surf.blit(ASSETS['flower'], (gx, gy))
        elif self.kind == 'star':
            surf.blit(ASSETS['star'], (gx, gy))
        elif self.kind == '1up':
            surf.blit(ASSETS['oneup'], (gx, gy))


class Coin:
    def __init__(self, x, y, popup=False):
        self.x = x; self.y = y
        self.popup = popup
        self.vy = -4 if popup else 0
        self.alive = True
        self.timer = 0
        self.anim = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x)+2, int(self.y), 10, 14)

    def update(self, lvl):
        self.anim += 1
        if self.popup:
            self.timer += 1
            self.y += self.vy
            self.vy += GRAVITY
            if self.timer > 30:
                self.alive = False
        # static coins picked up by collision check in level

    def draw(self, surf, cam_x):
        spr = _coin_collectible(self.anim // 6)
        surf.blit(spr, (int(self.x - cam_x), int(self.y)))


class Particle:
    def __init__(self, x, y, vx, vy, color, life=30):
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.color = color
        self.life = life
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += GRAVITY
        self.life -= 1
        if self.life <= 0: self.alive = False

    def draw(self, surf, cam_x):
        pygame.draw.rect(surf, self.color,
                         (int(self.x - cam_x), int(self.y), 3, 3))


class ScorePopup:
    def __init__(self, x, y, text, color=(255,255,255)):
        self.x = x; self.y = y; self.text = text; self.color = color
        self.life = 50
        self.alive = True
    def update(self):
        self.y -= 1
        self.life -= 1
        if self.life <= 0: self.alive = False
    def draw(self, surf, cam_x, font):
        img = font.render(self.text, False, self.color)
        surf.blit(img, (int(self.x - cam_x), int(self.y)))


# ============================================================
#  LEVEL
# ============================================================

class Level:
    def __init__(self, key, game):
        self.key = key
        self.game = game
        info = LEVELS[key]
        self.theme = info["theme"]
        self.time = info["time"]
        self.music_kind = info["music"]
        self.end_kind = info["end"]
        self.smbdis_object = info.get("smbdis_object")
        self.smbdis_label = info.get("smbdis_label")
        raw_rows = info["data"]
        if self.end_kind == "flag":
            raw_rows = _ensure_smb1_flagpole(raw_rows)
        self.rows = [list(r) for r in raw_rows]
        self.h = len(self.rows)
        self.w = max(len(r) for r in self.rows)
        self.flag_x = info.get("flagpole_x")
        if self.flag_x is None and self.end_kind == "flag":
            self.flag_x = _flagpole_target_x([''.join(r) for r in self.rows])
        self.flag_y_top = 1
        self.flag_y_bottom = 12 * TILE
        # pad rows
        for i, r in enumerate(self.rows):
            if len(r) < self.w:
                self.rows[i] = r + ['.'] * (self.w - len(r))
        self.cam_x = 0
        self.enemies = []
        self.powerups = []
        self.coins = []
        self.particles = []
        self.popups = []
        self.bg_decor = []
        self.qb_anim = 0
        self.lava_anim = 0
        self.castle_x = None
        self.axe_pos = None
        self.bowser_x = None
        self.bowser = None
        # spawn things
        self._populate()

    def _populate(self):
        # flagpole anchor (composite sprite — not T tiles in the grid)
        if self.flag_x is None and self.end_kind == "flag":
            self.flag_x = _flagpole_target_x([''.join(r) for r in self.rows])
            self.flag_y_top = 1
            self.flag_y_bottom = 12 * TILE
        for x in range(self.w):
            for y in range(self.h):
                c = self.rows[y][x]
                if c == 'C' and self.castle_x is None:
                    self.castle_x = x * TILE
                if c == 'A':
                    self.axe_pos = (x, y)
        if self.castle_x is None and self.end_kind == 'flag' and self.flag_x is not None:
            self.castle_x = (self.flag_x + 10) * TILE
        # find pipes -> spawn occasional piranhas
        rng = random.Random(hash(self.key))
        for x in range(1, self.w - 1):
            for y in range(2, self.h - 2):
                c = self.rows[y][x]
                if c == '[':
                    # is top of pipe?
                    if y + 1 < self.h and self.rows[y+1][x] == '{':
                        if rng.random() < 0.35 and self.theme == "over":
                            e = Enemy(x*TILE, y*TILE - 4, 'piranha', self.theme)
                            self.enemies.append(e)
        # add goombas / koopas based on level
        e_rng = random.Random(hash(self.key) ^ 0xC47C47)
        density = 0.04 if self.theme != "castle" else 0.02
        for x in range(8, self.w - 30):
            if self.rows[12][x] in ('.', 'L'): continue
            if self.rows[12][x] != 'X': continue
            # don't spawn on flagpole stretch
            if self.flag_x and abs(x - self.flag_x) < 30: continue
            if e_rng.random() < density:
                kind = e_rng.choices(
                    ['goomba','goomba','koopa','koopa_r','hammer'],
                    weights=[6,5,3,2,1 if int(self.key.split('-')[0]) >= 3 else 0]
                )[0]
                if self.theme == "under" and kind in ('hammer',):
                    kind = 'goomba'
                e = Enemy(x*TILE, 11*TILE, kind, self.theme)
                self.enemies.append(e)
        # convert 'o' tiles to coins
        for y in range(self.h):
            for x in range(self.w):
                if self.rows[y][x] == 'o':
                    self.coins.append(Coin(x*TILE, y*TILE))
                    self.rows[y][x] = '.'
        # Bowser at end of 8-4
        if self.key == "8-4":
            self.bowser = Bowser(self.w*TILE - 60, 11*TILE)
        # Background decorations: clouds, bushes, hills
        if self.theme == "over":
            d_rng = random.Random(hash(self.key) ^ 0x1234)
            for _ in range(self.w // 8):
                bx = d_rng.randint(2, self.w-4)
                by = d_rng.choice([1,2,3])
                self.bg_decor.append(('cloud', bx*TILE, by*TILE))
            for _ in range(self.w // 6):
                bx = d_rng.randint(2, self.w-6)
                self.bg_decor.append(('bush', bx*TILE, 12*TILE - 4))
            for _ in range(self.w // 10):
                bx = d_rng.randint(2, self.w-8)
                self.bg_decor.append(('hill', bx*TILE, 12*TILE - 24))

    def get_tile(self, x, y):
        if y < 0: return '.'
        if y >= self.h: return 'X'  # below floor = solid (no falling through)
        if x < 0 or x >= self.w: return 'X' if (0 <= y < self.h) else '.'
        return self.rows[y][x]

    def set_tile(self, x, y, c):
        if 0 <= y < self.h and 0 <= x < self.w:
            self.rows[y][x] = c

    def hit_block(self, tx, ty, mario):
        c = self.get_tile(tx, ty)
        if c == 'B':
            if mario.power > 0:
                # break
                self.set_tile(tx, ty, '.')
                for _ in range(6):
                    self.particles.append(Particle(
                        tx*TILE + 8, ty*TILE + 8,
                        random.uniform(-2, 2), random.uniform(-4, -2),
                        P['darkred'] if self.theme == 'castle' else (216,92,8),
                        30))
                self.add_score(50)
                play('break')
            else:
                # bump
                play('bump')
        elif c == '?' or c == '!':
            self.set_tile(tx, ty, 'U')
            # spawn coin or powerup
            if c == '?':
                self.coins.append(Coin(tx*TILE, ty*TILE - TILE, popup=True))
                self.add_score(200)
                self.game.coins += 1
                if self.game.coins >= 100:
                    self.game.coins -= 100
                    self.game.lives += 1
                    play('1up')
                else:
                    play('coin')
            elif c == '!':
                kind = 'mushroom' if mario.power == 0 else 'flower'
                self.powerups.append(PowerUp(tx*TILE, ty*TILE, kind))
                play('powerup')
        elif c == '-':
            # invisible 1up
            self.set_tile(tx, ty, 'U')
            self.powerups.append(PowerUp(tx*TILE, ty*TILE, '1up'))
            play('powerup')

    def add_score(self, n):
        self.game.score += n

    def update(self, mario):
        self.qb_anim = (self.qb_anim + 1) % 60
        self.lava_anim += 1
        # camera follows mario
        target_cam = max(0, mario.x - NES_W//2 + 8)
        if target_cam > self.cam_x:
            self.cam_x = target_cam
        max_cam = self.w * TILE - NES_W
        if self.cam_x > max_cam: self.cam_x = max_cam
        if self.cam_x < 0: self.cam_x = 0

        # update enemies
        for e in self.enemies:
            e.update(self, mario)
        # update powerups
        for p in self.powerups:
            p.update(self)
        for c in self.coins:
            c.update(self)
        for pa in self.particles:
            pa.update()
        for sp in self.popups:
            sp.update()
        if self.bowser:
            self.bowser.update(self, mario)
        # collisions
        if not mario.dead and not mario.flag_grab and not mario.entering_pipe and mario.growth_anim == 0:
            mr = mario.rect
            # enemy collisions
            for e in self.enemies:
                if not e.alive or not e.active: continue
                if not mr.colliderect(e.rect): continue
                if mario.star > 0:
                    e.kill_flip()
                    self.add_score(200)
                    self.popups.append(ScorePopup(e.x, e.y, "200"))
                    continue
                # stomp logic
                if e.kind == 'piranha':
                    mario.hurt(self)
                    continue
                if mario.vy > 0 and mario.y + mario.h - 6 < e.y + 6:
                    # stomp
                    if e.kind == 'goomba':
                        e.squish()
                        mario.vy = -3.5
                        self.add_score(100)
                        self.popups.append(ScorePopup(e.x, e.y, "100"))
                    elif e.kind in ('koopa','koopa_r'):
                        if not e.shell:
                            e.stomp_to_shell()
                            mario.vy = -3.5
                            self.add_score(100)
                            self.popups.append(ScorePopup(e.x, e.y, "100"))
                        else:
                            if e.shell_moving:
                                e.shell_moving = False
                                e.vx = 0
                                mario.vy = -3.5
                            else:
                                dir = 1 if mario.x < e.x else -1
                                e.kick_shell(dir)
                                mario.vy = -3.5
                    elif e.kind == 'hammer':
                        mario.hurt(self)
                else:
                    if e.kind in ('koopa','koopa_r') and e.shell and not e.shell_moving:
                        dir = 1 if mario.x < e.x else -1
                        e.kick_shell(dir)
                        self.add_score(400)
                    else:
                        mario.hurt(self)
            # powerup collisions
            for p in self.powerups:
                if not p.alive: continue
                if mr.colliderect(p.rect):
                    if p.kind == 'mushroom':
                        if mario.power == 0:
                            mario.power = 1
                            mario.y -= 16
                            mario.growth_anim = 24
                        self.add_score(1000)
                        self.popups.append(ScorePopup(p.x, p.y, "1000"))
                        play('powerget')
                    elif p.kind == 'flower':
                        if mario.power < 2:
                            if mario.power == 0:
                                mario.power = 1
                                mario.y -= 16
                                mario.growth_anim = 24
                            mario.power = 2
                            mario.fire_anim = 18
                        self.add_score(1000)
                        self.popups.append(ScorePopup(p.x, p.y, "1000"))
                        play('powerget')
                    elif p.kind == 'star':
                        mario.star = STAR_FRAMES
                        self.add_score(1000)
                        self.popups.append(ScorePopup(p.x, p.y, "1000"))
                        play('powerget')
                    elif p.kind == '1up':
                        self.game.lives += 1
                        self.popups.append(ScorePopup(p.x, p.y, "1UP", P['lgreen']))
                        play('1up')
                    p.alive = False
            # coin pickups (static)
            for c in self.coins:
                if not c.alive: continue
                if c.popup: continue
                if mr.colliderect(c.rect):
                    c.alive = False
                    self.add_score(200)
                    self.game.coins += 1
                    if self.game.coins >= 100:
                        self.game.coins -= 100
                        self.game.lives += 1
                        play('1up')
                    else:
                        play('coin')
            # fireball <-> enemy
            for fb in mario.fireballs:
                if not fb.alive: continue
                for e in self.enemies:
                    if not e.alive: continue
                    if fb.rect.colliderect(e.rect):
                        if e.fire_immune: continue
                        e.kill_flip()
                        fb.alive = False
                        self.add_score(200)
                        self.popups.append(ScorePopup(e.x, e.y, "200"))
                        break
            # flagpole grab
            if self.flag_x and not mario.flag_grab:
                fx_px = self.flag_x * TILE
                if mario.x + mario.W > fx_px and mario.x < fx_px + TILE:
                    mario.flag_grab = True
                    mario.flag_timer = 0
                    mario.x = fx_px - 6
                    mario.vx = 0; mario.vy = 0
                    # score based on height
                    yfrac = max(0, min(1, 1 - (mario.y / (self.flag_y_bottom - 16))))
                    bonus = int(yfrac * 5000)
                    self.add_score(bonus)
                    self.popups.append(ScorePopup(fx_px, mario.y, str(bonus)))
                    play('flag')
            # axe touch (castle clear)
            if self.axe_pos:
                ax, ay = self.axe_pos
                ar = pygame.Rect(ax*TILE, ay*TILE, TILE, TILE)
                if mr.colliderect(ar):
                    mario.level_done = True
                    self.axe_pos = None
                    play('clear')
                    # collapse bridge (visual: remove '=' tiles to the right)
                    for x in range(ax+1, self.w):
                        if self.rows[ay-1][x] == '=':
                            self.rows[ay-1][x] = '.'
                    if self.bowser:
                        self.bowser.fall()

        # fireballs update
        for fb in mario.fireballs:
            fb.update(self)
        mario.fireballs[:] = [f for f in mario.fireballs if f.alive]
        # cleanup
        self.enemies[:] = [e for e in self.enemies if e.alive or e.dead_timer < 40]
        self.powerups[:] = [p for p in self.powerups if p.alive]
        self.coins[:] = [c for c in self.coins if c.alive]
        self.particles[:] = [p for p in self.particles if p.alive]
        self.popups[:] = [s for s in self.popups if s.alive]

    def draw(self, surf):
        # background
        if self.theme == "over":
            surf.fill(P['sky'])
        elif self.theme == "under":
            surf.fill(P['underground'])
        else:
            surf.fill(P['castle_bg'])
        # bg decorations
        for kind, bx, by in self.bg_decor:
            gx = bx - int(self.cam_x)
            if gx < -64 or gx > NES_W: continue
            surf.blit(ASSETS[kind], (gx, by))
        # tiles
        cam_tx = int(self.cam_x) // TILE
        finish_junk = set('XBSC?![]{}=U#')
        for ty in range(self.h):
            for tx in range(cam_tx, cam_tx + NES_W//TILE + 2):
                if tx < 0 or tx >= self.w: continue
                c = self.rows[ty][tx]
                if c == '.' or c == 'o': continue
                if self.end_kind == 'flag' and self.flag_x is not None:
                    if tx == self.flag_x and ty < 13 and c in 'TF':
                        continue
                    if (self.flag_x - 32) <= tx <= (self.flag_x + 4) and ty < 12 and c in finish_junk:
                        continue
                gx = tx*TILE - int(self.cam_x); gy = ty*TILE
                if c == 'X':
                    surf.blit(ASSETS[f'ground_{self.theme}'], (gx, gy))
                elif c == 'B':
                    surf.blit(ASSETS[f'brick_{self.theme}'], (gx, gy))
                elif c == '?' or c == '!':
                    surf.blit(_question_tile(self.qb_anim // 12), (gx, gy))
                elif c == 'U':
                    surf.blit(ASSETS['question_used'], (gx, gy))
                elif c == '[':
                    surf.blit(ASSETS[f'pipe_tl_{self.theme}'], (gx, gy))
                elif c == ']':
                    surf.blit(ASSETS[f'pipe_tr_{self.theme}'], (gx, gy))
                elif c == '{':
                    surf.blit(ASSETS[f'pipe_bl_{self.theme}'], (gx, gy))
                elif c == '}':
                    surf.blit(ASSETS[f'pipe_br_{self.theme}'], (gx, gy))
                elif c == 'S':
                    surf.blit(ASSETS['solid'], (gx, gy))
                elif c == 'T':
                    if ty == 1:
                        surf.blit(ASSETS['flag_top'], (gx, gy))
                    else:
                        surf.blit(ASSETS['flag_pole'], (gx, gy))
                elif c == 'F':
                    surf.blit(ASSETS['flag_base'], (gx, gy))
                elif c == 'C':
                    surf.blit(ASSETS['castle_tile'], (gx, gy))
                elif c == 'L':
                    surf.blit(_lava_tile(self.lava_anim), (gx, gy))
                elif c == '=':
                    surf.blit(ASSETS['bridge'], (gx, gy))
                elif c == 'A':
                    surf.blit(ASSETS['axe'], (gx, gy))
                elif c == '-':
                    pass
                elif c == '#':
                    surf.blit(ASSETS[f'brick_{self.theme}'], (gx, gy))
        if self.end_kind == 'flag' and self.flag_x is not None:
            gx = self.flag_x * TILE - int(self.cam_x)
            if -TILE < gx < NES_W:
                surf.blit(ASSETS['flagpole_composite'], (gx, TILE))
        # coins
        for c in self.coins:
            c.draw(surf, self.cam_x)
        # powerups
        for p in self.powerups:
            p.draw(surf, self.cam_x)
        # enemies
        for e in self.enemies:
            e.draw(surf, self.cam_x)
        # bowser
        if self.bowser:
            self.bowser.draw(surf, self.cam_x)
        # particles
        for pa in self.particles:
            pa.draw(surf, self.cam_x)


class Bowser:
    def __init__(self, x, y):
        self.x = x; self.y = y
        self.vx = -0.5
        self.vy = 0
        self.alive = True
        self.falling = False
        self.fire_cd = 90
        self.anim = 0
        self.hp = 5  # fireballs to kill normally
        self.flame_cd = 60
        self.flames = []

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), 28, 30)

    def update(self, lvl, mario):
        self.anim += 1
        if self.falling:
            self.y += self.vy
            self.vy += 0.35
            return
        # patrol
        self.x += self.vx
        if self.x < lvl.w*TILE - 96: self.vx = abs(self.vx)
        if self.x > lvl.w*TILE - 40:  self.vx = -abs(self.vx)
        # gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL: self.vy = MAX_FALL
        self.y += self.vy
        if self.y > 11*TILE:
            self.y = 11*TILE
            self.vy = 0
            if random.random() < 0.02:
                self.vy = -3.5
        # breathe fire
        self.flame_cd -= 1
        if self.flame_cd <= 0:
            self.flames.append([self.x-8, self.y+10, -2.5, 0])
            self.flame_cd = 100
        for f in self.flames:
            f[0] += f[2]; f[1] += f[3]
            r = pygame.Rect(int(f[0]), int(f[1]), 12, 6)
            if r.colliderect(mario.rect):
                mario.hurt(lvl)
        self.flames = [f for f in self.flames if f[0] > lvl.cam_x - 16]
        # mario fireball collision
        for fb in mario.fireballs:
            if fb.rect.colliderect(self.rect):
                fb.alive = False
                self.hp -= 1
                if self.hp <= 0:
                    self.fall()
                    lvl.add_score(5000)

    def fall(self):
        self.falling = True
        self.vy = -3.0
        play('bowserfall')

    def draw(self, surf, cam_x):
        gx = int(self.x - cam_x); gy = int(self.y)
        spr = ASSETS['bowser']
        if self.anim % 30 < 15:
            spr = pygame.transform.flip(spr, True, False)
        if self.falling:
            spr = pygame.transform.flip(spr, False, True)
        surf.blit(spr, (gx, gy))
        for f in self.flames:
            pygame.draw.rect(surf, P['orange'], (int(f[0]-cam_x), int(f[1]), 12, 6))
            pygame.draw.rect(surf, P['yellow'], (int(f[0]-cam_x)+2, int(f[1])+2, 6, 2))


# ============================================================
#  FONT (procedural 8x8 bitmap font)
# ============================================================

FONT_GLYPHS = {
    'A':"01110/10001/10001/11111/10001/10001/10001/00000",
    'B':"11110/10001/10001/11110/10001/10001/11110/00000",
    'C':"01110/10001/10000/10000/10000/10001/01110/00000",
    'D':"11110/10001/10001/10001/10001/10001/11110/00000",
    'E':"11111/10000/10000/11110/10000/10000/11111/00000",
    'F':"11111/10000/10000/11110/10000/10000/10000/00000",
    'G':"01110/10001/10000/10111/10001/10001/01111/00000",
    'H':"10001/10001/10001/11111/10001/10001/10001/00000",
    'I':"01110/00100/00100/00100/00100/00100/01110/00000",
    'J':"00111/00010/00010/00010/00010/10010/01100/00000",
    'K':"10001/10010/10100/11000/10100/10010/10001/00000",
    'L':"10000/10000/10000/10000/10000/10000/11111/00000",
    'M':"10001/11011/10101/10101/10001/10001/10001/00000",
    'N':"10001/11001/10101/10101/10011/10001/10001/00000",
    'O':"01110/10001/10001/10001/10001/10001/01110/00000",
    'P':"11110/10001/10001/11110/10000/10000/10000/00000",
    'Q':"01110/10001/10001/10001/10101/10010/01101/00000",
    'R':"11110/10001/10001/11110/10100/10010/10001/00000",
    'S':"01111/10000/10000/01110/00001/00001/11110/00000",
    'T':"11111/00100/00100/00100/00100/00100/00100/00000",
    'U':"10001/10001/10001/10001/10001/10001/01110/00000",
    'V':"10001/10001/10001/10001/10001/01010/00100/00000",
    'W':"10001/10001/10001/10101/10101/11011/10001/00000",
    'X':"10001/10001/01010/00100/01010/10001/10001/00000",
    'Y':"10001/10001/01010/00100/00100/00100/00100/00000",
    'Z':"11111/00001/00010/00100/01000/10000/11111/00000",
    '0':"01110/10011/10101/10101/11001/10001/01110/00000",
    '1':"00100/01100/00100/00100/00100/00100/01110/00000",
    '2':"01110/10001/00001/00010/00100/01000/11111/00000",
    '3':"11111/00010/00100/00010/00001/10001/01110/00000",
    '4':"00010/00110/01010/10010/11111/00010/00010/00000",
    '5':"11111/10000/11110/00001/00001/10001/01110/00000",
    '6':"00110/01000/10000/11110/10001/10001/01110/00000",
    '7':"11111/00001/00010/00100/00100/01000/01000/00000",
    '8':"01110/10001/10001/01110/10001/10001/01110/00000",
    '9':"01110/10001/10001/01111/00001/00010/01100/00000",
    '-':"00000/00000/00000/01110/00000/00000/00000/00000",
    '.':"00000/00000/00000/00000/00000/00110/00110/00000",
    ',':"00000/00000/00000/00000/00000/00110/00110/00100",
    '!':"00100/00100/00100/00100/00100/00000/00100/00000",
    '?':"01110/10001/00001/00010/00100/00000/00100/00000",
    ':':"00000/00100/00100/00000/00100/00100/00000/00000",
    'x':"00000/00000/10001/01010/00100/01010/10001/00000",
    "'":"00100/00100/00000/00000/00000/00000/00000/00000",
    '(':"00010/00100/01000/01000/01000/00100/00010/00000",
    ')':"01000/00100/00010/00010/00010/00100/01000/00000",
    '*':"00100/10101/01110/11111/01110/10101/00100/00000",
    '+':"00000/00100/00100/11111/00100/00100/00000/00000",
    '/':"00001/00010/00010/00100/01000/01000/10000/00000",
    '>':"01000/00100/00010/00001/00010/00100/01000/00000",
    '<':"00010/00100/01000/10000/01000/00100/00010/00000",
    '=':"00000/00000/11111/00000/11111/00000/00000/00000",
    '%':"11000/11001/00010/00100/01000/10011/00011/00000",
    '$':"00100/01111/10100/01110/00101/11110/00100/00000",
    '#':"01010/01010/11111/01010/11111/01010/01010/00000",
    '_':"00000/00000/00000/00000/00000/00000/11111/00000",
    "&":"01000/10100/10100/01000/10101/10010/01101/00000",
    ' ':"00000/00000/00000/00000/00000/00000/00000/00000",
    '|':"00100/00100/00100/00100/00100/00100/00100/00000",
    '"':"01010/01010/00000/00000/00000/00000/00000/00000",
}

_font_cache = {}

def render_text(text, color=(252,252,252), scale=1):
    text = text.upper() if any(c.islower() and c not in FONT_GLYPHS for c in text) else text
    chars = []
    for ch in text:
        glyph = FONT_GLYPHS.get(ch) or FONT_GLYPHS.get(ch.upper()) or FONT_GLYPHS[' ']
        chars.append(glyph)
    w = len(chars) * 8 * scale
    h = 8 * scale
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for i, glyph in enumerate(chars):
        rows = glyph.split('/')
        for y, row in enumerate(rows):
            for x, bit in enumerate(row):
                if bit == '1':
                    surf.fill(color, (i*8*scale + x*scale, y*scale, scale, scale))
    return surf

def draw_text(surf, text, x, y, color=(252,252,252), scale=1, center=False):
    img = render_text(text, color, scale)
    if center:
        x -= img.get_width()//2
    surf.blit(img, (x, y))
    return img.get_width()

# ============================================================
#  GAME STATE MACHINE
# ============================================================

STATE_TITLE = 0
STATE_MENU = 1
STATE_PLAYING = 2
STATE_PAUSED = 3
STATE_GAMEOVER = 4
STATE_WORLD_CARD = 5
STATE_VICTORY = 6
STATE_HELP = 7
STATE_ABOUT = 8

class Game:
    def __init__(self):
        self.state = STATE_TITLE
        self.next_state = None
        self.level_key = "1-1"
        self.level = None
        self.mario = None
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.time_left = 400
        self.time_frames = 0
        self.menu_idx = 0
        self.menu_options = ["1 PLAYER GAME", "ABOUT", "HELP", "EXIT"]
        self.card_timer = 0
        self.fade_alpha = 0
        self.fade_dir = 0
        self.victory_timer = 0
        self.title_anim = 0
        self.last_world = 1

    def start_new_game(self):
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.level_key = "1-1"
        self.enter_world_card()

    def enter_world_card(self):
        self.state = STATE_WORLD_CARD
        self.card_timer = 0

    def start_level(self):
        self.level = Level(self.level_key, self)
        # spawn mario at left
        my = 11 * TILE - 16
        self.mario = Mario(2 * TILE, my)
        # carry power - here keep simple: lose power on death
        self.time_left = self.level.time
        self.time_frames = 0
        self.state = STATE_PLAYING
        start_music(self.level.music_kind)

    def next_level(self):
        w, s = self.level_key.split('-')
        w = int(w); s = int(s)
        s += 1
        if s > 4:
            s = 1; w += 1
            if w > 8:
                stop_music()
                self.state = STATE_VICTORY
                self.victory_timer = 0
                return
        self.level_key = f"{w}-{s}"
        self.enter_world_card()

    def player_died(self):
        stop_music()
        self.lives -= 1
        if self.lives < 0:
            self.state = STATE_GAMEOVER
            self.card_timer = 0
            return
        self.enter_world_card()

    def update(self, keys, events):
        if self.state == STATE_TITLE:
            self.title_anim += 1
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        self.state = STATE_MENU
                        self.menu_idx = 0
                        play('coin')
        elif self.state == STATE_MENU:
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_UP, pygame.K_w):
                        self.menu_idx = (self.menu_idx - 1) % len(self.menu_options)
                        play('bump')
                    elif ev.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_idx = (self.menu_idx + 1) % len(self.menu_options)
                        play('bump')
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        opt = self.menu_options[self.menu_idx]
                        if opt.startswith("1 PLAYER"):
                            self.start_new_game()
                            play('powerup')
                        elif opt == "ABOUT":
                            self.state = STATE_ABOUT
                        elif opt == "HELP":
                            self.state = STATE_HELP
                        elif opt == "EXIT":
                            pygame.quit(); sys.exit(0)
                    elif ev.key == pygame.K_ESCAPE:
                        self.state = STATE_TITLE
        elif self.state == STATE_WORLD_CARD:
            self.card_timer += 1
            if self.card_timer == 1:
                play('pause')
            if self.card_timer > 120:
                self.start_level()
        elif self.state == STATE_PLAYING:
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_p:
                        stop_music()
                        self.state = STATE_PAUSED
                        play('pause')
                    elif ev.key == pygame.K_ESCAPE:
                        stop_music()
                        self.state = STATE_TITLE
            ensure_music_loop()
            self.level.update(self.mario)
            self.mario.update(keys, self.level)
            # time
            self.time_frames += 1
            if self.time_frames >= TIME_FRAMES_PER_TICK:  # SMB1 timer @ 60 Hz Famicom
                self.time_frames = 0
                self.time_left -= 1
                if self.time_left <= 0:
                    self.mario.die()
            if self.mario.dead and self.mario.dead_timer > 120:
                stop_music()
                self.player_died()
            if self.mario.level_done and self.mario.level_done_timer > 60:
                # add time bonus
                bonus = self.time_left * 50
                self.score += bonus
                self.next_level()
        elif self.state == STATE_PAUSED:
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_p:
                        self.state = STATE_PLAYING
                        play('pause')
                        if self.level:
                            start_music(self.level.music_kind)
                    elif ev.key == pygame.K_ESCAPE:
                        self.state = STATE_TITLE
        elif self.state == STATE_GAMEOVER:
            self.card_timer += 1
            for ev in events:
                if ev.type == pygame.KEYDOWN and self.card_timer > 60:
                    self.state = STATE_TITLE
        elif self.state == STATE_VICTORY:
            self.victory_timer += 1
            for ev in events:
                if ev.type == pygame.KEYDOWN and self.victory_timer > 60:
                    self.state = STATE_TITLE
        elif self.state in (STATE_HELP, STATE_ABOUT):
            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    self.state = STATE_MENU

    def draw_title(self, surf):
        surf.fill(P['black'])
        # starfield
        rng = random.Random(self.title_anim // 60)
        for _ in range(40):
            x = rng.randint(0, NES_W-1)
            y = rng.randint(0, NES_H-1)
            surf.set_at((x, y), P['white'])
        # logo
        draw_text(surf, "SUPER", NES_W//2, 40, P['red'], 3, center=True)
        draw_text(surf, "MARIO BROS.", NES_W//2, 72, P['white'], 2, center=True)
        draw_text(surf, "AC SMB14k MAC PORT", NES_W//2, 96, P['yellow'], 1, center=True)
        # cat logo
        cat_y = 130
        pygame.draw.circle(surf, P['orange'], (NES_W//2, cat_y), 14)
        pygame.draw.polygon(surf, P['orange'], [(NES_W//2-12, cat_y-8),(NES_W//2-16, cat_y-18),(NES_W//2-6, cat_y-12)])
        pygame.draw.polygon(surf, P['orange'], [(NES_W//2+12, cat_y-8),(NES_W//2+16, cat_y-18),(NES_W//2+6, cat_y-12)])
        surf.set_at((NES_W//2-5, cat_y-2), P['black'])
        surf.set_at((NES_W//2+5, cat_y-2), P['black'])
        pygame.draw.line(surf, P['black'], (NES_W//2-3, cat_y+4), (NES_W//2+3, cat_y+4))
        # blink prompt
        if (self.title_anim // 30) % 2 == 0:
            draw_text(surf, "PRESS START", NES_W//2, 170, P['white'], 2, center=True)
        draw_text(surf, "AC HOLDINGS", NES_W//2, 210, P['gray'], 1, center=True)
        draw_text(surf, "FILES=OFF  60 FPS  FAMICOM", NES_W//2, 222, P['gray'], 1, center=True)

    def draw_menu(self, surf):
        surf.fill(P['black'])
        draw_text(surf, "AC SMB14k MAC PORT", NES_W//2, 30, P['red'], 2, center=True)
        draw_text(surf, "MAIN MENU", NES_W//2, 60, P['white'], 1, center=True)
        for i, opt in enumerate(self.menu_options):
            color = P['yellow'] if i == self.menu_idx else P['white']
            prefix = "> " if i == self.menu_idx else "  "
            draw_text(surf, prefix + opt, NES_W//2, 100 + i*20, color, 2, center=True)
        draw_text(surf, "Z/SPACE = CONFIRM   ARROWS = MOVE", NES_W//2, 215, P['gray'], 1, center=True)

    def draw_about(self, surf):
        surf.fill(P['darkblue'])
        draw_text(surf, "ABOUT", NES_W//2, 20, P['yellow'], 2, center=True)
        lines = [
            "AC HOLDINGS SMB14k MAC PORT",
            "SUPER MARIO BROS. (SMB1)",
            "",
            "BUILT BY AC HOLDINGS",
            "PYTHON 3.14 + PYGAME",
            "",
            "ALL 32 STAGES 1-1 TO 8-4",
            "SMB1 DISASSEMBLY LAYOUT",
            "60 FPS FAMICOM-ACCURATE SPEED",
            "MARIO MAKER HD SPRITES",
            "SMB1 SEAMLESS AUDIO LOOPS",
            "",
            "FILES = OFF  (SINGLE FILE)",
            "PYTHON 3.14 + PYGAME",
            "",
            "MEOW OWO",
        ]
        for i, l in enumerate(lines):
            draw_text(surf, l, NES_W//2, 50 + i*12, P['white'], 1, center=True)
        draw_text(surf, "PRESS ANY KEY", NES_W//2, 220, P['yellow'], 1, center=True)

    def draw_help(self, surf):
        surf.fill(P['darkgreen'])
        draw_text(surf, "HELP", NES_W//2, 20, P['yellow'], 2, center=True)
        lines = [
            "MOVE        ARROWS / WASD",
            "RUN/FIRE    X OR LSHIFT",
            "JUMP        Z OR SPACE",
            "DUCK        DOWN (BIG ONLY)",
            "PAUSE       P",
            "BACK        ESC",
            "",
            "POWERUPS:",
            " MUSHROOM = GROW BIG",
            " FIRE FLOWER = SHOOT",
            " STAR = INVINCIBLE",
            " 1UP = EXTRA LIFE",
            "",
            "STOMP ENEMIES FROM ABOVE!",
            "REACH FLAGPOLE OR AXE!",
        ]
        for i, l in enumerate(lines):
            draw_text(surf, l, NES_W//2, 45 + i*11, P['white'], 1, center=True)
        draw_text(surf, "PRESS ANY KEY", NES_W//2, 225, P['yellow'], 1, center=True)

    def draw_world_card(self, surf):
        surf.fill(P['black'])
        w, s = self.level_key.split('-')
        draw_text(surf, f"WORLD {w}-{s}", NES_W//2, 90, P['white'], 3, center=True)
        # mario icon
        surf.blit(ASSETS['mario_small_stand'], (NES_W//2 - 30, 130))
        draw_text(surf, f"X {self.lives:>2}", NES_W//2 + 5, 134, P['white'], 2)

    def draw_hud(self, surf):
        # top hud
        draw_text(surf, "MARIO", 16, 8, P['white'], 1)
        draw_text(surf, f"{self.score:06d}", 16, 18, P['white'], 1)
        # coin icon
        coin_spr = _coin_collectible(self.level.qb_anim // 12 if self.level else 0)
        small = pygame.transform.scale(coin_spr, (8,8))
        surf.blit(small, (90, 18))
        draw_text(surf, f"x{self.coins:02d}", 100, 18, P['white'], 1)
        w, s = self.level_key.split('-')
        draw_text(surf, f"WORLD", 150, 8, P['white'], 1)
        draw_text(surf, f"{w}-{s}", 165, 18, P['white'], 1)
        draw_text(surf, "TIME", 210, 8, P['white'], 1)
        tcol = P['red'] if self.time_left < 100 else P['white']
        draw_text(surf, f"{max(0,self.time_left):3d}", 215, 18, tcol, 1)

    def draw_playing(self, surf):
        if self.level is None: return
        self.level.draw(surf)
        # score popups (use render_text, which is the correct path)
        for sp in self.level.popups:
            img = render_text(sp.text, sp.color, 1)
            surf.blit(img, (int(sp.x - self.level.cam_x), int(sp.y)))
        # mario
        self.mario.draw(surf, self.level.cam_x)
        for fb in self.mario.fireballs:
            fb.draw(surf, self.level.cam_x)
        self.draw_hud(surf)
        # grow/fire flash
        if self.mario.growth_anim > 0 and self.mario.growth_anim % 4 < 2:
            r = self.mario.rect
            pygame.draw.rect(surf, P['white'], (r.x - self.level.cam_x, r.y, r.w, r.h), 1)

    def draw_paused(self, surf):
        self.draw_playing(surf)
        overlay = pygame.Surface((NES_W, NES_H), pygame.SRCALPHA)
        overlay.fill((0,0,0,140))
        surf.blit(overlay, (0,0))
        draw_text(surf, "PAUSED", NES_W//2, NES_H//2 - 8, P['white'], 3, center=True)
        draw_text(surf, "P=RESUME  ESC=TITLE", NES_W//2, NES_H//2 + 24, P['gray'], 1, center=True)

    def draw_gameover(self, surf):
        surf.fill(P['black'])
        draw_text(surf, "GAME OVER", NES_W//2, NES_H//2 - 16, P['red'], 3, center=True)
        draw_text(surf, f"FINAL SCORE: {self.score:06d}", NES_W//2, NES_H//2 + 12, P['white'], 1, center=True)
        if self.card_timer > 60:
            draw_text(surf, "PRESS ANY KEY", NES_W//2, NES_H//2 + 30, P['yellow'], 1, center=True)

    def draw_victory(self, surf):
        surf.fill(P['black'])
        draw_text(surf, "CONGRATULATIONS!", NES_W//2, 60, P['yellow'], 2, center=True)
        draw_text(surf, "YOU SAVED THE KINGDOM", NES_W//2, 90, P['white'], 1, center=True)
        draw_text(surf, f"SCORE: {self.score:06d}", NES_W//2, 115, P['white'], 2, center=True)
        # princess
        surf.blit(ASSETS['princess'], (NES_W//2 - 8, 140))
        draw_text(surf, "THANK YOU MARIO!", NES_W//2, 180, P['pink'], 1, center=True)
        draw_text(surf, "OUR QUEST IS OVER", NES_W//2, 195, P['pink'], 1, center=True)
        draw_text(surf, "MEOW :3", NES_W//2, 215, P['lgreen'], 1, center=True)
        if self.victory_timer > 60:
            draw_text(surf, "PRESS ANY KEY", NES_W//2, 230, P['yellow'], 1, center=True)

    def draw(self, surf):
        if self.state == STATE_TITLE:
            self.draw_title(surf)
        elif self.state == STATE_MENU:
            self.draw_menu(surf)
        elif self.state == STATE_HELP:
            self.draw_help(surf)
        elif self.state == STATE_ABOUT:
            self.draw_about(surf)
        elif self.state == STATE_WORLD_CARD:
            self.draw_world_card(surf)
        elif self.state == STATE_PLAYING:
            self.draw_playing(surf)
        elif self.state == STATE_PAUSED:
            self.draw_paused(surf)
        elif self.state == STATE_GAMEOVER:
            self.draw_gameover(surf)
        elif self.state == STATE_VICTORY:
            self.draw_victory(surf)


# ============================================================
#  MAIN
# ============================================================

def main():
    global snd_enabled, SFX
    pygame.init()
    snd_enabled = True
    try:
        pygame.mixer.pre_init(SR, -16, 2, 1024)
        pygame.mixer.init(SR, -16, 2, 1024)
        _init_music_channel()
        SFX = _build_sounds()
        global MUSIC
        MUSIC = _build_music_bank()
    except Exception as e:
        print(f"audio disabled: {e}")
        snd_enabled = False
        SFX = {}
        MUSIC = {}

    flags = pygame.SCALED
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
    pygame.display.set_caption("AC Holdings SMB14k Mac Port — SMB1 1-1..8-4 (FILES=OFF)")
    nes = pygame.Surface((NES_W, NES_H))
    clock = pygame.time.Clock()

    global ASSETS
    ASSETS = build_assets()

    game = Game()

    while True:
        events = []
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            events.append(ev)
        keys = pygame.key.get_pressed()
        game.update(keys, events)
        game.draw(nes)
        pygame.transform.scale(nes, (SCREEN_W, SCREEN_H), screen)
        pygame.display.flip()
        clock.tick(FAMICOM_FPS)


# expose globals for build_sounds reference
snd_enabled = False
SFX = {}

if __name__ == "__main__":
    main()
