#!/usr/bin/env python3
"""Build esp32c5-lp/svd/esp32c5-lp.base.svd from the HP esp32c5.base.svd.

Usage (from the esp-pacs repo root):
    python3 make_esp32c5_lp_base_svd.py \
        [esp32c5/svd/esp32c5.base.svd] [esp32c5-lp/svd/esp32c5-lp.base.svd]

Keeps only the peripherals the LP core uses (same set as esp32c6-lp, minus
PMU which is copied at patch time, plus LP_IO_MUX) and replaces the HP
interrupt numbers with the LP-core ones in LP_INTERRUPTS below.
"""
import copy
import sys
import xml.etree.ElementTree as ET

SRC = sys.argv[1] if len(sys.argv) > 1 else "esp32c5/svd/esp32c5.base.svd"
DST = sys.argv[2] if len(sys.argv) > 2 else "esp32c5-lp/svd/esp32c5-lp.base.svd"

KEEP = [
    "LP_I2C0", "LPPERI", "LP_ANA", "LP_AON", "LP_APM0", "LP_CLKRST",
    "LP_I2C_ANA_MST", "LP_IO", "LP_IO_MUX", "LP_TEE", "LP_TIMER",
    "LP_UART", "LP_WDT",
]

# !!! UNVERIFIED !!!  Copied from esp32c6-lp.  The numbers in the HP SVD
# (LP_UART=16, PMU=13, ...) are HP interrupt-matrix sources, NOT LP-core
# interrupt numbers.  Check the ESP32-C5 TRM (LP CPU interrupts) and fix here
# (and PMU's value in svd/patches/_pmu.yml).
LP_INTERRUPTS = {
    "LP_IO":    ("LP_IO_INT", 0),
    "LP_I2C0":  ("LP_I2C_INT", 1),
    "LP_UART":  ("LP_UART_INT", 2),
    "LP_TIMER": ("LP_TIMER_INT", 3),
}
# PMU 5

XS = "http://www.w3.org/2001/XMLSchema-instance"
ET.register_namespace("xs", XS)

root = ET.parse(SRC).getroot()
root.find("name").text = "ESP32-C5-LP"
root.find("description").text = "32-bit RISC-V MCU"

periph = root.find("peripherals")
by_name = {p.findtext("name"): p for p in periph}
missing = [n for n in KEEP if n not in by_name]
if missing:
    sys.exit(f"peripherals not found in {SRC}: {missing}")

for p in list(periph):
    periph.remove(p)
for n in KEEP:
    p = copy.deepcopy(by_name[n])
    for i in p.findall("interrupt"):
        p.remove(i)
    if n in LP_INTERRUPTS:
        iname, ival = LP_INTERRUPTS[n]
        e = ET.Element("interrupt")
        ET.SubElement(e, "name").text = iname
        ET.SubElement(e, "value").text = str(ival)
        regs = p.find("registers")
        p.insert(list(p).index(regs) if regs is not None else len(p), e)
    periph.append(p)

ET.indent(root, space="  ")
ET.ElementTree(root).write(DST, encoding="UTF-8", xml_declaration=True)
print(f"wrote {DST}: {len(KEEP)} peripherals")
print("WARNING: LP interrupt numbers are copied from esp32c6-lp and UNVERIFIED for C5")
