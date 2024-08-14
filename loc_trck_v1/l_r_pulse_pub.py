import rclpy
from rclpy.node import Node
from std_msgs.msg import Int16
import RPi.GPIO as GPIO
import busio
import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import threading
import time
import signal
import sys

# Shared variables for encoder counts
counter_r = 0
counter_l = 0
trnc_vol_l = 0
trnc_vol_r = 0

# Lock to synchronize access to shared variables
lock = threading.Lock()

def count_l(channel):
    global counter_l, trnc_vol_l
    with lock:
        if trnc_vol_l < 2.547:
            counter_l += 1
        elif trnc_vol_l > 2.551:
            counter_l -= 1

def count_r(channel):
    global counter_r, trnc_vol_r
    with lock:
        if trnc_vol_r > 2.484:
            counter_r += 1
            print(f'frwrd: {counter_r}')
        elif trnc_vol_r < 2.476:
            counter_r -= 1
            print(f'bkwrd: {counter_r}')

def setup_gpio():
    r_enc = 23
    l_enc = 24
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(r_enc, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(l_enc, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(l_enc, GPIO.FALLING, callback=count_l, bouncetime=30)
    GPIO.add_event_detect(r_enc, GPIO.FALLING, callback=count_r, bouncetime=30)

def gpio_thread():
    setup_gpio()
    while True:
        time.sleep(1)  # Keep the thread alive to handle GPIO events

class encPUBLISHER(Node):
    def __init__(self):
        super().__init__('enc_pub')
        self.publisher_1 = self.create_publisher(Int16, "lwheel", 10)
        self.publisher_2 = self.create_publisher(Int16, "rwheel", 10)

        self.timer = self.create_timer(1, self.publish_enc_values)
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c)

    def publish_enc_values(self):
        global counter_l, counter_r, trnc_vol_l, trnc_vol_r
        with lock:
            chan_l = AnalogIn(self.ads, ADS.P1)
            chan_r = AnalogIn(self.ads, ADS.P0)
            trnc_vol_l = round(chan_l.voltage, 3)
            trnc_vol_r = round(chan_r.voltage, 3)
            
            msg1 = Int16()
            msg1.data = counter_l
            self.publisher_1.publish(msg1)

            msg2 = Int16()
            msg2.data = counter_r
            self.publisher_2.publish(msg2)

def main(args=None):
    try:
    # Start GPIO interrupt handling in a separate thread
        gpio_thread_instance = threading.Thread(target=gpio_thread)
        gpio_thread_instance.daemon = True
        gpio_thread_instance.start()

    # Start the ROS 2 node
        rclpy.init(args=args)
        enc_pub = encPUBLISHER()
        rclpy.spin(enc_pub)
    except KeyboardInterrupt:
       print("i'm dying")
    finally:
        GPIO.cleanup()
        enc_pub.destroy_node()
        rclpy.shutdown()
if __name__ == '__main__':
    main()
