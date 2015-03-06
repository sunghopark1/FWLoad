#!/usr/bin/env python

'''
open connections to ref and test boards
'''

import mav_reference
import mav_test
import nsh_console
import util
from config import *
from StringIO import StringIO
from pymavlink import mavutil
from pymavlink.rotmat import Vector3
import rotate

def ref_gyro_offset_ok(refmav):
    '''check if ref gyro offsets are in range

    This copes with the reference board moving while in startup, which
    can lead to bad gyro calibration
    '''
    ref_ofs = refmav.recv_match(type='SENSOR_OFFSETS', blocking=True, timeout=5)
    if ref_ofs is None:
        return False
    gyros = Vector3(degrees(ref_ofs.gyro_cal_x),
                    degrees(ref_ofs.gyro_cal_y),
                    degrees(ref_ofs.gyro_cal_z))

    print("Gyro reference %.2f" % gyros.length())
    return gyros.length() < REF_GYRO_TOLERANCE
    

class Connection(object):
    '''open connections to ref and test boards'''
    def __init__(self, ref_only=False):
        util.kill_processes(['mavproxy.py', GDB])
        
        self.reflog = StringIO()
        self.testlog = StringIO()
        self.ref = None
        self.test = None
        self.nsh = None
        self.refmav = None
        self.testmav = None
        
        try:
            self.ref = mav_reference.mav_reference(self.reflog)
        except Exception as ex:
            self.close()
            util.show_error('Connecting to reference board1', ex, self.reflog)

        try:
            if not ref_only:
                self.test = mav_test.mav_test(self.testlog)
        except Exception as ex:
            self.close()
            util.show_error('Connecting to test board1', ex, self.testlog)

        try:
            if not ref_only:
                self.nsh = nsh_console.nsh_console()
        except Exception as ex:
            self.close()
            util.show_error('Connecting to nsh console', ex, self.testlog)

        try:
            print("CONNECTING MAVLINK TO REFERENCE BOARD")
            self.refmav = mavutil.mavlink_connection('127.0.0.1:14550')
            util.wait_heartbeat(self.refmav, timeout=30)
            util.wait_mode(self.refmav, IDLE_MODES)
        except Exception as ex:
            self.close()
            util.show_error('Connecting to reference board2', ex, self.reflog)

        try:
            if not ref_only:
                print("CONNECTING MAVLINK TO TEST BOARD")
                self.testmav = mavutil.mavlink_connection('127.0.0.1:14551')
                util.wait_heartbeat(self.testmav, timeout=30)
                util.wait_mode(self.testmav, IDLE_MODES)
        except Exception as ex:
            self.close()
            util.show_error('Connecting to test board2', ex, self.testlog)

        try:
            if not ref_only and not ref_gyro_offset_ok(self.refmav):
                self.close()
                util.failure("Bad reference gyro - FAILED")
        except Exception as ex:
            self.close()
            util.show_error('testing reference gyros', ex)

        print("Setting reference safety off")
        try:
            rotate.set_rotation(self, 'level', wait=False)
            util.safety_off(self.refmav)
        except Exception as ex:
            self.close()
            util.show_error("unable to set safety off", ex)

    def discard_messages(self):
        '''discard pending mavlink messages'''
        if self.refmav:
            util.discard_messages(self.refmav)
        if self.testmav:
            util.discard_messages(self.testmav)

    def close(self):
        '''close all connections'''
        print("Closing all connections")
        if self.refmav:
            self.refmav.close()
            self.refmav = None
        if self.testmav:
            self.testmav.close()
            self.testmav = None
        if self.ref:
            self.ref.close()
            self.ref = None
        if self.test:
            self.test.close()
            self.test = None
        if self.nsh:
            self.nsh.close()
            self.nsh = None

    def __del__(self):
        '''auto-close'''
        self.close()

if __name__ == '__main__':
    c = Connection()
