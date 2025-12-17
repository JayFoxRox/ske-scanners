#!/usr/bin/env python3

#FIXME: Dirty hacks with `global` and API to communicate with helper.py

import json
import os
import struct
import sys
import csv

from helper import *

plat = None

# Relevant functions are called
# JFR_some_table_element_init
#    JFR_get_table_element (first call in loop)
#        kingKongElementCount = JFR_numTableElements (used in bounds check)

# starWarsMessageTable
# (Can be found by searching for INVALID (which has XREFS from the localized tables); first entry of said table is XREF'd (might not auto-detect as pointer) which is the message map)


GAMES="/tmp/"

kingKongPro_0_88_0_Pro = {
    # 0x38 per element
    'UnkTable': 0x007446b8, # Stored at DAT_006f0a60
    'UnkCount': 0x16, # Initialized at 0039227c via DAT_007a9570 = DAT_005e41a8

    # 0x30 per element
    'ElementTable': 0x0749fc0,
    'ElementCount': 0x351,

    'MessageTable': 0x72a75c,

    'hook_node_board_device_led_table_data_entry_count': 0x2d6, # Found by 3x calloc in same function
    'JFR_led_table': 0x744b88, # 0x18 element size; found near XREF to hook_node_board_device_led_table_data_entry_count

    # switch table?
    # Found by looking for XREF to CN11 [first switch], then scrolling up
    'JFR_switch_table_probably': 0x748fa8,
    'JFR_switch_count': 0x67,

    'JFR_board_table': 0x0743e20,
    'JFR_board_count': 0xB, # 0x10 element size

    # some node table
     # &DAT_00743fd8 + uVar15 * 0x14;

    'path': GAMES + '/spike-2/king-kong/king_kong_pro-0_88_0.Release.16G.sdcard.raw.squashfs/games/king_kong_pro/',

    'alias': {}
}


starWarsFotE_0_85_0_LE = {
    # 0x58 per element
    'UnkTable': 0x8b5570, # Stored at 0x0869818
    'UnkCount': 0x13, # 0x58 per element

    # 0x50 per element
    'ElementTable': 0x8bca10, # ???
    'ElementCount': 0x29c,

    'MessageTable': 0x088ab10,
    'TypeTable': 0x8d1980,

    'JFR_switch_table_probably': 0x8bb410,
    'JFR_switch_count': 0x58,

    'hook_node_board_device_led_table_data_entry_count': 0x233,
    'JFR_led_table': 0x08b5bf8, # 0x28 per element
    
    'JFR_board_count': 9,
    'JFR_board_table': 0x008b44e0, # 0x20 per element

    #FIXME: Add finder and add to other games
    'node_board_type_table_data': 0x08b47b0,
    'NODE_BOARD_DEVICE_TYPE_TABLE_DATA_ENTRY_COUNT': 0x28, # 0x28 per element

    'path': GAMES + "/spike-3/star-wars-fall-of-the-empire/star_wars_2025_le-0_85_0.Release.64G.sdcard-secure.raw.squashfs/games/star_wars_2025_le/",

    "alias": {
        "playfield": "TestMenu/buck_le_playfield" # 002e0700 FotE 0.85 LE
    }
}


wdr_0_78_0_LE = {
    'UnkTable': 0x8b1c78,
    'UnkCount': 0x1A,

    'ElementTable': 0x8bc230,
    'ElementCount': 0x3CC,

    'MessageTable': 0x883be8,

    'JFR_switch_count': 0x5b,
    'JFR_switch_table_probably': 0x08bab70,

    'hook_node_board_device_led_table_data_entry_count': 0x359, # Assumed; found by looking for calloc, there's a function which does 3x calloc in sequence
    'JFR_led_table': 0x08b2568, # Found using XREFs to hook_node_board_device_led_table_data_entry_count

    'JFR_board_count': 10,
    'JFR_board_table': 0x8b0b98, # Found by looking for "Upper Playfield" (but CPU / Bridge) would have been easier

    'path': GAMES + '/walking_dead_remastered_le-0_78_0/walking_dead_remastered_le/',

    'alias': {}
}





