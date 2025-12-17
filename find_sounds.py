#!/usr/bin/env python3

# Working:
# spike-2	batman-66               	2017-01-11	(0, 65, 0)
# spike-2	guardians-of-the-galaxy-pro	2018-02-13	(0, 87, 0)
# spike-2	deadpool-pro	            2018-08-30	(0, 82, 0)
# spike-1	kiss-le	                    2018-12-11	(1, 41, 0)
# spike-1	whoa-nellie	                2019-01-25	(1, 55, 0)

# Not working:
# spike-2	elvira-house-of-horrors	    2020-10-15	(1, 0, 0)  (weird flash offsets / sidecar logic without sidecar)
# spike-1	can-crusher	                2020-12-22	(1, 2, 0)  (weird flash offsets / sidecar logic without sidecar)
# spike-1	primus	                    2020-12-22	(1, 4, 0)  (weird flash offsets / sidecar logic without sidecar)

# Games using a sidecar are not supported; examples:
# ./foo-fighters/foo_fighters_le-1_03_0.spk.uncompressed-squashfs/spk/foo_fighters_le-1_03_0/foo_fighters_le/image-sc17.bin
# ./dungeons-and-dragons/dungeons_and_dragons_pro-0_97_0.spk.uncompressed-squashfs/spk/dungeons_and_dragons_pro-0_97_0/dungeons_and_dragons_pro/image-sc01.bin
# ./john-wick/john_wick_le-0_98_0.Release.16G.sdcard.raw.squashfs/games/john_wick_le/image-sc02.bin
# ./john-wick/john_wick_le-0_99_0.spk.uncompressed-squashfs/spk/john_wick_le-0_99_0/john_wick_le/image-sc01.bin
# ./james-bond-007/james_bond_le-1_05_0.Release.16G.sdcard.raw.squashfs/games/james_bond_le/image-sc01.bin
# ./deadpool/deadpool_le-1_14_0.spk.uncompressed-squashfs/spk/deadpool_le-1_14_0/deadpool_le/image-sc01.bin
# ./metallica-remastered/metallica_spike-0_96_0.Release.32G.sdcard.raw.squashfs/games/metallica_spike/image-sc04.bin
# ./rush/rush_le-1_18_0.spk.uncompressed-squashfs/spk/rush_le-1_18_0/rush_le/image-sc05.bin


import struct
import wave
import sys

from helper import *
from search import *

has16BitScripts = True # Seems to have changed between 2018-12-11 (True) and 2019-01-25 (False)

