"""Recording TCP relay: forwards every byte between a client and the backend unchanged and appends the
client->backend bytes to a log (one record per chunk: '@@ <conn> <len>\n' + bytes). It never alters traffic,
so the client sees exactly the backend it would see without the relay.
Usage: python tap.py <listen_port> <upstream_port> <logfile>"""
import socket, sys, threading, itertools
LP, UP, LOG = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
lock = threading.Lock(); ids = itertools.count(1); logf = open(LOG, "ab", buffering=0)
def pipe(src, dst, cid=None):
    try:
        while True:
            d = src.recv(65536)
            if not d: break
            if cid is not None:
                with lock: logf.write(b"@@ %d %d\n" % (cid, len(d)) + d)
            dst.sendall(d)
    except OSError: pass
    finally:
        for s in (src, dst):
            try: s.shutdown(socket.SHUT_RDWR)
            except OSError: pass
def serve(c):
    u = socket.create_connection(("127.0.0.1", UP)); cid = next(ids)
    threading.Thread(target=pipe, args=(u, c), daemon=True).start()
    pipe(c, u, cid)
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", LP)); srv.listen(64)
while True:
    c, _ = srv.accept(); threading.Thread(target=serve, args=(c,), daemon=True).start()
