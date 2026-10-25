#!/usr/bin/env bash
set -u
adb shell settings put secure show_ime_with_hard_keyboard 1
test_status=0
gradle -p android connectedDebugAndroidTest || test_status=$?
adb logcat -d > android-interaction-logcat.txt
adb pull /sdcard/Android/data/app.sofaremote/files/ android-interaction-screenshots || true
cp /tmp/sofa-android.log android-interaction-server.log
exit "$test_status"