def findBoardTable():
    # The first candidates will be relocation info
    candidates = []
    candidates += list(findCandidateStrTablePtrs([b'CPU / BRIDGE\x00'] * 5))
    candidates += list(findCandidateStrTablePtrs([b'CPU / Bridge\x00'] * 5))
    candidates += list(findCandidateStrTablePtrs([b'CPU\x00'] * 5)) # Batman '66 0.65.0
    print(candidates)
    for candidate in candidates[::-1]:
        print("0x%X" % candidate)
        candidate -= boardSize
        #Loop entries backwards until we find INVALID
        while not has(readPtr(readPtr(candidate)), b'INVALID\x00'):
            candidate -= boardSize
        start = candidate - 2 * plat['PtrSize']

        # Loop entries forward until pointers repeat [as table is typically followed by localized text arrays]
        candidate = start + boardSize
        
        
        # A bit of a hack.. Batman '66 V0.65.0 has fields in different order, so everything is off by 4
        # Because the second and third entry will be a duplicared string pointer this will also work, but ignore the off-by-4.
        candidate += plat['PtrSize']


        while True:
            x = readPtr(candidate + 0 * plat['PtrSize'])
            y = readPtr(candidate + 1 * plat['PtrSize'])
            if x == y:
                break
            candidate += boardSize
        end = candidate

        size = end - start
        count = size // boardSize

        return start, count
    assert(False)

def findBoardTypeTable():
    # The first candidates will be relocation info
    candidates = []

    # The \x00 prefix is to avoid ws2812pinnode
    pinnodeStrings = list(findCandidates(b'\x00pinnode\x00'))
    print(pinnodeStrings)
    assert(len(pinnodeStrings) == 1)
    print("0x%X" % (pinnodeStrings[0] + 1))
    candidates += list(findPtrCandidates(pinnodeStrings[0] + 1))

    for candidate in candidates:
        candidate -= boardTypeSize
        candidate += plat['PtrSize']
        #Loop entries backwards until we find INVALID
        print("0x%X" % candidate)
        while not has(readPtr(readPtr(candidate)), b'INVALID\x00'):
            candidate -= boardTypeSize
        start = candidate - 3 * plat['PtrSize'] # Spike 3

        # Loop entries forward until pointers repeat [as table is typically followed by localized text arrays]
        candidate = start + boardTypeSize

        while True:
            x = readPtr(candidate + 0 * plat['PtrSize'])
            y = readPtr(candidate + 1 * plat['PtrSize'])
            if x == y:
                break
            candidate += boardTypeSize
        end = candidate

        size = end - start
        count = size // boardTypeSize

        return start, count
    assert(False)

def findElementTable():
    # The first candidates will be relocation info
    candidates = []
    candidates += list(findCandidateStrTablePtrs([b"QR SCANNER BACKLIGHT\x00"] * 5))
    if False:
        candidates += list(findCandidateStrTablePtrs([b"BACKBOX GI\x00"] * 5))
    if False:
        # This also finds lamps and switches
        candidates += list(findCandidateStrTablePtrs([
            b"START BUTTON\x00",
            b"START KNOPF\x00",
            b"BOUTON START\x00",
            b"BOTON START\x00",
            b"PULSANTE START\x00",
        ]))

    # Needed for Batman '66 V0.65.0
    if False:
        candidates += list(findCandidateStrTablePtrs([b"TROUGH\x00"] * 1))
        #FIXME: Also need to look at the last candidates first

    for candidate in candidates:
        print("check 0x%X" % candidate)
        
        candidate -= elementSize
        
        # Loop entries backwards until we find INVALID
        while not has(readPtr(readPtr(candidate)), b'INVALID\x00'):
            candidate -= elementSize
        start = candidate - (0x10 if plat['PtrSize'] == 4 else 0x20)

        # Loop entries forward until pointers repeat [as table is typically followed by localized text arrays]
        # For older games (Batman '66 V0.65.0) the element size is 24 bytes (!)
        candidate = candidate + (0x20 if plat['PtrSize'] == 4 else 0x30)
        while True:
            x = readPtr(candidate + 0 * plat['PtrSize'])
            y = readPtr(candidate + 1 * plat['PtrSize'])
            if x != 0 and x == y:
                break
            candidate += elementSize
        end = candidate

        size = end - start
        assert(size % elementSize == 0)
        count = size // elementSize


        return start, count
    assert(False)


