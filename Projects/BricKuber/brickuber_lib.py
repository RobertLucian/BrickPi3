#!/usr/bin/env python
#
# https://www.dexterindustries.com/BrickPi/
# https://github.com/DexterInd/BrickPi3
#
# Copyright (c) 2017 Dexter Industries
# Released under the MIT license (http://choosealicense.com/licenses/mit/).
# For more information, see https://github.com/DexterInd/BrickPi3/blob/master/LICENSE.md
#
# This code is a library of support functions for a Rubik's cube solving robot

from __future__ import print_function # use python 3 syntax but make it compatible with python 2
from __future__ import division       #                           ''

import time     # import the time library for the sleep function
import brickpi3 # import the BrickPi3 drivers
import commands # import system command support


# class of methods for reading an manipulating a Rubik's cube.
class BricKuberLib(object):
    # create a BrickPi3 instance
    BP = brickpi3.BrickPi3()
    
    # define motor ports
    MOTOR_GRAB = 0
    MOTOR_TURN = 1
    MOTOR_PORTS = [BP.PORT_D, BP.PORT_A]
    
    def __init__(self, robot_style, debug = False):
        self.debug = debug
        if robot_style == "NXT1":
            self.TurnTablePinion = 24
            self.TurnTableGear = 56
            
            # motor position constants
            self.MOTOR_GRAB_POSITION_HOME      = 0
            self.MOTOR_GRAB_POSITION_REST      = -35
            self.MOTOR_GRAB_POSITION_FLIP_PUSH = -90
            self.MOTOR_GRAB_POSITION_GRAB      = -130
            self.MOTOR_GRAB_POSITION_FLIP      = -240
            
            self.MOTOR_GRAB_SPEED_GRAB = 400
            self.MOTOR_GRAB_SPEED_FLIP = 600
            self.MOTOR_GRAB_SPEED_REST = 400
        elif robot_style == "EV3":
            self.TurnTablePinion = 12
            self.TurnTableGear = 36
            
            # motor position constants (these likely need to be adjusted)
            self.MOTOR_GRAB_POSITION_HOME      = 0
            self.MOTOR_GRAB_POSITION_REST      = -35
            self.MOTOR_GRAB_POSITION_FLIP_PUSH = -90
            self.MOTOR_GRAB_POSITION_GRAB      = -130
            self.MOTOR_GRAB_POSITION_FLIP      = -240
            
            self.MOTOR_GRAB_SPEED_GRAB = 400
            self.MOTOR_GRAB_SPEED_FLIP = 600
            self.MOTOR_GRAB_SPEED_REST = 400
        else:
            raise ValueError("Unsupported robot style")
        
        self.BP.set_motor_limits(self.MOTOR_PORTS[self.MOTOR_TURN], 0, ((500 * self.TurnTableGear) / self.TurnTablePinion))
        
        self.home_all()
    
    # find motor home positions for all motors
    def home_all(self):
        self.BP.set_motor_power(self.MOTOR_PORTS[self.MOTOR_GRAB], 15)
        EncoderLast = self.BP.get_motor_encoder(self.MOTOR_PORTS[self.MOTOR_GRAB])
        time.sleep(0.1)
        EncoderNow = self.BP.get_motor_encoder(self.MOTOR_PORTS[self.MOTOR_GRAB])
        while EncoderNow != EncoderLast:
            EncoderLast = EncoderNow
            time.sleep(0.1)
            EncoderNow = self.BP.get_motor_encoder(self.MOTOR_PORTS[self.MOTOR_GRAB])
        self.BP.offset_motor_encoder(self.MOTOR_PORTS[self.MOTOR_GRAB], (EncoderNow - 25))
        self.BP.set_motor_position(self.MOTOR_PORTS[self.MOTOR_GRAB], self.MOTOR_GRAB_POSITION_REST)
        
        self.BP.offset_motor_encoder(self.MOTOR_PORTS[self.MOTOR_TURN], self.BP.get_motor_encoder(self.MOTOR_PORTS[self.MOTOR_TURN]))
        self.TurnTableTarget = 0
        self.spin(0)
    
    # run a motor to the specified position, and wait for it to get there
    def run_to_position(self, port, position, tolerance = 3):
        self.BP.set_motor_position(self.MOTOR_PORTS[port], position)
        encoder = self.BP.get_motor_encoder(self.MOTOR_PORTS[port])
        while((encoder > (position + tolerance)) or (encoder < (position - tolerance))):
            time.sleep(0.01)
            encoder = self.BP.get_motor_encoder(self.MOTOR_PORTS[port])
    
    # spin the cube the specified number of degrees. Opionally overshoot and return (helps with the significant mechanical play while making a face turn).
    def spin(self, deg, overshoot = 0):
        if deg < 0:
            overshoot = -overshoot
        self.TurnTableTarget -= (deg + overshoot)
        self.run_to_position(self.MOTOR_TURN, ((self.TurnTableTarget * self.TurnTableGear) / self.TurnTablePinion))
        if overshoot != 0:
            self.TurnTableTarget += overshoot
            self.run_to_position(self.MOTOR_TURN, ((self.TurnTableTarget * self.TurnTableGear) / self.TurnTablePinion))
    
    # grab the cube
    def grab(self):
        self.BP.set_motor_limits(self.MOTOR_PORTS[self.MOTOR_GRAB], 0, self.MOTOR_GRAB_SPEED_GRAB)
        self.run_to_position(self.MOTOR_GRAB, self.MOTOR_GRAB_POSITION_GRAB)
        time.sleep(0.2)
    
    # release the cube
    def release(self):
        self.BP.set_motor_limits(self.MOTOR_PORTS[self.MOTOR_GRAB], 0, self.MOTOR_GRAB_SPEED_REST)
        self.run_to_position(self.MOTOR_GRAB, self.MOTOR_GRAB_POSITION_REST)
    
    # flip the cube, and optionall release if afterwards
    def flip(self, release = False):
        self.run_to_position(self.MOTOR_GRAB, self.MOTOR_GRAB_POSITION_FLIP_PUSH)
        time.sleep(0.05)
        self.grab()
        time.sleep(0.2)
        
        self.BP.set_motor_limits(self.MOTOR_PORTS[self.MOTOR_GRAB], 0, self.MOTOR_GRAB_SPEED_FLIP)
        self.run_to_position(self.MOTOR_GRAB, self.MOTOR_GRAB_POSITION_FLIP)
        
        self.run_to_position(self.MOTOR_GRAB, self.MOTOR_GRAB_POSITION_FLIP_PUSH)
        
        if release:
            self.release()
    
    # Return Opposite Face.
    def OF(self, f):
        if f < 3:
            return f + 3
        return f - 3
    
    # Current Cube Orientation. Keeps track of the cube orientation.
    CCO = [0, 1, 2] # side U, F, R
    
    # Execute a move
    def Move(self, cmd):
        DegreesToTurnFace = -90
        RecoverFace = 22
        if(cmd.find("'") != -1):
            DegreesToTurnFace = 90
        elif (cmd.find("2") != -1):
            DegreesToTurnFace = -180
        
        if(cmd.find("U") != -1):
            FaceToTurn = 0
        elif(cmd.find("F") != -1):
            FaceToTurn = 1
        elif(cmd.find("R") != -1):
            FaceToTurn = 2
        elif(cmd.find("D") != -1):
            FaceToTurn = 3
        elif(cmd.find("B") != -1):
            FaceToTurn = 4
        elif(cmd.find("L") != -1):
            FaceToTurn = 5
        
        if FaceToTurn == self.CCO[0]:
            # target is top
            # flip twice
            
            self.flip()
            self.flip()
            self.CCO[0] = self.OF(self.CCO[0])
            self.CCO[1] = self.OF(self.CCO[1])
        elif FaceToTurn == self.CCO[1]:
            # target is front
            # rotate 180 and flip
            
            self.release()
            self.spin(180)
            self.CCO[1] = self.OF(self.CCO[1])
            self.CCO[2] = self.OF(self.CCO[2])
            
            self.flip()
            tmp = self.CCO[0]
            self.CCO[0] = self.CCO[1]
            self.CCO[1] = self.OF(tmp)
        elif FaceToTurn == self.CCO[2]:
            # target is right
            # rotate -90 and flip
            
            self.release()
            self.spin(-90)
            tmp = self.CCO[2]
            self.CCO[2] = self.CCO[1]
            self.CCO[1] = self.OF(tmp)
            
            self.flip()
            tmp = self.CCO[0]
            self.CCO[0] = self.CCO[1]
            self.CCO[1] = self.OF(tmp)
        elif FaceToTurn == self.OF(self.CCO[0]):
            # target is bottom
            # don't do anything
            
            pass
        elif FaceToTurn == self.OF(self.CCO[1]):
            # target is back
            # flip
            
            self.flip()
            tmp = self.CCO[0]
            self.CCO[0] = self.CCO[1]
            self.CCO[1] = self.OF(tmp)
        elif FaceToTurn == self.OF(self.CCO[2]):
            # target is left
            # rotate 90 and flip
            
            self.release()
            self.spin(90)
            tmp = self.CCO[1]
            self.CCO[1] = self.CCO[2]
            self.CCO[2] = self.OF(tmp)
            
            self.flip()
            tmp = self.CCO[0]
            self.CCO[0] = self.CCO[1]
            self.CCO[1] = self.OF(tmp)
        
        self.grab()
        self.spin(DegreesToTurnFace, RecoverFace)
    
    # Execute a string of moves
    def Moves(self, cmds):
        for cmd in cmds.split():
            self.Move(cmd)
        self.run_to_position(self.MOTOR_GRAB, self.MOTOR_GRAB_POSITION_REST)
    
    rgb_values = [[0, 0, 0] for c in range(54)]
    
    # Use the camera to read the RGB colors for each of the 9 squares on the face
    def CameraReadFaceColors(self, face):
        commands.getstatusoutput(('raspistill -w 300 -h 300 -t 1 -o /tmp/BricKuber_%s_face.jpg' % face))
        raw_result = commands.getstatusoutput(('rubiks-cube-tracker.py --filename /tmp/BricKuber_%s_face.jpg' % face))[1]
        raw_result = raw_result.split("\n{")[1]
        raw_result = raw_result.split("}")[0]
        raw_results = raw_result.split("[")[1:]
        for c in range(9):
            raw_results[c] = raw_results[c].split("]")[0]
        
        if face == "front":
            numbers = [19, 20, 21, 22, 23, 24, 25, 26, 27]
        elif face == "right":
            numbers = [36, 35, 34, 33, 32, 31, 30, 29, 28]
        elif face == "back":
            numbers = [43, 40, 37, 44, 41, 38, 45, 42, 39]
        elif face == "left":
            numbers = [16, 13, 10, 17, 14, 11, 18, 15, 12]
        elif face == "top":
            numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        elif face == "bottom":
            numbers = [46, 47, 48, 49, 50, 51, 52, 53, 54]
        
        for c in range(9):
            vals = raw_results[c].split(", ")
            for v in range(3):
                self.rgb_values[numbers[c] - 1][v] = int(vals[v])
    
    # Read the entire cube, and retun the result as a string that can be fed directly into kociemba.
    def ReadCubeColors(self):
        self.release()
        self.CameraReadFaceColors("top")
        self.flip(True)
        self.CameraReadFaceColors("front")
        self.flip(True)
        self.CameraReadFaceColors("bottom")
        self.spin(90)
        self.flip(True)
        self.CameraReadFaceColors("right")
        self.spin(-90)
        self.flip(True)
        self.CameraReadFaceColors("back")
        self.flip(True)
        self.CameraReadFaceColors("left")
        self.CCO = [5, 1, 0]
        
        str = "'{"
        for c in range(54):
            str += '"%d": [%d, %d, %d]' % ((c + 1), self.rgb_values[c][0], self.rgb_values[c][1], self.rgb_values[c][2])
            if c == 53:
                str += "}'"
            else:
                str += ', '
        
        str = 'rubiks-color-resolver.py --rgb %s' % str
        if self.debug:
            print(str)
        raw_result = commands.getstatusoutput(str)[1]
        raw_result = raw_result.split("\n")
        raw_result = raw_result[-1]
        return raw_result
