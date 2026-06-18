#!/bin/bash
# vim: fileencoding=utf-8:nomodified:nowrap:textwidth=0:foldmethod=marker:foldcolumn=4:syntax=sh:filetype=sh:ruler:showcmd:lcs=tab\:|- list
#
picocom -b 115200 --flow n --noreset --quiet --send-cmd "slowcat" /dev/ttyACM0


