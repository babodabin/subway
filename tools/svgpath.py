# -*- coding: utf-8 -*-
"""SVG path d 속성을 점 목록(폴리라인)으로 펼친다. 필요한 명령만 지원."""
import math
import re

TOK = re.compile(r"[MmLlHhVvCcSsAaZz]|-?\d*\.?\d+(?:e[-+]?\d+)?")


def _arc(x0, y0, rx, ry, rot, large, sweep, x, y, steps=16):
    """끝점 표기 호 → 점 목록 (SVG 명세 F.6.5)."""
    if rx == 0 or ry == 0:
        return [(x, y)]
    phi = math.radians(rot)
    cp, sp = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x0 - x) / 2.0, (y0 - y) / 2.0
    x1p, y1p = cp * dx2 + sp * dy2, -sp * dx2 + cp * dy2
    rx, ry = abs(rx), abs(ry)
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x0 + x) / 2.0, sp * cxp + cp * cyp + (y0 + y) / 2.0

    def ang(ux, uy, vx, vy):
        d = math.hypot(ux, uy) * math.hypot(vx, vy)
        if d == 0:
            return 0.0
        c = max(-1.0, min(1.0, (ux * vx + uy * vy) / d))
        a = math.acos(c)
        return -a if ux * vy - uy * vx < 0 else a

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    pts = []
    for i in range(1, steps + 1):
        t = t1 + dt * i / steps
        pts.append(
            (
                cx + rx * math.cos(t) * cp - ry * math.sin(t) * sp,
                cy + rx * math.cos(t) * sp + ry * math.sin(t) * cp,
            )
        )
    return pts


def _bez(p0, p1, p2, p3, steps=12):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append(
            (
                u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1],
            )
        )
    return out


def flatten(d):
    """d → [폴리라인, ...]. M 이 나올 때마다 새 폴리라인."""
    toks = TOK.findall(d)
    i = 0
    subs, cur = [], []
    x = y = sx = sy = 0.0
    px = py = None  # 직전 제어점 (S/s 용)
    cmd = None
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
        n = lambda k: float(toks[i + k])
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            if cur:
                subs.append(cur)
            x, y = (x + n(0), y + n(1)) if rel else (n(0), n(1))
            sx, sy = x, y
            cur = [(x, y)]
            i += 2
            cmd = "l" if rel else "L"
        elif c == "L":
            x, y = (x + n(0), y + n(1)) if rel else (n(0), n(1))
            cur.append((x, y))
            i += 2
        elif c == "H":
            x = x + n(0) if rel else n(0)
            cur.append((x, y))
            i += 1
        elif c == "V":
            y = y + n(0) if rel else n(0)
            cur.append((x, y))
            i += 1
        elif c in "CS":
            if c == "C":
                p1 = (x + n(0), y + n(1)) if rel else (n(0), n(1))
                p2 = (x + n(2), y + n(3)) if rel else (n(2), n(3))
                p3 = (x + n(4), y + n(5)) if rel else (n(4), n(5))
                i += 6
            else:
                p1 = (2 * x - px, 2 * y - py) if px is not None else (x, y)
                p2 = (x + n(0), y + n(1)) if rel else (n(0), n(1))
                p3 = (x + n(2), y + n(3)) if rel else (n(2), n(3))
                i += 4
            cur.extend(_bez((x, y), p1, p2, p3))
            px, py = p2
            x, y = p3
            continue
        elif c == "A":
            rx, ry, rot, la, sw = n(0), n(1), n(2), int(float(toks[i + 3])), int(float(toks[i + 4]))
            nx, ny = (x + n(5), y + n(6)) if rel else (n(5), n(6))
            cur.extend(_arc(x, y, rx, ry, rot, la, sw, nx, ny))
            x, y = nx, ny
            i += 7
        elif c == "Z":
            cur.append((sx, sy))
            x, y = sx, sy
            i += 1
        else:
            raise ValueError("모르는 명령 %r" % cmd)
        if c not in "CS":
            px = py = None
    if cur:
        subs.append(cur)
    return subs


def project(poly, x, y):
    """점을 폴리라인에 투영. (누적거리, 수직거리) 반환."""
    best = (0.0, 1e18)
    acc = 0.0
    for i in range(len(poly) - 1):
        ax, ay = poly[i]
        bx, by = poly[i + 1]
        dx, dy = bx - ax, by - ay
        seg = math.hypot(dx, dy)
        if seg == 0:
            continue
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (seg * seg)))
        d = math.hypot(ax + t * dx - x, ay + t * dy - y)
        if d < best[1]:
            best = (acc + t * seg, d)
        acc += seg
    return best