def findDriverTable():
    candidates = list(findCandidateStrTables([b"Unknown\x00"] * 5))
    for candidate in candidates:

        candidate += 6 * plat['PtrSize'] # Skip "Unknown" table
        candidate += 6 * plat['PtrSize'] # Skip "INVALID" table
    
        start = candidate

        return start, None

    assert(False)

def findLightTable():
    # Look for 3x N/A direct pointer, followed by *not* another N/A pointer and preceeded by 40 zeros, too
    candidates = list(findCandidateStrTables([b"N/A\x00"] * 3))
    for candidate in candidates:

        start = candidate - lightSize

        if read(start, lightSize) != b'\x00' * lightSize:
            continue

        candidate += plat['PtrSize'] * 3
        if read(candidate, 4) != b'\x00\x00\x01\x00':
            continue

        return start, None

    assert(False)

def findMessageTable():
    candidates = list(findCandidateStrTablePtrs([b"INVALID\x00"] * 4 + [b'INVALIDA\x00']))
    assert(len(candidates) == 1)

    # Table stores message in one order, but the data is stored after the table in reverse order.
    # So we can scan forward, and eventually the last entry will point at data in the next slot.
    i = 0
    start = candidates[0]
    while True:
        offset = start + i * plat['PtrSize']
        i += 1
        if readPtr(offset) == offset + plat['PtrSize']:
            count = i
            break
        

    return start, count


def findSwitchTable():

    # The first entry in the switch table is all zeroes, then we see a repeating pointer
    # 0x40 zero bytes, then a pointer, which repeats a number of times in - at least - first 10 slots or so
    guessed = 10 # FIXME: Check how many bytes in Spike 2
    for candidate in findCandidates(b'\x01' + b"\x00" * (guessed if plat['PtrSize'] == 4 else 33)):

        # We look for index 1 [to avoid looking at all zeros] so we need to go back one slot (+ first field)
        candidate -= plat['PtrSize'] + switchSize

        # Start is even earlier than this (fully empty)
        start = candidate - switchSize
        if read(start, switchSize) != b'\x00' * switchSize:
            continue

        # Now that we are at the first switch with pointer, check if it has a pointer
        x = readPtr(candidate)
        if x == 0:
            continue

        # Ensure the next 5 entries match the pointer
        isMatch = True
        for i in range(5):
            candidate += switchSize
            y = readPtr(candidate)
            if x != y:
                isMatch = False
                break

        if not isMatch:
            continue
            

        return start, 0
    assert(False)



def dumpTable(name, table):
    #csvfile = open(name, 'w', newline='')
    #out = csv.writer(csvfile, quoting=csv.QUOTE_NONNUMERIC)
    #out.writerow(list(table[0].keys()))
    #for info in table:
    #    out.writerow(list(info.values()))
    def fix(x):
        if isinstance(x, bytes):
            return x.hex()
        assert(False)
    open("/tmp/" + name, 'wb').write(json.dumps(table, indent=2, default=fix).encode())


def getTable(count, getter):
    table = []
    for i in range(count):
        table += [getter(i)]
    return table









def getBoard(i):

    # Can't do anything if we don't have this table
    if not 'JFR_board_table' in game:
        return None


    assert(i < game['JFR_board_count'])
    offset = game['JFR_board_table'] + i * boardSize
    print("Board at 0x%X" % (offset), boardSize)

    data = read(offset - imageBase, boardSize)

    r = Reader(data)
    info = {
        "unkA": r.readPtr(), # probably a pointer; 8 byte in Spike 3, 4 byte in Spike 2
        'unkFun': r.readPtr(),
        "name": r.readStrTable(),
        "board-type": r.parse("<H")[0],
        "node": r.parse("<H")[0],
        "pad?": r.read(0 if plat['PtrSize'] == 4 else 4).hex(),
    }
    print("0x%X" % r.cursor)
    assert(r.cursor == len(r.data))

    return info


