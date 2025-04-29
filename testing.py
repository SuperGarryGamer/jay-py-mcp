import mcp2515 as can
import random
import time

def random_frame(extended: bool = False, remote: bool = False):
    id = random.random() * 0x1fffffff
    if not extended:
        id = id & 0x7fff
    data = []
    for i in range(random.random() * 8):
        data.append(random.random() * 255)

    return can.CAN_Frame(extended, remote, id, data)

def prettyprint_frame(frame):
    print(f"{"Extended " if frame.extended else ""}{"Remote " if frame.remote else ""}CAN Frame {hex(frame.id)}: {frame.data}")

def speedtest_tx(can_controller, num_frames):
    for i in range(num_frames):
        can_controller.queue_frame(random_frame())

    start = time.time()
    print("Start transmitting frames")
    can_controller.flush_tx_queue()
    while not can_controller.tx_queue.empty():
        pass
    elapsed = time.time() - start
    print(f"Transmitted {num_frames} frames in {int(elapsed * 10000)/10000} seconds")

def flush_rx(can_controller):
    count = 0
    while not can_controller.rx_queue.empty():
        prettyprint_frame(can_controller.rx_queue.get())
        count += 1
    print(f"Received {count} frames")