#!/usr/bin/env python3

import struct
import wave
import sys

from helper import *


def main(path):
    imageBase, game, _ = readElf(path)

    if True:

        def find_adjustment_table_data():

                
            def check(x, hasSpike3Fields):
                if hasSpike3Fields:
                    # Expect to be followed by description
                    try:
                        if game.readStr(x + game.ptrSize) != "NO DESCRIPTION":
                            return []
                    except:
                        return []
                    x -= game.ptrSize
                    try:
                        if game.readStr(x) != 'INVALID':
                            return []
                    except:
                        return []
                    if game.ptrSize == 8:
                        x -= 4
                        if game.read32(x) != 0:
                            return []
                else:
                    # Expect to be followed by 4 zeros
                    if game.read32(x + game.ptrSize) != 0:
                        print("b1", "0x%X" % x)
                        return []

                print("c1")

                # Expect 5 zero values before this, and then one valid pointer
                for i in range(5):
                    x -= 4
                    if game.read32(x) != 0:
                        return []
                print("c2")
                x -= game.ptrSize
                if game.readPtr(x) == 0:
                    return []
                print("c3")
                return [x]



            for x in findCandidateStrTablePtrs([b"invalid\x00"] * 5):
                print("0x%X" % x)
                for x in check(x, True):
                    print("YES!")
                    yield x

                    # We consider this an exact match
                    return

            for x in findCandidateStrTablePtrs([b"INVALID\x00"] * 5):
                print("0x%X" % x)
                for x in check(x, False):
                    yield x


                



        x = list(find_adjustment_table_data())
        print(["0x%X" % (y+imageBase) for y in x])
        #assert(len(x) == 1)
        adjustment_table_data = x[0]
        assert(game.getSymbol('adjustment_table_data') in [adjustment_table_data, None])

        def find_adjustment_table():
                for x in findPtrCandidates(adjustment_table_data): # Required knowledge
                    yield x

        x = list(find_adjustment_table())
        print(["0x%X" % (y+imageBase) for y in x])
        #assert(len(x) == 1)
        adjustment_table = x[-1]
        assert(game.getSymbol('adjustment_table') in [adjustment_table, None])

        #adjustment_table = game.getSymbol('adjustment_table')

    else:

        # fote 0.85 LE:
        adjustment_table = 0x860010 - imageBase
        # adjustment_table_data = 0x872e80 ??

        # kingkong 0.88 pro
        adjustment_table = 0x6e2dc8
        # adjustment_table_data = 0x06f4110
              
        # All the 0x2C stuff is accidental stuff for this
        #   redemption_adjustment_table = 0x6e5950
        #   redemption_adjustment_table_data = 0x759280 ??



    adjustment_table_data = game.readPtr(adjustment_table + 0)
    ADJUSTMENT_TABLE_DATA_ENTRY_COUNT = game.readPtr(adjustment_table + game.ptrSize)
    elementSize = game.readPtr(adjustment_table + game.ptrSize * 2)

    assert(elementSize in [0x20, 0x2C, 0x40])

    for i in range(ADJUSTMENT_TABLE_DATA_ENTRY_COUNT):
        data = game.read(adjustment_table_data + i * elementSize, elementSize)

        hasSpike3Fields = elementSize in [0x2C, 0x40]

        r = Reader(data)
        r.setPtrSize(game.ptrSize)
        info = {
            'block_ram_ptr': r.readPtr(),
            'default': r.read32(),
            'min': r.read32(),
            'max': r.read32(),
            'step': r.read32(),
            'a4': r.read32(), # Maybe a divisor for storing values?
            'a5': r.read32() if game.ptrSize == 8 else None,
            'unkStr': r.readStr() if hasSpike3Fields else None,
            'localizedName': r.readStrTable(), # localized
            'descriptionStr': r.readStr() if hasSpike3Fields else None,
            'typeIndex': r.read16(),
            'a6': r.read16(),
            'a7': r.read16() if hasSpike3Fields else None,
            'a8': r.read16() if hasSpike3Fields else None,
        }
        print(r.cursor, len(r.data))
        assert(r.cursor == len(r.data))

        print(i, info)

        # Padding probably
        assert(info['a5'] in [None, 0])

        #assert(info['a4'] in [0, 1, 10, 1000000])
        #assert(info['a7'] in [None, 0, 2])
        #assert(info['a8'] in [None, 0, 8, 48, 49])


if __name__ == "__main__":
    main(sys.argv[1])