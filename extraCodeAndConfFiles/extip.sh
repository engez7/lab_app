#!/bin/bash

NEWIP=$(curl -4 icanhazip.com)
OLDIP=$(cat /home/pi/bin/extip.txt)

if [[ $NEWIP != $OLDIP ]]
then
  #echo $OLDIP
  #echo $NEWIP
  #echo "Change"
  >/home/pi/bin/extip.txt
  echo "$NEWIP" >/home/pi/bin/extip.txt
  cat /home/pi/bin/extip.txt | rev | mailx -s "Cha-cha-cha-cha-Changes" ezio.recaldini@gmail.com
#cat extip.txt
#else
  #echo $OLDIP
  #echo $NEWIP
  #echo "NoChange"
fi
