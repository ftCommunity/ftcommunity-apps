#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# as of 2020/04/29 found at https://github.com/harbaum/cfw-apps/tree/master/packages/tx-pi-hat-test 


class TxPiHat():
    MODE = "bcm"  # "bcm" or "board"

    if MODE == "board":
        # board mode uses the pin numbers of the 40 pin
        # connector.
        PINS = { "I1": 32, "I2": 36, "I3": 38, "I4": 40,
                 "STBY": 35,
                 "AIN1": 16, "AIN2": 15, "PWMA": 12,
                 "BIN1": 29, "BIN2": 31, "PWMB": 33 }
    else:
        # BCM mode uses the GPIO port numbers
        PINS = { "I1": 12, "I2": 16, "I3": 20, "I4": 21,
                 "STBY": 19,
                 "AIN1": 23, "AIN2": 22, "PWMA": 18,
                 "BIN1": 5,  "BIN2": 6,  "PWMB": 13 }
        
    def __init__(self):
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            
            self.GPIO.setwarnings(False)
            if self.MODE == "board":
                self.GPIO.setmode(self.GPIO.BOARD)
            else:
                self.GPIO.setmode(self.GPIO.BCM)

            # configure I1..I4 as input
            self.GPIO.setup(self.PINS["I1"], self.GPIO.IN)
            self.GPIO.setup(self.PINS["I2"], self.GPIO.IN)
            self.GPIO.setup(self.PINS["I3"], self.GPIO.IN)
            self.GPIO.setup(self.PINS["I4"], self.GPIO.IN)

            # power up h bridge for M1 and M2
            self.GPIO.setup(self.PINS["STBY"], self.GPIO.OUT)
            self.GPIO.output(self.PINS["STBY"], self.GPIO.HIGH)

            # ---------------- M1 -----------------------
            # configure h bridge
            self.GPIO.setup(self.PINS["PWMB"], self.GPIO.OUT)
            self.pwm1 = self.GPIO.PWM(self.PINS["PWMB"], 200)  # 200 Hz
            self.pwm1.start(0)

            self.GPIO.setup(self.PINS["BIN1"], self.GPIO.OUT)
            self.GPIO.output(self.PINS["BIN1"], self.GPIO.LOW)

            self.GPIO.setup(self.PINS["BIN2"], self.GPIO.OUT)
            self.GPIO.output(self.PINS["BIN2"], self.GPIO.LOW)

            # ---------------- M2 -----------------------
            # configure h bridge
            self.GPIO.setup(self.PINS["PWMA"], self.GPIO.OUT)
            self.pwm2 = self.GPIO.PWM(self.PINS["PWMA"], 200)  # 200 Hz
            self.pwm2.start(0)

            self.GPIO.setup(self.PINS["AIN1"], self.GPIO.OUT)
            self.GPIO.output(self.PINS["AIN1"], self.GPIO.LOW)
        
            self.GPIO.setup(self.PINS["AIN2"], self.GPIO.OUT)
            self.GPIO.output(self.PINS["AIN2"], self.GPIO.LOW)
            
            self.ok = True
        except Exception as e:
            self.ok = False
            self.err = str(e)

    def get_input(self, i):
        return self.GPIO.input(self.PINS[i]) != 1

    def m_set_pwm(self, motor, v):
        mpwm = { "M1": self.pwm1, "M2": self.pwm2 }
        mpwm[motor].ChangeDutyCycle(v)
       
    def m_set_mode(self, motor, mode):
        mpins = { "M1": [self.PINS["BIN1"], self.PINS["BIN2"]],
                  "M2": [self.PINS["AIN1"], self.PINS["AIN2"]] }
        bits = { "Off":   [ self.GPIO.LOW,  self.GPIO.LOW  ],
                 "Left":  [ self.GPIO.HIGH, self.GPIO.LOW  ],
                 "Right": [ self.GPIO.LOW,  self.GPIO.HIGH ],
                 "Brake": [ self.GPIO.HIGH, self.GPIO.HIGH ] }
        self.GPIO.output(mpins[motor][0], bits[mode][0]);
        self.GPIO.output(mpins[motor][1], bits[mode][1]);
