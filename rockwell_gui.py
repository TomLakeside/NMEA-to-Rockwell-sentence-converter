#!/usr/bin/env python3
"""
Toont de Rockwell-zin (255/129, bericht 103) in een tkinter-venster en ververst
de waarden bij elke ontvangen zin.

Heeft rockwell_decode.py nodig in dezelfde map.

Gebruik:
  python3 rockwell_gui.py /dev/tty.usbserial-11230
  python3 rockwell_gui.py /dev/tty.usbserial-11230 --baud 9600
  python3 rockwell_gui.py --file capture.bin        # speelt een opname af, 1 zin per seconde
"""
import math
import time
import queue
import threading
import argparse
import tkinter as tk
from tkinter import ttk

from rockwell_decode import Reader, next_message, u16, s16, u32, fp, efp, hms

STALE_AFTER = 3.0          # seconden zonder nieuwe zin voordat "geen data" getoond wordt
INVALID_AFTER = 15.0       # seconden zonder nieuwe zin voordat de positiestatus op ongeldig gaat

GROUPS = [
    ('Links', [
        ('Tijd', [
            ('gpsweek', 'GPS-week'),
            ('tow', 'GPS-tijd in week'),
            ('utcvalid', 'UTC geldig'),
            ('datum', 'Datum (UTC)'),
            ('tijd', 'Tijd (UTC)'),
            ('settime', 'Tijd sinds start'),
        ]),
        ('Positie', [
            ('lat', 'Breedtegraad'),
            ('lon', 'Lengtegraad'),
            ('hoogte', 'Hoogte'),
            ('ecef', 'ECEF X, Y, Z'),
        ]),
        ('Snelheid', [
            ('sog', 'Snelheid / koers'),
            ('vel', 'Oost, Noord, Omhoog'),
        ]),
    ]),
    ('Rechts', [
        ('Nauwkeurigheid', [
            ('dop', 'HDOP / VDOP / PDOP'),
            ('tdop', 'TDOP / GDOP'),
            ('err', 'Verwachte fouten'),
        ]),
        ('Ontvanger', [
            ('status', 'Status'),
        ]),
    ]),
]


def decode(m):
    """Zet een 128-bytes zin (bericht 103) om in tekstwaarden en een lijst kanalen."""
    v = {}
    v['gpsweek'] = '%d' % s16(m, 16)
    v['tow'] = '%.2f s' % efp(m, 10)
    v['utcvalid'] = 'ja' if u16(m, 18) else 'nee'
    v['datum'] = '%04d-%02d-%02d' % (s16(m, 30), s16(m, 28), s16(m, 26))
    v['tijd'] = hms(efp(m, 20))
    v['settime'] = '%.2f s' % (u32(m, 32) * 0.02)

    lat, lon = math.degrees(efp(m, 66)), math.degrees(efp(m, 72))
    v['lat'] = '%.6f\u00b0 %s' % (abs(lat), 'N' if lat >= 0 else 'Z')
    v['lon'] = '%.6f\u00b0 %s' % (abs(lon), 'O' if lon >= 0 else 'W')
    v['hoogte'] = '%.1f m' % fp(m, 78)
    v['ecef'] = '%.1f  %.1f  %.1f m' % (efp(m, 36), efp(m, 42), efp(m, 48))

    ve, vn, vu = fp(m, 54), fp(m, 58), fp(m, 62)
    sog = math.hypot(ve, vn) * 3600 / 1852
    cog = (math.degrees(math.atan2(ve, vn)) + 360) % 360
    v['sog'] = '%.1f kn / %.1f\u00b0' % (sog, cog)
    v['vel'] = '%.2f  %.2f  %.2f m/s' % (ve, vn, vu)

    v['dop'] = '%.2f  %.2f  %.2f' % (s16(m, 82) / 100, s16(m, 84) / 100, s16(m, 86) / 100)
    v['tdop'] = '%.2f  %.2f' % (s16(m, 88) / 100, s16(m, 90) / 100)
    v['err'] = 'EHPE %d  EVPE %d  ETE %d  EHVE %.2f m/s' % (
        s16(m, 112), s16(m, 114), s16(m, 116), s16(m, 118) * 0.01)
    status = u16(m, 124)
    v['status'] = '0x%04x: positie geldig %s, %d satellieten' % (
        status, 'ja' if status & 8 else 'nee', (status >> 4) & 7)

    channels = []
    for i in range(5):
        state, snr = u16(m, 92 + 4 * i), u16(m, 94 + 4 * i)
        if state == 0:
            channels.append(('%d' % (i + 1), '-', '-', 'ongebruikt'))
        else:
            channels.append(('%d' % ((state >> 12) & 7), '%d' % (state & 0x1F),
                             '%d' % (snr >> 8), '0x%04x' % state))
    return v, channels


