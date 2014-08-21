#!/usr/bin/env python3
#
# Simple script for benchmarking 
#
import argparse
import numpy
import random
import time
import zmq

def send_array(socket, A, flags=0, copy=True, track=False):
    """send a numpy array with metadata"""
    md = dict(
        dtype = str(A.dtype),
        shape = A.shape,
        timestamp = time.time()
    )
    socket.send_json(md, flags|zmq.SNDMORE)
    scoopTime = time.time()
    socket.send(A, flags, copy=copy, track=track)
    dropTime = time.time()
    return dropTime - scoopTime

def recv_array(socket, flags=0, copy=True, track=False):
    """recv a numpy array"""
    md = socket.recv_json(flags=flags)
    msg = socket.recv(flags=flags, copy=copy, track=track)
    buf = memoryview(msg)
    A = numpy.frombuffer(buf, dtype=md['dtype'])
    return md['timestamp'], A.reshape(md['shape'])

parser = argparse.ArgumentParser('image_transfer_zmq_benchmark.py')
parser.add_argument('mode', choices=['server', 'requester'])
parser.add_argument('imageCount', type=int)
parser.add_argument('URIs', nargs='+', metavar='URI')
args = parser.parse_args()
if args.imageCount <= 0:
    raise ValueError('imageCount must be > 0.')

context = zmq.Context()

if args.mode == 'server':
    socket = context.socket(zmq.REP)
    for URI in args.URIs:
        socket.bind(URI)
    images = [numpy.random.random_integers(0, 65535, (2560,1600)).astype(numpy.uint16) for i in range(args.imageCount)]
    servedCount = 0
    dishingIntervalsTotal = 0
    try:
        while True:
            random.shuffle(images)
            idx = 0
            while True:
                if socket.recv_string() == 'send an image':
                    dishingIntervalsTotal += send_array(socket, images[idx], copy=False, track=False)
                    servedCount += 1
                    idx += 1
                    if idx >= args.imageCount:
                        break
                else:
                    socket.send_string('These are not the droids you\'re looking for.')
    except KeyboardInterrupt:
        pass
    if servedCount == 0:
        print('\nDished out 0 images.  Not a one.')
    else:
        print('\nDished out ', servedCount, ' images.  Average time spent socket.send(..)ing: ', (dishingIntervalsTotal / servedCount) * 1000, 'ms.')
elif args.mode == 'requester':
    socket = context.socket(zmq.REQ)
    for URI in args.URIs:
        socket.connect(URI)
    reqSendIntervalsTotal = 0
    reqSendToTimestampIntervalsTotal = 0
    recvIntervalsTotal = 0
    timestampToRecvCompleteIntervalsTotal = 0
    receivedCount = 0
    try:
        for n in range(args.imageCount):
            reqTime = time.time()
            socket.send_string('send an image')
            repTime = time.time()
            timestamp, image = recv_array(socket, copy=False, track=True)
            finishTime = time.time()

            reqSendIntervalsTotal += repTime - reqTime
            reqSendToTimestampIntervalsTotal += timestamp - reqTime
            recvIntervalsTotal += finishTime - repTime
            timestampToRecvCompleteIntervalsTotal = finishTime - timestamp
            receivedCount += 1
    except KeyboardInterrupt:
        pass
    if receivedCount == 0:
        print('\nFor 0 images, average\n\tI\'VE GOT NOTHING')
    else:
        print('\nFor', receivedCount, 'images, average ')
        print('\trequest sending interval = \n\t\t', 1000 * (reqSendIntervalsTotal / receivedCount), 'ms')
        print('\trequest sending to reply sending interval = \n\t\t', 1000 * (reqSendToTimestampIntervalsTotal / receivedCount), 'ms')
        print('\treply receiving interval = \n\t\t', 1000 * (recvIntervalsTotal / receivedCount), 'ms')
        print('\treply sending to reply received interval = \n\t\t', 1000 * (timestampToRecvCompleteIntervalsTotal / receivedCount), 'ms')
