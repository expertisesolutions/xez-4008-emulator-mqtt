import crcengine
import serial
import binascii
import time
import serial.rs485

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
        ccrc = msg[-1]
        ncrc = crc(msg[:-1])

        if ccrc != ncrc:
            #print ("Error doing CRC check for ", msg)
            for i in range (len(msg)-1):
                ccrc = msg[i]
                ncrc = crc(msg[:i])
                if ccrc == ncrc: # check first slice
                    ccrc = msg[-1]
                    ncrc = crc(msg[i+1:-1])
                    if ccrc == ncrc:
                        #print ("Looks like it should be broken down to: ", msg[:i+1], " and ", msg[i+1:])
                        self.__handle_msg (msg[:i+1], handler)
                        self.__handle_msg (msg[i+1:], handler)
                        return
                    else:
                        print ("Second part did not check, first part is: ", msg[:i+1])

            print ("Error doing CRC check for ", msg) #, ". Ignoring timing: ", delta*1000, ' gap before ', wait_before*1000)
            #f.write (f'<- CRC Fail for {bytes.hex(msg)} gap before: {wait_before*1000} \n')
            return

        handler (msg[:-1])
        # if msg == b'\x0e\x20\x05\x03\x00\x00\x00\x1e\xc9':
        #     m = group2[0]
        #     m = m[:-1]
        #     m = m + bytes([crc(m)])
        #     self.send_buffer += [m]
        # elif msg[:2] == (group2[1])[:2]:
        #     m = group2[2]
        #     m = m[:-1]
        #     m = m + bytes([crc(m)])
        #     self.send_buffer += [m]
        #     #print ('asked ', msg)
        #     #send_buffer += [group2[2]]
        # elif msg[:2] == (group2[3])[:2]:
        #     m = group2[4]
        #     m = m[:-1]
        #     m = m + bytes([crc(m)])
        #     self.send_buffer += [m]
        #     #self.send_buffer += [group2[4]]

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
            if len(self.msg) != 0:
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