def getElement(i):

    assert(i < game['ElementCount'])
    offset = game['ElementTable'] + i * elementSize
    print("Element at 0x%X" % (offset), elementSize)

    data = read(offset - imageBase, elementSize)

    r = Reader(data)
    info = {
        "node-ext": r.readStr(), # "8c" etc.
        "_meta": r.readStr(),
        "unkBPtr": r.readPtr(),
        'name': r.readStr(),
        'localizedName': r.readStrTable(),

        'description': r.readStr(),

        'imageName': r.readStr(),

        # 0x38 is uint16 index into yet another array with 0x20 size elements [Spike 3]
        'boardIndex': r.parse("<H")[0],

        'address': r.parse("<H")[0], # As in "8-DR-<address>"

        # 0x3c: index into type table at 8d1980
        'typeIndex': r.parse("<H")[0], # As in "8-<type>-<address>"
        
        'unk10': r.parse("<H")[0],

        'location': r.readMessage(),
        'type': r.readMessage(),

        'x': r.parse("<H")[0],
        'y': r.parse("<H")[0],

        'w': r.parse("<H")[0], #'retwireA',
        'h': r.parse("<H")[0], #'retwireB',

        'pad?': r.read(0 if plat['PtrSize'] == 4 else 4)
    }
    print("0x%X" % r.cursor)
    assert(r.cursor == len(r.data))

    print(info['boardIndex'], getBoard(info['boardIndex']))
    

    # Fixup the metadata:
    meta = {}
    print(info)
    if info['_meta'] != None:
        parts = info['_meta'].split("#")
        for part in parts:
            if part == '':
                continue
            print(part)
            key, _, value = part.partition(":")
            if key == 'part':
                print(key, value)
                assert(not 'part' in meta)
                meta['part'] = value
            elif key == 'rect':
                
                print(key, value)
                
                values = list(map(int, value.split(',')))

                # Create an iterator for the values
                it = iter(values)
                
                # Generate the dictionaries
                rects = [
                    {'x': next(it, None), 'y': next(it, None), 'w': next(it, None), 'h': next(it, None)}
                    for _ in range(0, len(values), 4)
                ]

                meta['rects'] = meta.get('rects', []) + rects
            else:
                print(part)
                assert(False)

    info["meta"] = meta

    return info

# Regarding address field in manual.
# in FotE 0.85 LE 0x058d7a0:
# lVar3 = ?
# param1 = element?
"""
if (*(long *)(&JFR_TypeOfTableElement + (ulong)uVar1 * 0x10) == 0) {
    sprintf(param_2,"%d%s.%d",(ulong)*(byte *)(lVar3 + 0x1a),"",
            (ulong)*(ushort *)(puVar2 + (ulong)param_1 * 0x50 + 0x3a));
}
else {
    sprintf(param_2,"%d%s-%s-%d",(ulong)*(byte *)(lVar3 + 0x1a),"");
}
"""

def toManualSwitch(info):
    print(info)
    element = getElement(info['element'])
    board = getBoard(element['boardIndex'])
    node = board['node'] if board != None else '???'
    manualItem = {
        "ID": info['id'],
        "Name": element['localizedName'],
        "Node": node,
        "Node Ext": element["node-ext"],
        "Conn.": info['connector'],
        "Input Pin": info['input-pin'],
        "Input Wire": info['input-wire-color'],
        "GND Pin": info['ground-pin'],
        "Ground Wire": info['ground-wire-color'],
        "Location": element['location'],
        "Type": element['type'],
        "Address": "%s-%s-%d" % (node, types[element['typeIndex']].upper(), element['address']),
        "Part Number": element['meta'].get('part', None)
    }
    #drawElement(element, str(info['id']), manualItem
    return manualItem


def toManualLight(info):
    element = getElement(info['element'])
    board = getBoard(element['boardIndex'])
    node = board['node'] if board != None else '???'
    manualItem = {
        "ID": info['id'],
        "Name": element['localizedName'],
        "Node": node,
        "Node Ext": element["node-ext"],
        "Conn.": info['connector'],
        "Ret. Pin": info['return-pin'],
        "Ret. Wire": info['return-wire-color'],
        "Src. Pin": info['source-pin'],
        "Src. Wire": info['source-wire-color'],
        "Location": element['location'],
        "Type": element['type'],
        "Light Color": '???', #FIXME: Does this info exist?
        "Address": "%s-%s-%d" % (node, types[element['typeIndex']].upper(), element['address']),
        "Part Number": element['meta'].get('part', None)
    }

    #drawElement(element, str(info['id']), manualItem)
    return manualItem
    

