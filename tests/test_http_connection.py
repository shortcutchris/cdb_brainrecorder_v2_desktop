import errno
import socket
import ssl
import unittest
from unittest.mock import patch
from services import http_connection as net

class Socket:
    def __init__(self, family, *_):self.family=family;self.closed=False;self.timeout=None
    def setblocking(self, value):pass
    def bind(self, address):pass
    def connect_ex(self, endpoint):return 0 if self.family==socket.AF_INET else errno.EINPROGRESS
    def settimeout(self, value):self.timeout=value
    def close(self):self.closed=True

class ConnectionTests(unittest.TestCase):
    def setUp(self):net._CACHE.clear()
    def rows(self):return [(socket.AF_INET6,socket.SOCK_STREAM,6,'',('::1',443,0,0)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]
    def test_unresponsive_ipv6_falls_back_after_quarter_second_and_closes_loser(self):
        clock=[0.];sockets=[]
        class Selector:
            def register(self,*args):pass
            def select(self,delay):clock[0]+=delay;return []
            def close(self):pass
        def make(*args):s=Socket(*args);sockets.append(s);return s
        with patch.object(net,'resolve',return_value=self.rows()),patch.object(net.socket,'socket',side_effect=make),patch.object(net.selectors,'DefaultSelector',Selector),patch.object(net.time,'monotonic',side_effect=lambda:clock[0]):
            result=net.connect(('example.test',443),90)
        self.assertAlmostEqual(clock[0],.25)
        self.assertEqual(result.family,socket.AF_INET);self.assertEqual(result.timeout,90)
        self.assertTrue(sockets[0].closed);self.assertFalse(result.closed)

    def test_all_unreachable_addresses_are_bounded_and_closed(self):
        clock=[0.];sockets=[]
        class Selector:
            def register(self,*args):pass
            def select(self,delay):clock[0]+=delay;return []
            def close(self):pass
        def make(*args):s=Socket(*args);sockets.append(s);return s
        with patch.object(net,'resolve',return_value=self.rows()[:1]),patch.object(net.socket,'socket',side_effect=make),patch.object(net.selectors,'DefaultSelector',Selector),patch.object(net.time,'monotonic',side_effect=lambda:clock[0]):
            with self.assertRaises(TimeoutError):net.connect(('example.test',443),90)
        self.assertEqual(clock[0],10);self.assertTrue(all(s.closed for s in sockets))

    def test_dns_cache_is_short_lived_and_family_order_alternates(self):
        with patch.object(net.socket,'getaddrinfo',return_value=self.rows()) as resolve,patch.object(net.time,'monotonic',return_value=100):
            self.assertEqual(net.resolve(('example.test',443)),self.rows())
            net.resolve(('example.test',443));self.assertEqual(resolve.call_count,1)
        with patch.object(net.socket,'getaddrinfo',return_value=self.rows()) as resolve,patch.object(net.time,'monotonic',return_value=131):
            net.resolve(('example.test',443));resolve.assert_called_once()

    def test_tls_identity_and_certificate_validation_are_unchanged(self):
        conn=net.HTTPSConnection('example.test')
        self.assertTrue(conn._context.check_hostname)
        self.assertEqual(conn._context.verify_mode,ssl.CERT_REQUIRED)
        self.assertEqual(conn.host,'example.test')

    def test_real_local_tcp_and_read_timeout(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1',0));server.listen()
            with net.connect(server.getsockname(),2) as client:
                accepted,_=server.accept()
                with accepted:
                    self.assertEqual(client.gettimeout(),2)
                    client.sendall(b'hello');self.assertEqual(accepted.recv(5),b'hello')

    def test_missing_ipv6_support_still_tries_ipv4(self):
        original=socket.socket
        def make(family,*args,**kwargs):
            if family==socket.AF_INET6:raise OSError(errno.EAFNOSUPPORT,'IPv6 unavailable')
            return original(family,*args,**kwargs)
        with original() as server:
            server.bind(('127.0.0.1',0));server.listen()
            rows=self.rows();rows[1]=(socket.AF_INET,socket.SOCK_STREAM,6,'',server.getsockname())
            with patch.object(net,'resolve',return_value=rows),patch.object(net.socket,'socket',side_effect=make):
                with net.connect(('example.test',443),2):
                    accepted,_=server.accept();accepted.close()
