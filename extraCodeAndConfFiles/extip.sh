#!/bin/bash

# Notifies a recipient email when the home public IP address changes
# (e.g. useful with a dynamic-IP ISP connection).
# Replace with your own notification email address.
NOTIFY_EMAIL="your-email@example.com"

NEWIP=$(curl -4 icanhazip.com)
OLDIP=$(cat /home/pi/bin/extip.txt)

if [[ $NEWIP != $OLDIP ]]
then
  #echo $OLDIP
  #echo $NEWIP
  #echo "Change"
  >/home/pi/bin/extip.txt
  echo "$NEWIP" >/home/pi/bin/extip.txt
  cat /home/pi/bin/extip.txt | rev | mailx -s "Cha-cha-cha-cha-Changes" "$NOTIFY_EMAIL"
#cat extip.txt
#else
  #echo $OLDIP
  #echo $NEWIP
  #echo "NoChange"
fi
