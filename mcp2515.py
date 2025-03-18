import RPi.GPIO as GPIO
import spidev
import queue


class MCP2515:
    def __init__(self, interrupt_pin=25):
        self.spi = spidev.SpiDev()
        self.spi.open(0,0)
        self.spi.max_speed_hz = 10_000_000 # MCP2515 is rated for 10 MHz SPI
        self.spi.mode = 0b00
        self.reset()
        self.set_mode(0)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(interrupt_pin, GPIO.IN)
        GPIO.add_event_detect(interrupt_pin, GPIO.FALLING, callback=self._on_interrupt, bouncetime=50)
        self.set_register(0x2b, 0x03)


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
    
    def _on_interrupt(self):
        """Interrupt handler, do not call"""
        
class CAN_Frame:  
    def __init__(self, extended: bool, remote: bool, id: int, data: list[int]):
        if id > 0x1fffffff or (not extended and id > 0x7ff):
            raise OverflowError
        
        if len(data) > 8:
            raise ValueError
        
        self.extended = extended
        self.remote = remote
        self.id = id
        self.data = data

    def __init__(self, raw_data: list[int]):
        pass
        
