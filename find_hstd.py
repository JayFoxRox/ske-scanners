#!/usr/bin/env python3

import struct
import wave
import sys

from helper import *


def main(path):
    imageBase, game, _ = readElf(path)

    #hstd_entry_table = game.getSymbol('hstd_entry_table')

    def find_hstd_entry_table_data():
        for x in findCandidateStrTables([b"INV\x00", b"INVALID\x00"]):
            yield x - game.ptrSize

    x = list(find_hstd_entry_table_data())
    print(["0x%X" % (y+imageBase) for y in x])
    assert(len(x) == 1)
    hstd_entry_table_data = x[0]
    assert(game.getSymbol('hstd_entry_table_data') in [hstd_entry_table_data, None])

    def find_hstd_entry_table():
        for x in findPtrCandidates(hstd_entry_table_data): # Required knowledge
            yield x

    x = list(find_hstd_entry_table())
    print(["0x%X" % (y+imageBase) for y in x])
    #assert(len(x) == 1)
    hstd_entry_table = x[-1]
    assert(game.getSymbol('hstd_entry_table') in [hstd_entry_table, None])


    #FIXME: Can be found by looking for { &"INV", &"INVALID" }
    hstd_entry_table_data_ = game.readPtr(hstd_entry_table)
    HSTD_ENTRY_TABLE_DATA_ENTRY_COUNT = game.readPtr(hstd_entry_table + game.ptrSize)
    elementSize = game.readPtr(hstd_entry_table + game.ptrSize * 2)

    assert(hstd_entry_table_data == hstd_entry_table_data_)
    print(HSTD_ENTRY_TABLE_DATA_ENTRY_COUNT, elementSize)

    assert(elementSize in [0x20, 36, 0x40])

    for i in range(HSTD_ENTRY_TABLE_DATA_ENTRY_COUNT):
        data = game.read(hstd_entry_table_data + i * elementSize, elementSize)

        r = Reader(data)
        r.setPtrSize(game.ptrSize)
        info = {
            'block_ram_ptr': r.readPtr(), # like `hse_invalid_hstd_block_ram`
            'playerInitials': r.readStr(),
            'playerName': r.readStr(),
            'initials_from_ds_fn_ptr': r.readPtr(), # like `sys_hstd_set_hstd_initials_from_ds``
            'unk': r.readPtr(), # Padding maybe?
            'unkNew': r.readStr() if elementSize in [36, 0x40] else None, # Only on some games?
            'localizedName': r.readStrTable(),
            'unk0': r.read16(), # Probably offset into another table or type of some sort
            'scoreAdjustmentIndex': r.read16(),
            'awardAdjustmentIndex': r.read16(),
            'awardsAdjustmentIndex': r.read16()
        }
        print(r.cursor)
        assert(r.cursor == len(r.data))

        print(i, info)

        #assert(info['unk'] == 0)

        # 0 seen on INVALID
        # 1 seen on grand champion
        # 3 seen on anything else
        assert(info['unk0'] in [0, 1, 3])

        
if __name__ == "__main__":
    main(sys.argv[1])