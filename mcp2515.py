import RPi.GPIO as GPIO
import spidev
import queue


class MCP2515:
    def __init__(self, interrupt_pin=25):
        self.rx_queue = queue.Queue()
        self.tx_queue = queue.Queue()
        self.spi = spidev.SpiDev()
        self.spi.open(0,0)
        self.spi.max_speed_hz = 10_000_000 # MCP2515 is rated for 10 MHz SPI
        self.spi.mode = 0b00
        self.reset()
        self.set_mode(0)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(interrupt_pin, GPIO.IN)
        GPIO.add_event_detect(interrupt_pin, GPIO.FALLING, callback=self._on_interrupt, bouncetime=50)
        self.set_register(0x2b, 0x1f)


    def reset(self):
        """Resets internal registers to default, enters configuration mode"""
        self.spi.xfer([0xc0])

    def set_mode(self, mode: int):
        """Sets MCP2515 operation mode. 
        
        Possible values for mode:
        0: Normal mode
        1: Sleep mode
        2: Loopback mode
        3: Listen-only mode
        4: Configuration mode"""

        if mode < 0 or mode > 4:
            raise ValueError
        
        canctrl = self.get_register(0xf0)
        canctrl = canctrl & 0b00011111 # Clear top 3 bits
        canctrl += (mode << 5) # Put mode in top 3 bits
        self.set_register(0xf0, canctrl)

    def set_register(self, address: int, value: int):
        """Sets register at address to value. Takes 8-bit ints for both."""
        if address < 0 or address > 255 or value < 0 or value > 255:
            raise OverflowError
        
        self.spi.xfer([0x02, address, value])
    
    def set_registers(self, start_address: int, values: list[int]):
        """Sets registers starting at start_address to values"""
        if start_address < 0 or start_address > 255:
            raise OverflowError
        
        self.spi.xfer([0x02, start_address] + values)

    def get_register(self, address: int):
        """Returns the value of register at address"""
        if address < 0 or address > 255:
            raise OverflowError
        
        return self.spi.xfer([0x03, address, 0x00])[2]
    
    def get_status(self):
        """Returns MCP2515 Interrupt status flags"""
        return self.spi.xfer([0xa0, 0x00])[1]
    
    def _on_interrupt(self):
        """Interrupt handler, do not call"""
        flags = self.get_status()

        if flags & 0b00000001 != 0: # RXB0 Full
            raw_data = self.spi.xfer([0x90, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])[1:]
            self.rx_queue.put(CAN_Frame(raw_data))
        if flags & 0b00000010 != 0: # RXB1 Full
            raw_data = self.spi.xfer([0x94, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])[1:]
            self.rx_queue.put(CAN_Frame(raw_data))
        if not self.tx_queue.empty():
            if   flags & 0b00001000 != 0: # TXB0 Clear
                self.set_registers(0x31, self.tx_queue.get().serialize())
                self.spi.xfer([0x81])
            elif flags & 0b00100000 != 0: # TXB1 Clear
                self.set_registers(0x41, self.tx_queue.get().serialize())
                self.spi.xfer([0x82])
            elif flags & 0b10000000 != 0: # TXB2 Clear
                self.set_registers(0x51, self.tx_queue.get().serialize())
                self.spi.xfer([0x84])

        
class CAN_Frame:  
    def __init__(self, extended: bool, remote: bool, id: int, data: list[int]):
        """Initialize frame with given parameters"""
        if id > 0x1fffffff or (not extended and id > 0x7ff):
            raise OverflowError
        
        if len(data) > 8:
            raise ValueError
        
        self.extended = extended
        self.remote = remote
        self.id = id
        self.data = data

    def __init__(self, raw_data: list[int]):
        """Initialize frame from raw data from RXB0~1 registers"""
        if raw_data[1] & 0b00001000 != 0:
            self.extended = True
        if raw_data[4] & 0b01000000 != 0:
            self.remote = True

        self.id = raw_data[0] << 3 + (raw_data[1] >> 5)
        if self.extended:
            self.id = (self.id << 18) + (raw_data[1] << 21) + (raw_data[2] << 8) + raw_data[3]
        
        self.data = []
        for i in range(raw_data[4] & 0b00001111):
            self.data.append(raw_data[5 + i])

    def serialize(self):
        """Returns sequence of bytes representing the frame that can be written directly to TXB0~2 registers"""
        serialized = [0, 0, 0, 0, 0]
        if self.extended:
            serialized[0] = self.id >> 21
            serialized[1] = ((self.id >> 18) & 0b111) << 5 + 8 + ((self.id >> 16) & 0b11) # + 8 sets the EXIDE bit
            serialized[2] = (self.id >> 8) & 0xFF
            serialized[3] = self.id & 0xFF
            serialized[4] = len(self.data)
            if self.remote:
                serialized[4] += 64 # Set the RTR bit

        serialized += self.data
        return serialized

        