def toManualDriver(info):
    element = getElement(info['element'])
    board = getBoard(element['boardIndex'])
    node = board['node'] if board != None else '???'
    manualItem = {
        "ID": info['id'],
        "Name": element['localizedName'],
        "Node": node,
        "Conn.": info['connector'],
        "Ret. Pin": info['return-pin'],
        "Ret. Wire": info['return-wire-color'],
        "Voltage": info['voltage'],
        "V+ Pin": info['vplus-pin'],
        "V+ Wire": info['vplus-wire-color'],
        "Location": element['location'],
        "Type": element['type'],
        "Address": "%s-%s-%d" % (node, types[element['typeIndex']].upper(), element['address']),
        "Part Number": element['meta'].get('part', None)
    }

    #drawElement(element, str(info['id']), manualItem)
    return manualItem
    
    


def getSwitch(i):
    offset = game['JFR_switch_table_probably'] + i * switchSize
    data = read(offset - imageBase, switchSize)
    #print(data.hex())

    #for j in range(len(data) // 2):
    #    print("0x%X" % (j*2), ":", struct.unpack_from("<H", data, j * 2)[0])

    print("switch data at 0x%X" % offset)

    r = Reader(data)
    info = {            
        'unk0': r.readPtr(),
        'unk8': r.readPtr(), #read(0x8),
        
        # 0x8
        # 0x9
        # 0xA
        # 0xB
        # 0xC
        # 0xD
        # 0xE
        # 0xF
        
        'connector': r.readStr(),
        "input-pin": r.readStr(),
        "ground-pin": r.readStr(),
        'id': r.parse("<H")[0],

        #'_': r.check(0x16), # Spike 2 only

        'element': r.parse("<H")[0],

        'unkA': r.read(10),
        # 2C
        # 2D
        # 2E
        # 2F
        # 30
        # 31
        # 32
        # 33
        # 34
        # 35

        "input-wire-color": r.readMessage(), # 0x36
        "ground-wire-color": r.readMessage(), # 0x38

        'unkB': r.read(2 if plat['PtrSize'] == 4 else 6)
    }

    print("0x%X" % r.cursor)
    assert(r.cursor in [0x28, 0x40]) # Spike 2, Spike 3

    print("switch 0x%X" % offset, data.hex(), info)
    return info

def getLight(i):
    data = read(game['JFR_led_table'] + i * lightSize - imageBase, lightSize)

    r = Reader(data)
    info = {
        "connector": r.readStr(),
        "return-pin": r.readStr(),
        "source-pin": r.readStr(),
        "id": r.parse("<H")[0],
        "element": r.parse("<H")[0],
        "1C": r.parse("<H")[0],
        "1E": r.parse("<H")[0],
        "return-wire-color": r.readMessage(),
        "source-wire-color": r.readMessage(),
        'f_24': r.read(0 if plat['PtrSize'] == 4 else 4)
        #parse("<H")[0],
        #'f_26': r.parse("<H")[0],
    }

    print("0x%X" % r.cursor)
    assert(r.cursor in [0x18, 0x28]) # Spike 2, Spike 3

    return info

