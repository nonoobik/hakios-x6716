#!/usr/bin/env python3
"""
Pack mtkloader, XNUP payload, and stock DTB into Android boot image v2
for Infinix Note 30i (X6716 / MT6768).
"""
import argparse
import gzip
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PREBUILT = os.path.join(HERE, 'prebuilt', 'uefi')

DRAM_BASE = 0x40078000
KERNEL_OFFSET = 0x00008000
RAMDISK_OFFSET = 0x07C08000
TAGS_OFFSET = 0x0BC08000
PAGE_SIZE = 2048
HEADER_VERSION = 2

PREBUILT_DTB = os.path.join(PREBUILT, 'X6716.dtb')

def find_default_dtb():
    if os.path.isfile(PREBUILT_DTB):
        return PREBUILT_DTB
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-p', '--payload', required=True, help='Path to XNUP payload container')
    ap.add_argument('-o', '--output', default=os.path.join(HERE, 'xnu-x6716.img'), help='Output boot image path')
    ap.add_argument('--dtb', default=find_default_dtb(), help='Path to MT6768 X6716 DTB')
    args = ap.parse_args()
    if not args.dtb or not os.path.isfile(args.dtb):
        sys.exit(f'Error: no device tree ({args.dtb or PREBUILT_DTB})')

    loader_bin = os.path.join(HERE, 'mtkloader', 'mtkloader.bin')
    if not os.path.isfile(loader_bin):
        sys.exit(f'Error: {loader_bin} not found. Run mtkloader/build.sh first.')

    loader_data = open(loader_bin, 'rb').read()
    payload_data = open(args.payload, 'rb').read()
    assert payload_data[:4] == b'XNUP', 'Invalid payload magic'

    blob = loader_data + b'\0' * (-len(loader_data) % 16) + payload_data
    blob += b'\0' * (-len(blob) % 16)

    kernel_temp = args.output + '.kernel~'
    with open(kernel_temp, 'wb') as f:
        f.write(gzip.compress(blob, 6))

    mkbootimg = os.path.join(PREBUILT, 'mkbootimg.py')
    ramdisk = os.path.join(PREBUILT, 'ramdisk')

    cmd = [
        sys.executable, mkbootimg,
        '--kernel', kernel_temp,
        '--ramdisk', ramdisk,
        '--dtb', args.dtb,
        '--base', hex(DRAM_BASE),
        '--kernel_offset', hex(KERNEL_OFFSET),
        '--ramdisk_offset', hex(RAMDISK_OFFSET),
        '--tags_offset', hex(TAGS_OFFSET),
        '--pagesize', str(PAGE_SIZE),
        '--header_version', str(HEADER_VERSION),
        '-o', args.output
    ]

    try:
        subprocess.check_call(cmd)
    finally:
        try:
            os.unlink(kernel_temp)
        except OSError:
            pass

    print(f'Created {args.output}: {os.path.getsize(args.output)} bytes')

if __name__ == '__main__':
    main()
  