def main(path):

    gamePath = path + "/game"
    imageBin = load(path + "/image.bin")

    imageBase, elf_reader, play = readElf(gamePath)
    game = elf_reader
    elf_reader = None # Discourage use

    def readAt(offset, size):
        return imageBin[offset:offset+size]


    # image.bin is in banks of 0x800000 bytes


    
    def find_sound_effect_table():

        def dummyTable(elementSize):
            ptr = "????????"
            elementCount = "????0000" # Assume elementCount is less than 16 bit
            elementSize = struct.pack("<L", elementSize).hex()
            return ptr + elementCount + elementSize


        kickback_table = dummyTable(0xC)
        sound_effect_table = dummyTable(0x14)
        skill_post_table = dummyTable(0xC)

        sig = kickback_table + sound_effect_table + skill_post_table
        print(sig)
        x = 0

        while True:
            x = find_signature(game.data, sig, x)
            if x == -1:
                break
            y = game._find_virtual_address_for_offset(x)
            y += 0xC # Skip kickback table
            print("0x%X" % y)
            yield y
            x += 1

    def find_hook_checksum_flash_location():
        expectedOffset = len(imageBin) - 4
        needle = struct.pack("<Q", expectedOffset)
        candidates = game.findCandidates(needle)
        for x in candidates:
            yield x

    def rel(base, offset):
        def fn():
            yield symbols[base] + offset
        return fn

    symbols = {}
    def set(name, generator):
        values = list(generator())
        assert(len(values) == 1)
        value = values[0]
        print("Setting %s: 0x%X" % (name, value))
        assert(name not in symbols)
        debugSymbolValue = game.find_va_for_symbol(name)
        if debugSymbolValue != None:
            print("Confirming! found 0x%X == 0x%X game?" % (value, debugSymbolValue))
            assert(value == debugSymbolValue)
        symbols[name] = value

    set('sound_effect_table', find_sound_effect_table)

    set('hook_checksum_flash_location', find_hook_checksum_flash_location)

    set('hook_game_config_flash_offset', rel('hook_checksum_flash_location', -8))
    set('hook_sound_config_flash_offset', rel('hook_game_config_flash_offset', -8))
    set('hook_font_table_entry_count', rel('hook_sound_config_flash_offset', -8))
    set('hook_font_table_flash_offset', rel('hook_font_table_entry_count', -8))
    set('hook_image_table_entry_count', rel('hook_font_table_flash_offset', -8))
    set('hook_image_table_flash_offset', rel('hook_image_table_entry_count', -8))
    set('hook_sound_script_table_entry_count', rel('hook_image_table_flash_offset', -8))
    set('hook_sound_script_table_flash_offset', rel('hook_sound_script_table_entry_count', -8))

    # Guardians 0.87 has 'hook_game_package_name' after 'hook_checksum_flash_location' which breaks the chain!
    # Whoa nellie 1.55 has 'hook_game_package_name' after 'hook_game_code_build_date'
    #set('hook_game_number', rel('hook_checksum_flash_location', 8))
    #set('hook_game_name_3_letter', rel('hook_game_number', 4))  
    #set('hook_game_name', rel('hook_game_name_3_letter', 4))
    #set('hook_game_code_build_date', rel('hook_game_name', 4))


        
    # Look at `sound_effect_request`
    sound_effect_table = symbols['sound_effect_table']
    sound_effect_table_data = game.read32(sound_effect_table + 0)
    SOUND_EFFECT_TABLE_DATA_ENTRY_COUNT = game.read32(sound_effect_table + 4)
    elementSize = game.read32(sound_effect_table + 8)
    entrySize = 4 * 5
    assert(elementSize == entrySize)

    print("0x%X" % SOUND_EFFECT_TABLE_DATA_ENTRY_COUNT)

    sound_effect_table_data = game.read(sound_effect_table_data, SOUND_EFFECT_TABLE_DATA_ENTRY_COUNT * entrySize)
    for i in range(SOUND_EFFECT_TABLE_DATA_ENTRY_COUNT):

        print("effect", i)
        offset = i * entrySize
        p0, p1, p2, ba0, ba1, ba2, ba3, b0, b1, b2, b3 = struct.unpack("<LLLBBBBBBBB", sound_effect_table_data[offset:offset + entrySize])    
        print(p0, p1, "0x%X" % p2, ba0, ba1, ba2, ba3, "0x%X" % b0, b1, b2, b3)
        # p0 history_list_ram
        # p1 history_list_index_ram
        # p2 = list of sound scripts [32 bit entries until the entry is 0?]

        # Probably a short ba0 | ba1
        assert(ba0 == 0)
        assert(ba1 == 0)

        # Probably a short: local_ssi_history_index?
        if False:
            assert(ba2 in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 15, 25]) # only seems to be higher when more scripts exist?
        assert(ba3 == 0)

        assert(b1 in [0, 1])

        # b0 = priority maybe?
        if False:
            if b1 == 0:
                assert(b0 in [0x00, 0x01, 0x81, 0xA0, 0xB0, 0xFD])
            else:
                assert(b0 in [0x01, 0x60, 0x70, 0x71, 0x72, 0x80, 0x81, 0x90, 0x91, 0x92, 0xB1, 0xC4, 0xDF, 0xF0, 0xF1, 0xF3, 0xF4, 0xF5, 0xF7, 0xF9, 0xFA, 0xFB, 0xFD, 0xFF])
        if False:
            if ba2 == 0:
                assert(b2 == 0)
            else:
                assert(b2 in [0, 1])
        assert(b3 == 0)

        offset = p2
        while True:
            
            x = game.read16(offset) if has16BitScripts else game.read32(offset)
            if x == 0:
                break
            print("  script ", x)
            offset += 2 if has16BitScripts else 4





                                                           
        
    


    # Unknown what the number is
    sscr_op_table = [
        ["SSCR_OP_INVALID", 0],     # 0x0
        ["SSCR_OP_ASSIGNFADER", 2], # 0x1
        ["SSCR_OP_ATTENUATION", 2], # 0x2
        ["SSCR_OP_ENDLOOP", 0],
        ["SSCR_OP_GLOBALFADER", 2], # 0x4
        ["SSCR_OP_HEADER", 6],
        ["SSCR_OP_JUMPMARKER", 0],  # 0x6
        ["SSCR_OP_LOOP", 1],
        ["SSCR_OP_MARKER", 4],  # 0x8
        ["SSCR_OP_MOVEFADER", 0xF],
        ["SSCR_OP_PLAY", 9],    # 0xA
        ["SSCR_OP_QUIET", 1],
        ["SSCR_OP_SETFADER", 2], # 0xC
        ["SSCR_OP_SIGNAL", 4],
        ["SSCR_OP_TRACKS", 1], # 0xE
        ["SSCR_OP_WAIT", 4], # 0xF
        ["SSCR_OP_WAITFOR", 1], # 0x10
        ["SSCR_OP_WAITSIGNAL", 8] # 0x11
    ]


    def get_script_data(x):
        if False:
            return x
        else:
            # Based on can-crusher `get_script_data`
            assert(False) #FIXME: Unfinished
            """
            tmp = bytearray([0,0,0,0])
            remap_tables = game.read(game.find_va_for_symbol('remap_tables'), 0x1000)
            for i in range(4):
                tmp[i] = tmp[i] ^ remap_tables[i + (scriptIndex * 4 & 0x3f00) + (scriptIndex & 0x7f)]
            return remap_tables + ((local_20._0_4_ ^ 0x54434824) & 0x5f5)
            """



    soundConfigSize = 12 #FIXME: At least. It might be longer
    if True:
        hook_sound_config_flash_offset = game.read64(symbols['hook_sound_config_flash_offset'])
    else:
        # Based on can-crusher `sys_sound_get_sound_config_pdi` -> `sys_flash_memory_sidecar_get_asset_ptr_pdi(0,2)``
        assert(False) #FIXME: Does not work, wtf are they doing?
        arg2 = 2
        offset = 24 + arg2 * 8
        print(offset)
        hook_sound_config_flash_offset = struct.unpack("<L", readAt(offset, 4))[0]

    print("0x%X" % hook_sound_config_flash_offset)
    soundConfig = readAt(hook_sound_config_flash_offset, soundConfigSize)
    someOffset, unkB, sampleRate = struct.unpack("<LLL", soundConfig)
    # byte+7 appears to be number of languages?
    print(someOffset, unkB, sampleRate)

    offset = 0
    hook_sound_script_table_entry_count = game.read32(symbols['hook_sound_script_table_entry_count'])
    print("0x%X scripts" % hook_sound_script_table_entry_count)
    for i in range(hook_sound_script_table_entry_count):
        size = 8 * 5 # Probably 8 bytes per entry, and 5 languages
        x = readAt(game.read64(symbols['hook_sound_script_table_flash_offset']) + offset, size)
        print(i, x.hex())
        offset += size

        la, lb, lc, ld, le = struct.unpack("<QQQQQ", x)
        assert(lb == la)
        assert(lc == la)
        assert(ld == la)
        assert(le == la)

        so = 0
        print("  script", readAt(la, 20).hex())
        while True:
            command = readAt(la + so, 1)[0]
            print("  command 0x%02X" % command, end=" ")
            print(sscr_op_table[command][0], end=" ")
            l = sscr_op_table[command][1]
            args = readAt(la + so + 1, l)
            print(args.hex())
            so += 1 + l

            if command == 0x0A:
                # SSCR_OP_PLAY
                #   1 byte channel maybe
                #   4 byte offset?
                #   4 byte unknown [always zero anyway?]
                unkA, unkOffset, unkC = struct.unpack("<BLL", args)

                # Offset +7 is a byte for the codec
                # 0 = raw
                # 1 = adpcm

                print("   >>", unkA, unkOffset)
                assert(unkC == 0)


                # Read sound
                sound = readAt(unkOffset, 8)
                duration, channels, unkB, unkC, codec = struct.unpack("<LBBBB", sound)
                assert(channels in [1, 2])
                assert(unkB == 0)
                print(unkC)
                assert(unkC in [1, 2])
                assert(codec in [0, 1])

                print("   >>>>>>", sound.hex(), "duration=%.4fs" % (duration / sampleRate))

                padEnd = 100 # Because we don't know where we start and end

                y = readAt(unkOffset + 8, duration * channels * 2 + padEnd)


                name = "/tmp/sound%d_%d" % (i, unkC)
                open(name + ".bin", "wb").write(y)

                if codec == 0:
                    with wave.open(name + ".wav", mode="wb") as wav_file:
                        wav_file.setnchannels(channels)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sampleRate)
                        wav_file.writeframes(y[0:-padEnd])
                elif codec == 1:
                    assert(False)
                

            elif command == 0x00:
                # SSCR_OP_INVALID
                break
        

    gameConfigSize = 100 # FIXME: Unknown
    hook_game_config_flash_offset = game.read64(symbols['hook_game_config_flash_offset'])
    gameConfig = readAt(hook_game_config_flash_offset, gameConfigSize)
    print(gameConfig.hex())
    print(gameConfig)


if __name__ == "__main__":
    main(sys.argv[1])