import crcengine
import serial
import binascii
import time
import serial.rs485
import sys

baud = 4800
stop_bits = serial.STOPBITS_ONE
parity=serial.PARITY_NONE
one_char_wait = (8 + (1 if stop_bits == serial.STOPBITS_ONE else 2) + (0 if parity == serial.PARITY_NONE else 1)) / 4800
crc = crcengine.create(0x01, 8, 0xff, False, False, "", 0)

def create (device):
    ser = serial.rs485.RS485(port=device,baudrate=4800, bytesize=serial.EIGHTBITS, parity=parity, stopbits=stop_bits, timeout=one_char_wait*0.2)
    return protocol (ser)

class protocol:
    def __init__ (self, ser):
        self.before_read_success_time = time.clock_gettime(time.CLOCK_MONOTONIC)
        self.last_byte_time = time.clock_gettime(time.CLOCK_MONOTONIC)
        self.last_prev_byte_time = time.clock_gettime(time.CLOCK_MONOTONIC)
        self.first_byte_time = time.clock_gettime(time.CLOCK_MONOTONIC)
        self.last_write_time = time.clock_gettime(time.CLOCK_MONOTONIC)
        self.msg = b''
        self.timeout = True
        self.ser = ser
        self.send_buffer = []

    def __handle_msg (self, msg, handler):
        if crc(msg) != 0:
            #print ("Error doing CRC check for ", msg)
            j = 0
            for i in range (2,len(msg)-1):
                if i - j > 1: # at least two bytes
                    new_msg = msg[j:i]
                    if crc(new_msg) == 0: # check current slice
                        self.__handle_msg (new_msg, handler)
                        j = i # next starts at open-ended index
            return

        handler (msg[:-1])

    def loop (self, handle_msg):
        now = time.clock_gettime(time.CLOCK_MONOTONIC)
        if not self.timeout:
            self.before_read_success_time = now
        b = self.ser.read(1)
        now = time.clock_gettime(time.CLOCK_MONOTONIC)

        self.timeout = (len(b) == 0)

        if not self.timeout and len(self.msg) == 0:
            # this is called when we did read something, but msg is still empty
            # meaning this is the first character from the message. So we time it
            self.first_byte_time = now
        elif not self.timeout:
            self.last_byte_time = now

        if (now - self.before_read_success_time) > one_char_wait*2:
            if len(self.msg) > 1:
                self.__handle_msg (self.msg, handle_msg)
                self.last_prev_byte_time = self.last_byte_time
            if not self.timeout: # start next message
                #print('started new message')
                self.first_byte_time = now
                self.msg = b
            else:
                self.msg = b''
        elif not self.timeout:
            self.msg += b
            #if len(msg) == 1:
            #    print('started new message')

        if self.timeout and (
                ((now - self.before_read_success_time) > one_char_wait*3.5) and
                ((now - self.last_write_time) > one_char_wait*3.5) and
                len(self.send_buffer) != 0):
            #print ('send buffer is', self.send_buffer)
            s = self.send_buffer[0]
            s += bytes([crc(s)])
            self.send_buffer.pop(0)
            # print ('sending ', s)
            self.ser.write (s)
            # f.write (f'-> {bytes.hex(s)} gap before last comm: {(time.clock_gettime(time.CLOCK_MONOTONIC) - before_read_success_time)*1000} ms\n')
            self.last_write_time = now # reset time

    def send (self, msg):
        self.send_buffer += [msg]
