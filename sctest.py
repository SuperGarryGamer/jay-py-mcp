import can
import random
import time
import hashlib

INTERFACE = "socketcan"
CHANNEL   = "can0"

def test_send(frame_count, send_delay):
    
    # Generate random frames
    frames = []
    checksum_raw = []

    for i in range(frame_count-1):
        arb_id = int(random.random() * 0x7FF)
        frame_data = [int(random.random() * 0xFF) for i in range(8)]
        frames.append(can.Message(is_extended_id=False, arbitration_id=arb_id, data=frame_data))
        checksum_raw += frame_data
    
    # Distinct end frame (random.random() < 1 -> int(r.r() * 0xFF) != 0xFF)
    frames.append(can.Message(is_extended_id=False, arbitration_id=0x7FF, data=[0xFF for i in range(8)]))
    checksum_raw += [0xFF for i in range(8)]
    checksum = hashlib.md5(bytes(checksum_raw)) 

    time_spent_waiting = 0

    with can.Bus(CHANNEL, INTERFACE) as bus:

        # Ping :3
        ping_msg = can.Message(is_extended_id=False, arbitration_id=0x007, data=[80, 105, 110, 103])
        ping_start = time.time()
        bus.send(ping_msg)
        bus.recv()
        ping_end = time.time()
        print(f"Round trip time: {ping_end - ping_start} seconds")
        time.sleep(0.5)
        print(f"Sending {frame_count} frames")
        start = time.time()
        for frame in frames:
            try:
                bus.send(frame)
            except can.exceptions.CanOperationError:
                wait_start = time.time()
                sent = False
                while not sent:
                    try:
                        time.sleep(0.0005)
                        bus.send(frame)
                        sent = True
                    except can.exceptions.CanOperationError:
                        pass # :)
                wait_stop = time.time()
                time_spent_waiting += (wait_stop - wait_start)
                
            time.sleep(send_delay)
        end = time.time()
        print(f"Sent {frame_count} frames in {end - start} seconds")
        print(f"Spent {time_spent_waiting} seconds waiting for TX buffer to clear (average {time_spent_waiting/frame_count} per frame)")
        
        print(f"Nominal TX bitrate:   {int((111*frame_count)/(end - start))} bits/second") # 1 full standard-length ID frame is 111 bits
        print(f"Effective TX bitrate: {int((64*frame_count)/(end - start))} bits/second") # 1 full frame transmits 64 bits of useful
    
        rx_checksum_high = bus.recv()
        rx_checksum_low  = bus.recv()
        rx_checksum      = bytes() + rx_checksum_high.data + rx_checksum_low.data
        print(f"True checksum: {checksum.hexdigest()}")
        print(f"Received checksum: {rx_checksum.hex()}")
        if checksum.digest() == rx_checksum:
            print("Checksums match, PASS")
            return True
        else:
            print("Checksum mismatch, FAIL")
            return False

def test_receive():
    received = []
    with can.Bus(CHANNEL, INTERFACE) as bus:

        # Wait for ping
        print("Listening...")
        bus.recv()
        bus.send(can.Message(is_extended_id=False, arbitration_id=0x123, data=[80, 111, 110, 103]))
        print("Received ping, listening for transmission...")
        # Bulk receive
        done = False
        while not done:
            received.append(bus.recv())
            if received[-1].arbitration_id == 0x7FF:
                done = True
        print(f"Received {len(received)} frames")
        
        # Calculate checksum
        checksum_raw = bytes()
        for frame in received:
            checksum_raw += bytes(frame.data)
        checksum = hashlib.md5(checksum_raw).digest()
        print(f"MD5 Checksum: {checksum.hex()}")
        
        # Send checksum
        bus.send(can.Message(arbitration_id=0x01, data=checksum[:8]))
        time.sleep(0.1)
        bus.send(can.Message(arbitration_id=0x02, data=checksum[8:]))