def getDriver(i):
    # 0x10 is a function pointed cb(void*, void*)
    # 0x3A = table element
    # 0x42 short
    # 0x44 short
    # 0x46 short



    print("")
    print("")
    offset = game['UnkTable'] + i*driverSize
    print("At 0x%X" % offset)
    data = read(offset - imageBase, driverSize)



    # if pointer at 0x10 is 0 then:
    #   if ((uint)puVar3->field31_0x42 + (uint)puVar3->field32_0x44 != 0) {
    #       FUN_003a4a20(uVar2,puVar3->field_0x4f,puVar3->field31_0x42,puVar3->field_0x50,
    #                 puVar3->field32_0x44,puVar3->field33_0x46);



    if False:
        UnkStruct = "<HHHHQQQQQQHHHHHHHHHHHHHHHH"
        x = struct.unpack(UnkStruct, data)
        print(x[0])
        assert(x[0] in [0, 8, 64, 256, 32768])
        print(x[1])
        assert(x[1] in [0, 1])
        print(x[2])
        assert(x[2] == 0)
        print(x[3])
        assert(x[3] == 0)
        print(x[4])
        assert(x[4] == 0)
        print(x[5])
        #assert(x[5] == 0)
        print(readStr(x[6]))
        print(readStr(x[7]))
        print(readStr(x[8]))
        print(readStr(x[9]))
        print(x[10])
        print(readStr(x[11]))
        print(readStr(x[12]))

    r = Reader(data)
    info = {

        'unk0': r.read(0x8 if plat['PtrSize'] == 4 else 0x10),
        # 0x0
        # 0x1
        # 0x2
        # 0x3
        # 0x4
        # 0x5
        # 0x6
        # 0x7
        # 0x8
        # 0x9
        # 0xA
        # 0xB
        # 0xC
        # 0xD
        # 0xE
        # 0xF

        'f_10': r.readPtr(), # Some optional function pointer

        "connector": r.readStr(),
        "return-pin": r.readStr(),
        "vplus-pin": r.readStr(),
        "voltage": r.readStr(),

        'id': r.parse("<H")[0], # ID from manual
        'element': r.parse("<H")[0], # Index into elements array  # 0x1E in spike 2

        'unkX': r.read(6),
        # 0x3C
        # 0x3D
        # 0x3E
        # 0x3F
        # 0x40
        # 0x41

        'f_42': r.parse("<H")[0], # count or index

        'f_44': r.parse("<H")[0], # count or index

        'f_46': r.parse("<H")[0],

        'return-wire-color': r.readMessage(),
        'vplus-wire-color': r.readMessage(),

        'unkY': r.read(3),
        # 0x4C
        # 0x4D
        # 0x4E

        'f_4F': r.parse("<B")[0],
        'f_50': r.parse("<H")[0],

        'unkZ': r.read(0x2 if plat['PtrSize'] == 4 else 6)
        # 0x52
        # 0x53
        # 0x54
        # 0x55
        # 0x56
        # 0x57
    }

    print("0x%X" % r.cursor)
    assert(r.cursor in [0x38, 0x58]) # Spike 2, Spike 3

    #   if ((uint)puVar3->field31_0x42 + (uint)puVar3->field32_0x44 != 0) {
    #       FUN_003a4a20(uVar2,puVar3->field_0x4f,puVar3->field31_0x42,puVar3->field_0x50,
    #                 puVar3->field32_0x44,puVar3->field33_0x46);
    
    return info






def collectGame():
    game = {}

    # Confirmed working on
    # Batman '66 V0.65.0
    if True:
        start, count = findMessageTable()
        game['MessageTable'] = start + imageBase
        game['MessageCount'] = count

    start, count = findBoardTable()
    game['JFR_board_table'] = start + imageBase
    game['JFR_board_count'] = count

    start, count = findBoardTypeTable()
    game['node_board_type_table_data'] = start + imageBase
    game['NODE_BOARD_DEVICE_TYPE_TABLE_DATA_ENTRY_COUNT'] = count

    start, count = findElementTable()
    game['ElementTable'] = start + imageBase
    game['ElementCount'] = count
    elstart = start


    # Hack to disable to work on older tables
    if True:
        start, count = findSwitchTable()
        swstart = start
        # Ends where the element table begins?!
        count = getCount(elstart - start, switchSize)
        game['JFR_switch_count'] = count
        game['JFR_switch_table_probably'] = start + imageBase

    if True:
        print("light")
        start, count = findLightTable()
        listart = start
        # Ends 0x20 bytes before swtable?
        guessed = 0x10 if plat['PtrSize'] == 4 else 0x20
        end = swstart - guessed
        count = getCount(end - start, lightSize)
        game['JFR_led_table'] = start + imageBase
        game['hook_node_board_device_led_table_data_entry_count'] = count

    if True:
        print("driver")
        start, count = findDriverTable()
        end = listart
        count = getCount(end - start, driverSize)
        # Ends in LED table?!
        game['UnkTable'] = start + imageBase
        game['UnkCount'] = count

    return game