class App:
    def __init__(self, root, args):
        self.root = root
        self.q = queue.Queue()
        self.count = 0
        self.errors = 0
        self.last = None            # tijdstip van de laatste zin
        self.vars = {}

        root.title('Rockwell zin 103')
        mono = ('Menlo', 12) if root.tk.call('tk', 'windowingsystem') == 'aqua' else ('Courier', 11)

        body = ttk.Frame(root, padding=8)
        body.grid(row=0, column=0, sticky='nsew')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        for col, (_, frames) in enumerate(GROUPS):
            column = ttk.Frame(body)
            column.grid(row=0, column=col, sticky='nsew', padx=4)
            body.columnconfigure(col, weight=1)
            for title, fields in frames:
                box = ttk.LabelFrame(column, text=title, padding=6)
                box.pack(fill='x', pady=4)
                for r, (key, label) in enumerate(fields):
                    ttk.Label(box, text=label).grid(row=r, column=0, sticky='w', padx=(0, 12))
                    var = tk.StringVar(value='-')
                    self.vars[key] = var
                    ttk.Label(box, textvariable=var, font=mono).grid(row=r, column=1, sticky='w')

            if col == 1:
                box = ttk.LabelFrame(column, text='Satellieten', padding=6)
                box.pack(fill='x', pady=4)
                cols = ('kanaal', 'prn', 'snr', 'status')
                self.tree = ttk.Treeview(box, columns=cols, show='headings', height=5)
                for c, w in zip(cols, (60, 60, 60, 100)):
                    self.tree.heading(c, text=c.upper() if c in ('prn', 'snr') else c.capitalize())
                    self.tree.column(c, width=w, anchor='center')
                self.tree.pack(fill='x')
                self.rows = [self.tree.insert('', 'end', values=('-', '-', '-', '-')) for _ in range(5)]

        self.status = tk.StringVar(value='Wachten op data...')
        ttk.Label(root, textvariable=self.status, anchor='w', padding=(8, 2)).grid(
            row=1, column=0, sticky='ew')

        threading.Thread(target=self.worker, args=(args,), daemon=True).start()
        self.poll()

    # --- thread: leest de seriele poort / het bestand, zet zinnen in de wachtrij ---
    def worker(self, args):
        try:
            if args.file:
                rd = Reader(open(args.file, 'rb'), True)
            else:
                import serial
                port = serial.Serial(args.port, args.baud, bytesize=8,
                                     parity=serial.PARITY_ODD, stopbits=1, timeout=1)
                rd = Reader(port, False)
            while True:
                m = next_message(rd, lambda t: self.q.put(('err', t)))
                self.q.put(('msg', m))
                if args.file:
                    time.sleep(1)
        except EOFError:
            self.q.put(('status', 'Einde van het bestand'))
        except Exception as e:
            self.q.put(('status', 'Fout: %s' % e))

    # --- hoofdthread: haalt zinnen uit de wachtrij en ververst het scherm ---
    def poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == 'msg':
                    self.show(payload)
                elif kind == 'err':
                    self.errors += 1
                else:
                    self.status.set(payload)
        except queue.Empty:
            pass

        if self.last is not None:
            age = time.time() - self.last
            if age > STALE_AFTER:
                self.status.set('Geen nieuwe data sinds %.0f s  |  zinnen: %d  controlesomfouten: %d'
                                % (age, self.count, self.errors))
            if age > INVALID_AFTER:
                # te lang niets ontvangen: de laatste positie is niet meer betrouwbaar
                self.vars['status'].set('positie ongeldig: geen zin sinds %.0f s' % age)
        self.root.after(100, self.poll)

    def show(self, m):
        self.count += 1
        self.last = time.time()
        if u16(m, 2) != 103 or u16(m, 4) != 58:
            self.status.set('Bericht %d (onbekend formaat)  |  zinnen: %d' % (u16(m, 2), self.count))
            return
        values, channels = decode(m)
        for key, text in values.items():
            self.vars[key].set(text)
        for row, vals in zip(self.rows, channels):
            self.tree.item(row, values=vals)
        self.status.set('Laatste zin %s  |  zinnen: %d  controlesomfouten: %d'
                        % (time.strftime('%H:%M:%S'), self.count, self.errors))


def main():
    ap = argparse.ArgumentParser(description='Rockwell zin 103 in een tkinter-venster')
    ap.add_argument('port', nargs='?', default='/dev/tty.usbserial-120', help='seriele poort')
    ap.add_argument('--baud', type=int, default=9600)
    ap.add_argument('--file', help='speel een binaire opname af in plaats van een poort')
    args = ap.parse_args()

    root = tk.Tk()
    App(root, args)
    root.mainloop()


if __name__ == '__main__':
    main()
