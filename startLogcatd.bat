@echo off
echo Start logcatd...

adb root
adb remount

adb shell setprop persist.logd.logpersistd logcatd
adb shell setprop persist.logd.logpersistd.size 5
adb shell setprop persist.logd.logpersistd.rotate_kbytes 102400
adb shell setprop logd.logpersistd.enable true

echo Done.
pause