# Designed for FotE 0.85 LE
def getBoardType(i):
    data = read(game['node_board_type_table_data'] + i * boardTypeSize - imageBase, boardTypeSize)

    r = Reader(data)
    info = {

        "part-string": r.readStr(),
        "part-number": r.readPtr(),
        "type": r.readStr(),
        "name": r.readStrTable(),
        'f_0x20': r.read(4).hex(),
        #'f_0x20': r.parse("<H")[0],
        #'f_0x22': r.parse("<H")[0],
        "pad?": r.read(0 if plat['PtrSize'] == 4 else 4).hex(), # assumed
    }

    print(info)
    print("0x%X" % r.cursor)
    assert(r.cursor in [0x14, 0x28]) # Spike 3

    return info




def main(path):
    global data
    global plat
    global game
    global imageBase

    if True:
        game = wdr_0_78_0_LE
        plat = spike3
        imageBase = 0x100000

    if True:
        game = starWarsFotE_0_85_0_LE
        plat = spike3
        imageBase = 0x100000

    if False:
        game = kingKongPro_0_88_0_Pro
        plat = spike2
        imageBase = 0

    if True:
        game = {
            'path': path,
            'alias': {}
        }

        # Ensure the path has a final slash
        game['path'] = game['path'].rstrip('/') + '/'


    binPath=game['path'] + '/game'

    imageBase, elf_reader, plat = readElf(binPath)
    setElfReader(imageBase, elf_reader, plat)

    global types
    types = {
        0: '???',
        1: "sw",
        2: "dr",
        3: "lp",
    }



    if False:
        for i in range(100):
            print(getMessage(i))

    global boardSize
    boardSize = 0x10 if plat['PtrSize'] == 4 else 0x20
    global boardTypeSize
    boardTypeSize = 0x14 if plat['PtrSize'] == 4 else 0x28
    global elementSize
    elementSize = 0x30 if plat['PtrSize'] == 4 else 0x50
    global switchSize
    switchSize = 0x28 if plat['PtrSize'] == 4 else 0x40
    global lightSize
    lightSize = 0x18 if plat['PtrSize'] == 4 else 0x28
    global driverSize
    driverSize = 0x38 if plat['PtrSize'] == 4 else 0x58    


    # Read entire file for searching
    elf_reader.f.seek(0)
    data = elf_reader.f.read()
    setData(data)


    oldGame = {} #kingKongPro_0_88_0_Pro
    newGame = {**oldGame, **game, **collectGame() }
    print(oldGame)
    print(newGame)


    game = newGame
    setGame(game)

    game['package'] = game['path'].split('/')[-2]

    if game['package'] == "star_wars_2025_le":
        game['alias'] = {
            "playfield": "TestMenu/buck_le_playfield" # 002e0700 FotE 0.85 LE
        }



    open("/tmp/game.json", 'wb').write(json.dumps(game, indent=2).encode())

    if 'node_board_type_table_data' in game:
        boardTypes = getTable(game['NODE_BOARD_DEVICE_TYPE_TABLE_DATA_ENTRY_COUNT'], getBoardType)
        dumpTable("table_boardTypes.csv", boardTypes)

    if 'MessageTable' in game:
        messages = getTable(game['MessageCount'], getMessage)
        dumpTable("table_messages.csv", messages)

    if 'ElementTable' in game:
        # es = plat['ElementSize']
        elements = getTable(game['ElementCount'], getElement)
        dumpTable("table_elements.csv", elements)

    if 'JFR_board_table' in game:
        boards = getTable(game['JFR_board_count'], getBoard)
        dumpTable("table_boards.csv", boards)

    # Dump switch table
    if 'JFR_switch_table_probably' in game:

        switches = getTable(game['JFR_switch_count'], getSwitch)
        dumpTable("table_switches.csv", switches)

        for info in switches:
            toManualSwitch(info)

    # Dump light table
    if 'JFR_led_table' in game:
        
        lights = getTable(game['hook_node_board_device_led_table_data_entry_count'], getLight)
        dumpTable("table_lights.csv", lights)

        for info in lights:
            toManualLight(info)

    # Dump the driver table
    if 'UnkTable' in game:

        drivers = getTable(game['UnkCount'], getDriver)
        dumpTable("table_drivers.csv", drivers)

        for info in drivers:
            toManualDriver(info)


if __name__ == "__main__":
    main(sys.argv[1])