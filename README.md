# Air Monitoring On The Go

This project aims to simplify the process of setting up and using a portable air quality monitor, using low cost Adafruit hardware. 

The aim is that once you have the kit, it should be possible to create your own portable (and water resistant) air quality monitor in a short time.

# Pevious Work

This repo was forked from https://github.com/Option-Zero/software-for-climate-iot - which is an asignment set by [Option Zero](https://www.optionzero.co/), during their course [Software Stacks in Climate Tech](https://www.terra.do/climate-education/cohort-courses/software-stacks-in-climate-tech/)

# Hardware

This uses:
- an ESP32-S2 TFT Feather or [Reverse TFT Feather](https://learn.adafruit.com/esp32-s2-reverse-tft-feather)
- an [SCD40 or 41](https://learn.adafruit.com/adafruit-scd-40-and-scd-41) CO2/Temperature/Humidity sensor
- any other Adafruit sensors
- a battery
- cables to link the feather and sensors together
- a decent USB C cable that can do data transfer

# Setup

Install CircuitPython on your deveice and get one of the examples on the Circuitpython site going. Then copy across the files in this repository.
TODO: improve these instructions

