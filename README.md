SendKeys
========

###Description:
A utility for sending keystrokes to an attached Android device.  

###Requirements:
adb available and pathed in  
android device connected  
python 2.?  

###Notes:
This utility can be pretty slow with special keys as they are sent through adb and processed one at a time due to a limitation in "adb shell input keyevent".  Normal keys can be queued up and and sent in batches (strings!).
It is generally faster to do normal navigation with the touchpad on Glass and then normal key entry through SendKeys.

###Testing:
So far only tested with Python 2.7.3  
Only tested with Google Glass so far  
