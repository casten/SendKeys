'''
Created on Aug 19, 2013

This sends keys from a terminal to an android device.

@author: Casten Riepling
'''
import curses,time
import subprocess,shlex
import threading
from threading import Thread, Lock, Event
import sys

versionSendKeys='0.1'

debug=False
if debug:
    #update for your location of pydev if you want to debug in pydev (curses precludes from using Eclipse)
    sys.path.append(r'/home/casten/adt-bundle-linux-x86_64-20130729/eclipse/plugins/org.python.pydev_2.8.1.2013072611/pysrc')
    import pydevd


#was originally in a separate file, but I put it in here so it could be a single file
class AdbUtils:
    @staticmethod
    def adbCommand(command):
        process = subprocess.Popen(['adb',command],stdout=subprocess.PIPE)
        out, _ = process.communicate()
        return out

    @staticmethod
    def adbSendKeys(keys):
        command = 'shell input text '+''.join(chr(x) for x in keys)
        args = shlex.split(command)
        args.insert(0, 'adb')
        process = subprocess.Popen(args,stdout=subprocess.PIPE)
        out, _ = process.communicate()
        return out
    
    @staticmethod
    def adbSendSpecials(specials):
        strSpecials = ''
        for x in specials:
            strSpecials += 'input keyevent ' +str(x)+';'
             
        command = 'shell '+strSpecials
        args = shlex.split(command)
        args.insert(0, 'adb')
        process = subprocess.Popen(args,stdout=subprocess.PIPE)
        out, _ = process.communicate()
        return out
    
    @staticmethod
    def monkeyRunExperiment():
        command = r'/home/casten/adt-bundle-linux-x86_64-20130729/sdk/tools/monkeyrunner'
        args = shlex.split(command)
        process = subprocess.Popen(args,stdout=subprocess.PIPE,stdin=subprocess.PIPE,close_fds=False)
        out, __ = process.communicate("from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice\rdevice = MonkeyRunner.waitForConnection()\rdevice.press('KEYCODE_ENTER', MonkeyDevice.DOWN_AND_UP)\r")
        return out    


def isNewVersion():
	try:
		import urllib2
		response = urllib2.urlopen('https://raw.github.com/casten/SendKeys/master/version')
		version = response.read().strip()
		if (version != versionSendKeys):
			return True 
	except:
		pass
	return False

def checkDevice():
    resp = AdbUtils.adbCommand('devices')
    if 'device\n' not in resp:
        return False
    return True

def initCurses(scr):
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    scr.keypad(1)
    scr.nodelay(True)

def cleanupCurses(scr):
    curses.echo()
    curses.nocbreak()
    curses.curs_set(1)
    scr.keypad(0)
    scr.nodelay(False)
    curses.endwin()

def enum(**enums):
    return type('Enum', (), enums)

andKeys = enum(
    KEYCODE_HOME = 3,
    KEYCODE_BACK = 4,
    KEYCODE_DPAD_UP = 19,
    KEYCODE_DPAD_DOWN = 20,
    KEYCODE_DPAD_LEFT = 21,
    KEYCODE_DPAD_RIGHT = 22,
    KEYCODE_CAMERA = 27,
    KEYCODE_ENTER = 66,
    KEYCODE_ESCAPE = 111
)


cursesAndroidMap = {
                    curses.KEY_HOME:andKeys.KEYCODE_HOME,
                    27:andKeys.KEYCODE_BACK,
                    curses.KEY_UP:andKeys.KEYCODE_DPAD_UP,
                    curses.KEY_DOWN:andKeys.KEYCODE_DPAD_DOWN,
                    curses.KEY_LEFT:andKeys.KEYCODE_DPAD_LEFT,
                    curses.KEY_RIGHT:andKeys.KEYCODE_DPAD_RIGHT,
                    curses.KEY_IC:andKeys.KEYCODE_CAMERA,
                    10:andKeys.KEYCODE_ENTER
                    }

def cursesToAndroid(c):
    if c in cursesAndroidMap:
        return True,cursesAndroidMap[c]
    else:
        return False,c
    
def printLegend():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK);
            stdscr.addstr(0,0,'SendKeys for Android')
            stdscr.attron(curses.color_pair(1));
            stdscr.addstr(0,21,'by Casten Riepling')
            stdscr.attroff(curses.color_pair(1));
            stdscr.addstr(3,0,'        Special Keys        ',curses.A_UNDERLINE)
            stdscr.addstr(4,0,'HOME key      - Android Home')
            stdscr.addstr(5,0,'ESCape key    - Android Back')
            stdscr.addstr(6,0,'INSert key    - Take Picture')
            stdscr.addstr(7,0,'Arrow keys    - DPAD Keys')
            stdscr.addstr(8,0,'Ctrl-c        - Quit')
            if (isNewVersion()):
                stdscr.addstr(9,0,'Note:  a new version is available at http://github.com/casten/SendKeys',curses.A_REVERSE)
                stdscr.refresh()

	
#This handles the queue of keys in a (hopefully!) thread safe manner
class keyQueue():
    queue = []
    lock = Lock()
    
    #This gets a block of values that are all of the same type (special or normal).
    #We do this because we send blocks of keys of the same type since we use slightly
    #different methods for sending them over.
    def getValsBlock(self):
        self.lock.acquire()
        isSpecial,val = self._dequeue()
        vals = [val]
        while(self._size()):
            if self._peek(0)[0] == isSpecial:
                item = self._dequeue()
                vals.append(item[1])
            else:
                break
        self.lock.release()
        return isSpecial,vals
    
    def enqueue(self, key):
        self.lock.acquire()
        self.queue.append(key)
        self.lock.release()

    def _dequeue(self):
        item = self.queue[0]
        del self.queue[0]
        return item
    
    def dequeue(self):
        self.lock.acquire()
        item = self._dequeue()
        self.lock.release()
        return item
    
    def _size(self):
        length = len(self.queue)
        return length

    def size(self):
        self.lock.acquire()
        length = self._size()
        self.lock.release()
        return length
    
    def _peek(self,index):
        item = self.queue[index]
        return item
    
#Threadproc for reading keys asynchronously from cursers and putting them in the
#queue to send            
def keyReader(scr,kq,killme):
    while(not killme.isSet()):
        key = scr.getch(1,0)
        if (key != -1):
            isSpecial, key = cursesToAndroid(key)
            kq.enqueue([isSpecial,key])
        else:
            time.sleep(0.1)

def processKeys():
    thread = None
    killEvent = Event() 
    lastFlush = time.time()
    kq = keyQueue()
    thread = Thread(target=keyReader,args=(stdscr,kq,killEvent))
    thread.name = 'keyboard-reader'
    thread.start()
    while(True):
        try:
            while (kq.size() ==  0):
                time.sleep(0.1)
            now = time.time()
            #queue up keys for 1 second before sending off since there
            #is a lot of latency sending events across adb 
            if ((now - lastFlush) > 1):
                while(kq.size() > 0):
                    #get the next block of keys of the same type (special or not)
                    isSpecial,vals = kq.getValsBlock()
                    if (isSpecial):
                        AdbUtils.adbSendSpecials(vals)
                    else:
                        AdbUtils.adbSendKeys(vals)
                stdscr.refresh()
                lastFlush = time.time()
        except KeyboardInterrupt:
            break
    killEvent.set()
    
    
if __name__ == '__main__':    
    if debug:
        pydevd.settrace()
    if not checkDevice():   
        print 'no device attached'
        exit()
    stdscr = curses.initscr()
    initCurses(stdscr)
    printLegend()
    processKeys()
    cleanupCurses(stdscr)
        




