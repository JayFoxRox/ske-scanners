#!/usr/bin/env python3

import sys
import struct

from helper import *

def main(path):
    data = load(path)

    # fixup path to only reveal Stern names (or similar)
    if True:
        path = path.partition("squashfs/")[0]
        path = path.partition("-secure/")[0]
        path = path.rpartition("/")[2]
        path = path.strip(".")
        path = path.removesuffix(".uncompressed-")

    print()
    print(path)


    machine = data[0x12]

    if machine == 0x28: # ARM
        codesize = 4
        entrySize = 12
        entryFormat = "<LLL"
    elif machine == 0xB7: # aarch64
        codesize = 8
        entrySize = 24
        entryFormat = "<QQQ"
    else:
        print("Unknown arch 0x%X" % machine)


    def letters(bs):
        l = ""
        t = ""
        vs = []
        for i in range(codesize):
            v = bs[i]
            if v == 0:
                break

            sym = ord('A') + v - 1

            if sym >= ord('A') and sym <= ord('Z'):
                t += "%c" % (sym)
            else:
                t += "?"
        return t # " ".join(["%d" % x for x in bs[0:2]]) + " | " + t

    def read(offset, size):
        return data[offset:offset+size]


    # Turn letters into code
    def code(s):
        b = bytes([(ord(x) - ord('A') + 1) for x in s])
        b = (b + b'\x00' * codesize)[0:codesize]
        return b

    def findOne(s, offset=0):
        x = data.find(s, offset)
        if x != -1:
            assert(findOne(s, x+1) == -1)
        return x

    # These appear in every game since Spike 1
    b = code("HDG") + code("FNF")
    x = findOne(b)
    if x == -1:
        print("NONE", path)
        sys.exit(1)

    # Scan backward
    start = x - codesize
    while not b'\x00' in read(start, 3):
        start -= codesize
    start += codesize

    # Scan forward
    end = x + 2 * codesize
    while not b'\x00' in read(end, 3):
            end += codesize
    #end += codesize

    print("OFFSET", "0x%X" % start, path)

    size = end - start
    assert(size % codesize == 0)
    count = size // codesize
    print("COUNT", count, path)


    # Before the code list, there'll be the actual table using these codes
    # These's one more entry for ee_invalid, but we currently ignore it
    startEntries = start - entrySize * count


    for i in range(count):

        startEntry = startEntries + i * entrySize

        entry = read(startEntry, entrySize)
        codeAddress, callbackAddress, flags = struct.unpack(entryFormat, entry)
        #print("ENTRY", "@", startEntry, "=", codeAddress, callbackAddress, flags)

        # Code list is reversed order from entry list
        codeAddressAssumed = (end - codesize) - i * codesize
        #print("CODE", "@", codeAddressAssumed)

        #FIXME: Need to map virtual address to file offset
        #assert(fileOffset(codeAddress) == codeAddressAssumed)
    
        v = read(codeAddressAssumed, codesize)


        




        """
        EOL [5, 15, 12] metallica # Calls unknownFunction(0x18), removed in later versions. Probably related to "The End Of the Line" (song or mode)
        
        IRS [9, 18, 19] beatles
        SRG [19, 18, 7] beatles

        Q?E [17, 27, 5] bond-60th

        LKP [12, 11, 16] avengers-infinity, led-zeppelin, rush, turtles
        RED [18, 5, 4] led zeppelin, rush
        """

        knownCodes = {
            "ABC": "Credits",

            # Tested on DnD by yuut: https://discord.com/channels/1430023971725774860/1432922437590192138/1436591412270333952
            "JAJ": 'Flip N Out Pinball Podcast / DND: Shows drawn picture "The Silverball Struggles of Joel and Jared"',
            "TDP": "Triple Drain Pinball podcast logo",
            "DCE": "LoserKid Pinball podcast logo",

            # Many of these come from bdash
            "DEA": "Deadflip",
            "KME": "Keith Elwin",
            "RAY": "raydaypinball (Raymond Davidson) video clip on Foo Fighters",
            "RJN": "Rick Naegele",
            "ADG": "Dean Grover? code_list_ee_hello_world in star-wars-elg (only does `sys_proc_sleep(1)` ?)", # https://www.ipdb.org/search.pl?searchtype=advanced&ppl=Dean%20Grover
            "ZYT": "Zombie Yeti",
            "JHD": "Harrison Drake",
            "JDT": "Jerry Thompson",
            "RON": "Ron Ivan Staley?", # goltz in GOT
            "DSD": "code_list_ee_mcalpine GOT / COLIN MCALPINE",

            "DRO": 'code_list_ee_tonybread SoR / "Tony Bread Always Wins" on Led Zeppelin', 
            "HNW": 'SoR / NICK WEYNA was (first) mentioned in same release? / "Happy Thanksgiving" On Led Zeppelin',

            # This has a bunch of similar ones: https://pinside.com/pinball/forum/topic/machines-that-have-references-to-other-machines#post-2192870
            "MJD": "code_list_ee_mdoran GOT / MIKE DORAN",
            "PMA": "code_list_ee_mandletort GOT / PAUL MANDLETORT",
            "ERW": "code_list_ee_wurt GOT / ERIK WURTENBERGER",
            "CFA": "code_list_ee_frolic GOT / CHRIS FROLIC",
            "FBE": 'code_list_ee_johndng GOT / "HIYA JOHN"', #FIXME not sure what actual person this is
            "GXH": "code_list_ee_genex GOT / GENE X HWANG",
            "SKB": 'code_list_ee_skb in GOT / "HIYA STEVE" / "THANK YOU FOR YOUR HELP" STEVE BREITEL?',

            "TTA": "code_list_ee_trent GOT / TRENT AUGENSTEIN",
            # GAD and CCC on DnD both have a flag set that allows them to be entered outside of attract mode.
            # And they both do the same thing. I'm not entirely clear what that is, though.
            "GAD": "code_list_ee_xaqery GOT / Dwight Sullivan?" + # bdash said so
                'Shows "Reality is the fantasy of the majority" on turtles',

            "CFE": "code_list_ee_chris_f munsters / Chris Franchi", # "Christopher Franchi"
            "DDF": "code_list_ee_sc_group munsters",
            "DBA": 'code_list_ee_ascii_message munsters; Revealed in scorearea by the lamps which ASCII encode the flippercode / Shows a secret code and instructions; on munsters',
            "DAD": 'code_list_ee_ascii_unlock munsters / Secret Mania on munsters (Shows "Welcome To The Munsters" message. Complete Grandpa\'s Mode twice to unlock Secret Mania Mode)',

            # Turtles
            "AIG": "on Turtles is something to do with Marc Silk, a voice actor on the game",
            "DDF": "on turtles picture of Dwight", # says bdash

            # Godzilla
            "DGR": 'on godzilla photo of a cat with "ALL HAIL DODGER"', # Tested by bdash on Godzilla: https://discord.com/channels/1430023971725774860/1432922437590192138/1436785598798102711
            "TRX": 'on godzilla TRIXIE / plays mothra sound + photo of rich cat and "I haz ur ATM codez"', # Tested by yuut on Godzilla: https://discord.com/channels/1430023971725774860/1432922437590192138/1436566050090127392

            "GAG": "George Gomez?",
            "JCR": "Johnny Crap",

            "FLN": 'Shows photo of a cat on pinball-machine, "Flynn / KME\'s Playtester" on Jurassic Park', # Tested by yuut on Jurassic Park: https://discord.com/channels/1430023971725774860/1432922437590192138/1436473531906129970

            # Bond
            "KEN": "Ken Walker, aka jetsurgeon?",
            "TOF": "uses string TAILS / TEB",
            "TOG": "uses strings EMMER B",


            # Some more info by bdash
            # Related code: https://discord.com/channels/1430023971725774860/1432922437590192138/1436462823990628443
            # Photo of debug overlay: https://discord.com/channels/1430023971725774860/1432922437590192138/1436463731029573695
            "ADJ": "Show hidden adjustments",
            # It's identical in implementation to ADJ, but with the `FG_SHOW_HIDDEN_AUDITS` flag
            "AUD": "toggles hidden audits",

            # Tested on DnD by yuut: https://discord.com/channels/1430023971725774860/1432922437590192138/1436582180481531955
            "CCC": "Hello, World", 

            # Available on most games, usually after game specific codes before system codes
            "???": "Toggle temporary highscore mode", # only [99, 99, 99], sys_hstd_toggle_temporary_high_score_mode

            # System ones, usually coming last
            "DIA": "Diagnostics", # Missing from WWE 1.17
            "HDG": "Serial number (Hardware diagnostics)",
            "FNF": "Fatal and non-fatal errors",
            "BLK": "Black screen count" # Only on Spike 2 (?)
        }

        s = letters(v)

        def dumpFlags(flags):
            flagNames = {
                1: "(Not just in attract mode)", 
                4: "FLAG-4" # Typically used on 99,99,99
            }
            c = []
            for flagValue, flagName in flagNames.items():
                if flags & flagValue:
                    c += [flagName]
                    flags &= ~flagValue
            if flags != 0:
                c += ["FLAGS-0x%X" % flags]
            #assert(flags == 0)
            return c # " | ".join(c)

        print(s, list(v.partition(b'\x00')[0]), knownCodes.get(s, "UNKNOWN"), "cb=0x%X" % callbackAddress, "flags=" + str(dumpFlags(flags)), path)
        

    data.close()

if __name__ == "__main__":
    main(sys.argv[1])