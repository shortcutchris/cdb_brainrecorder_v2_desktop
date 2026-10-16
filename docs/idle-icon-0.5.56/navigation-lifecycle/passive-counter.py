"""Bounded, read-only IPv4 loopback counter. Never persists headers or bodies."""
import collections
import json
import socket
import struct
import time
import urllib.request
from datetime import datetime, timezone

PATHS = {b'/': 'document', b'/microphone.js': 'microphone_script',
         b'/assets/play.svg': 'play_icon', b'/assets/pause.svg': 'pause_icon',
         b'/api/state': 'state', b'/api/wake/status': 'wake_status',
         b'/favicon.ico': 'favicon'}

def classify(packet):
    if len(packet) < 40 or packet[0] >> 4 != 4 or packet[9] != 6:
        return None
    ihl = (packet[0] & 15) * 4
    if ihl < 20 or len(packet) < ihl + 20:
        return None
    if packet[12:20] != b'\x7f\x00\x00\x01' * 2:
        return None
    if struct.unpack('!H', packet[6:8])[0] & 0x3fff:
        return None
    if struct.unpack('!H', packet[ihl+2:ihl+4])[0] != 8088:
        return None
    offset = (packet[ihl+12] >> 4) * 4
    if offset < 20:
        return None
    data = packet[ihl+offset:]
    line = data.split(b'\r\n', 1)[0]
    parts = line.split(b' ')
    if len(parts) != 3 or parts[0] != b'GET' or not parts[2].startswith(b'HTTP/1.'):
        return None
    return PATHS.get(parts[1], 'other_get')

def self_test():
    ip = bytearray(20); ip[0] = 0x45; ip[9] = 6; ip[12:20] = b'\x7f\x00\x00\x01'*2
    tcp = bytearray(20); tcp[2:4] = struct.pack('!H',8088); tcp[12] = 0x50
    p=bytes(ip+tcp)
    assert classify(p+b'GET /assets/play.svg HTTP/1.1\r\nSecret: not-logged') == 'play_icon'
    assert classify(p+b'GET /unknown?private=value HTTP/1.1\r\n') == 'other_get'
    assert classify(p+b'POST /api/live HTTP/1.1\r\n') is None
    assert classify(p[:30]) is None
    assert classify(p+b'GET /assets/play.svg') is None
    assert classify(p+b'HTTP/1.1 200 OK\r\n') is None

if __name__ == '__main__':
    self_test()
    sock=socket.socket(socket.AF_PACKET,socket.SOCK_DGRAM,socket.htons(0x0800))
    sock.bind(('lo',0)); sock.settimeout(.5)
    counts=collections.Counter(); start=time.monotonic()
    started=datetime.now(timezone.utc).isoformat()
    # Exactly one harmless known request proves this capture sees loopback HTTP.
    with urllib.request.urlopen('http://127.0.0.1:8088/favicon.ico',timeout=3) as r:
        validation_status=r.status
    try:
        while time.monotonic()-start < 45:
            try: packet,address=sock.recvfrom(512)
            except socket.timeout: continue
            if address[2] == socket.PACKET_OUTGOING: continue
            category=classify(packet)
            if category: counts[category]+=1
        packets,dropped=struct.unpack('II',sock.getsockopt(263,6,8))
    finally: sock.close()
    print(json.dumps({'started_at':started,'duration_seconds':time.monotonic()-start,
        'counts':dict(counts),'validation_request_status':validation_status,
        'validation_favicon_expected':1,'packet_statistics':{'packets':packets,'dropped':dropped},
        'stored_headers_or_bodies':False,'ipv4_loopback_only':True,
        'packet_reassembly':False,'pid_attribution':False,'self_tests_passed':True}))
