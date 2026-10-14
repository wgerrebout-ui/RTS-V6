"""Réseau téléphone à téléphone (Wi-Fi / partage de connexion) : TCP, messages JSON, un par ligne."""
import json
import queue
import socket
import threading

PORT = 5555


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


class Peer:
    def __init__(self, sock):
        self.sock = sock
        self.inbox = queue.Queue()
        self.alive = True
        self.lock = threading.Lock()
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass
        sock.settimeout(None)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        buf = b''
        try:
            while self.alive:
                data = self.sock.recv(65536)
                if not data:
                    break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    if line:
                        try:
                            self.inbox.put(json.loads(line))
                        except ValueError:
                            pass
        except Exception:
            pass
        self.alive = False

    def send(self, msg):
        if not self.alive:
            return False
        try:
            data = (json.dumps(msg, separators=(',', ':')) + '\n').encode()
            with self.lock:
                self.sock.sendall(data)
            return True
        except Exception:
            self.alive = False
            return False

    def poll(self):
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    def close(self):
        self.alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


class Server:
    """Salon de l'hôte : attend un seul joueur."""

    def __init__(self, port=PORT):
        self.peer = None
        self.error = None
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.srv.bind(('', port))
            self.srv.listen(1)
            threading.Thread(target=self._accept, daemon=True).start()
        except Exception as e:
            self.error = str(e)

    def _accept(self):
        try:
            conn, _ = self.srv.accept()
            self.peer = Peer(conn)
        except Exception as e:
            if self.peer is None:
                self.error = str(e)

    def close(self):
        try:
            self.srv.close()
        except Exception:
            pass


class Connector:
    """Connexion du joueur invité (dans un thread pour ne pas figer l'écran)."""

    def __init__(self, ip, port=PORT, timeout=6.0):
        self.peer = None
        self.error = None
        self.done = False
        threading.Thread(target=self._run, args=(ip.strip(), port, timeout), daemon=True).start()

    def _run(self, ip, port, timeout):
        try:
            s = socket.create_connection((ip, port), timeout=timeout)
            self.peer = Peer(s)
        except Exception as e:
            self.error = str(e)
        self.done = True
