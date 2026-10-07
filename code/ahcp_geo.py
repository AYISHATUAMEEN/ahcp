"""Minimal point-in-polygon tract assignment with no GIS dependencies (numpy only).

Reads an ESRI polygon shapefile + DBF straight from the Census cartographic-boundary zip, builds a coarse grid
index over tract bounding boxes, and assigns each point the tract whose polygon contains it (even-odd rule
across all rings, so holes are handled). Points in no polygon (shoreline generalization, boundary slivers) get
the nearest tract within `snap_m` metres and are flagged method='nearest_vertex'.
"""
import io, struct, zipfile, math
from collections import defaultdict
import numpy as np

CELL = 0.1  # degrees


def read_dbf(buf, fields):
    n, hlen, rlen = struct.unpack("<IHH", buf[4:12])
    cols, off, pos = [], 1, 32
    while buf[pos] != 0x0D:
        name = buf[pos:pos + 11].split(b"\x00")[0].decode()
        ln = buf[pos + 16]
        cols.append((name, off, ln)); off += ln; pos += 32
    want = [(nm, o, l) for nm, o, l in cols if nm in fields]
    out = {nm: [] for nm, _, _ in want}
    for i in range(n):
        rec = buf[hlen + i * rlen: hlen + (i + 1) * rlen]
        for nm, o, l in want:
            out[nm].append(rec[o:o + l].decode("latin-1").strip())
    return out


def read_shp_polygons(buf):
    """Yield (bbox, [ring arrays]) per record; None for null shapes."""
    pos, end = 100, len(buf)
    while pos < end:
        clen = struct.unpack(">i", buf[pos + 4:pos + 8])[0] * 2
        rec = buf[pos + 8:pos + 8 + clen]; pos += 8 + clen
        st = struct.unpack("<i", rec[:4])[0]
        if st == 0:
            yield None; continue
        bbox = struct.unpack("<4d", rec[4:36])
        nparts, npts = struct.unpack("<2i", rec[36:44])
        parts = list(struct.unpack("<%di" % nparts, rec[44:44 + 4 * nparts])) + [npts]
        pts = np.frombuffer(rec, dtype="<f8", count=npts * 2, offset=44 + 4 * nparts).reshape(-1, 2)
        yield bbox, [pts[parts[i]:parts[i + 1]] for i in range(nparts)]


class TractIndex:
    def __init__(self, zip_path):
        z = zipfile.ZipFile(zip_path)
        shp = [n for n in z.namelist() if n.endswith(".shp")][0]
        dbf = read_dbf(z.read(shp[:-4] + ".dbf"), {"GEOID"})
        self.geoid, self.bbox, self.rings = [], [], []
        for gid, rec in zip(dbf["GEOID"], read_shp_polygons(z.read(shp))):
            if rec is None: continue
            self.geoid.append(gid); self.bbox.append(rec[0]); self.rings.append(rec[1])
        self.grid = defaultdict(list)
        for i, (x0, y0, x1, y1) in enumerate(self.bbox):
            for cx in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
                for cy in range(int(math.floor(y0 / CELL)), int(math.floor(y1 / CELL)) + 1):
                    self.grid[(cx, cy)].append(i)

    @staticmethod
    def _inside(rings, x, y):
        c = False
        for r in rings:
            xi, yi = r[:-1, 0], r[:-1, 1]; xj, yj = r[1:, 0], r[1:, 1]
            cond = (yi > y) != (yj > y)
            if cond.any():
                xint = (xj[cond] - xi[cond]) * (y - yi[cond]) / (yj[cond] - yi[cond]) + xi[cond]
                if (np.count_nonzero(x < xint) % 2) == 1: c = not c
        return c

    def locate(self, lon, lat, snap_m=1000.0):
        """Return (geoid, method, distance_m). method in {'contains','nearest_vertex',''}"""
        cx, cy = int(math.floor(lon / CELL)), int(math.floor(lat / CELL))
        for i in self.grid.get((cx, cy), ()):
            x0, y0, x1, y1 = self.bbox[i]
            if x0 <= lon <= x1 and y0 <= lat <= y1 and self._inside(self.rings[i], lon, lat):
                return self.geoid[i], "contains", 0.0
        best, bi = None, None
        kx = 111320.0 * math.cos(math.radians(lat)); ky = 110540.0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in self.grid.get((cx + dx, cy + dy), ()):
                    for r in self.rings[i]:
                        dd = np.min(((r[:, 0] - lon) * kx) ** 2 + ((r[:, 1] - lat) * ky) ** 2)
                        if best is None or dd < best: best, bi = dd, i
        if best is not None and math.sqrt(best) <= snap_m:
            return self.geoid[bi], "nearest_vertex", round(math.sqrt(best), 1)
        return "", "", float("nan")
