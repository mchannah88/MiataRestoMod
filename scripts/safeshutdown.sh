#!/bin/bash

# GPIO Pin configuration (Modify these if using different pins)
GPIO_OUT=23
GPIO_IN=24

echo "$GPIO_IN" > /sys/class/gpio/export
echo "in" > /sys/class/gpio/gpio$GPIO_IN/direction
echo "$GPIO_OUT" > /sys/class/gpio/export
echo "out" > /sys/class/gpio/gpio$GPIO_OUT/direction

# Tells the circuit the Pi is fully on
echo "1" > /sys/class/gpio/gpio$GPIO_OUT/value

while [ 1 ]; do
  # Polls the GPIO pin to check if the button is pressed (status "0")
  status=$(cat /sys/class/gpio/gpio$GPIO_IN/value)
  if [ "$status" = "0" ]; then
    # Triggers graceful shutdown
    sudo shutdown -h now
    exit
  fi
  sleep 1
done
