from elftools.elf.elffile import ELFFile

import struct
import mmap

#FIXME: Pass explicitly
data = None
def setData(newData):
    global data
    data = newData
imageBase = None
elf_reader = None
plat=None
def setElfReader(newImageBase, newElfReader, newPlat):
    global imageBase
    global elf_reader
    global plat
    imageBase = newImageBase
    elf_reader = newElfReader
    plat = newPlat
game = None
def setGame(newGame):
    global game
    game = newGame


def mmapFile(f):
    return mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)

def load(path):
    f = open(path, 'rb')
    return mmapFile(f)


spike2 = {
    'PtrSize': 4,
    'ElementSize': 0x30,
    'ElementStruct': "<LLLLLLLHHHHHHHHHH"
}

spike3 = {
    'PtrSize': 8,
    'ElementSize': 0x50,
    'ElementStruct': "<QQQQQQQHHHHHHHHHHHH",
}



class Reader:
    def __init__(self, data):
        self.data = data
        self.cursor = 0
        self.ptrSize = 0
    def setPtrSize(self, ptrSize):
        self.ptrSize = ptrSize
    def read(self, offset, size=None):
        #print("Reading at 0x%X" % self.cursor)
        
        # If we only have an offset, that was meant to be the size
        if size == None:
            return self.read(None, offset)

        if offset != None:
            self.cursor = offset
        self.cursor += size
        return self.data[self.cursor-size:self.cursor]
    def parse(self, format):
        return struct.unpack(format, self.read(self.cursor, struct.calcsize(format)))
    def readPtr(self):
        return self.parse("<L" if self.ptrSize == 4 else "<Q")[0]
    def readStr(self): #FIXME: Misnomer!
        ptr = self.readPtr()
        return self.readStrData(ptr)
    def readStrTable(self):
        ptr = self.readPtr()
        return readStrTable(ptr)
    def readMessage(self):
        return getMessage(self.parse("<H")[0])
    def check(self, cursor):
        assert(self.cursor == cursor)

    def seek(self, cursor):
        self.cursor = cursor  

    # Some hacks for absolute reading
    def read16(self, offset):
        return struct.unpack("<H", self.read(offset, 2))[0]
    def read32(self, offset):
        return struct.unpack("<L", self.read(offset, 4))[0]
    def read64(self, offset):
        return struct.unpack("<Q", self.read(offset, 8))[0]
    def readStrData(self, offset):
        if offset == 0:
            return None
        s = self.read(offset, 2048)
        s, zero, _ = s.partition(b'\x00')
        assert(zero == b'\x00')
        return s.decode()



class ELFReader(Reader):
    def __init__(self, elf_path):
        print("Loading %s" % elf_path)
        self.f = open(elf_path, 'rb')
        self.elf = ELFFile(self.f)
        self.elf_path = elf_path

        super().__init__(mmapFile(self.f))


        machine = self.elf.header['e_machine']
                
        if machine == "EM_ARM": # (ARM architecture)
            #plat = spike2
            #imageBase = 0
            self.setPtrSize(4)
        elif machine == "EM_AARCH64": # (AArch64 architecture)
            #plat = spike3
            #imageBase = 0x100000  
            self.setPtrSize(8)
        else:
            print(f"Unknown architecture: {machine}")

        symtab = self.elf.get_section_by_name('.symtab')
        if symtab is None:
            self.elfSymbols = None
        else:
            self.elfSymbols = {}
            for sym in symtab.iter_symbols():
                name = sym.name
                #assert(not name in self.elfSymbols)
                self.elfSymbols[name] = sym['st_value']  # virtual address

    def find_va_for_symbol(self, symbol_name):
        if self.elfSymbols == None:
            return None
        return self.elfSymbols[symbol_name]

    def _find_segment_for_address(self, virtual_address):
        """
        Finds the segment containing the virtual address.
        """
        for segment in self.elf.iter_segments():

            segment_vaddr = segment['p_vaddr'] #+ imageBase
            segment_size = segment['p_memsz']
            segment_offset = segment['p_offset']
             

            if segment['p_type'] == 'PT_LOAD':  # Only consider loaded segments

                #print("checking", segment, "0x%X" % segment_vaddr, "-", "0x%X" % (segment_vaddr+segment_size-1), "from", "0x%X" % segment_offset)

                # Check if the virtual address falls within this segment's range
                if segment_vaddr <= virtual_address < segment_vaddr + segment_size:
                    return segment, segment_vaddr, segment_offset
        raise ValueError(f"Virtual address {hex(virtual_address)} not within any loaded segment.")

    def _find_virtual_address_for_offset(self, file_offset):
        """
        Finds the virtual address corresponding to the given file offset.
        """
        for segment in self.elf.iter_segments():
            
            segment_vaddr = segment['p_vaddr']
            segment_size = segment['p_memsz']
            segment_offset = segment['p_offset']
            segment_filesz = segment['p_filesz']

            if segment['p_type'] == 'PT_LOAD':  # Only consider loaded segments

                # Check if the file offset falls within this segment's file range
                if segment_offset <= file_offset < segment_offset + segment_filesz:
                    # Compute the corresponding virtual address
                    virtual_address = segment_vaddr + (file_offset - segment_offset)
                    return virtual_address

        raise ValueError(f"File offset {hex(file_offset)} not within any loaded segment.")

    def _find_section_for_address(self, virtual_address):
        """
        Finds the section containing the given virtual address.
        """
        for section in self.elf.iter_sections():
            
            section_name = section.name
            section_vaddr = section['sh_addr']
            section_size = section['sh_size']

            # Check if the virtual address falls within this section's range
            if section_vaddr <= virtual_address < section_vaddr + section_size:
                return section_name

        raise ValueError(f"Virtual address {hex(virtual_address)} not within any section.")

    def _get_offset_by_section_name(self, section_name):
        """
        Finds the file offset corresponding to the given section name.
        """
        for section in self.elf.iter_sections():
            
            if section.name == section_name:
                # Return the file offset of the section
                return section['sh_offset']
        
        raise ValueError(f"Section with name '{section_name}' not found.")

    def read(self, virtual_address, size):
        """
        Read `size` bytes starting from the given `virtual_address`.
        """
        # Find the segment that holds the given virtual address
        segment, segment_vaddr, segment_offset = self._find_segment_for_address(virtual_address)
        
        # Calculate the offset within the segment
        offset_within_segment = virtual_address - segment_vaddr
        
        # Verify that the read will not go beyond the segment's memory size
        if offset_within_segment + size > segment['p_memsz']:
            raise ValueError("Attempt to read beyond segment memory bounds.")
        
        # Seek to the correct position in the file
        self.f.seek(segment_offset + offset_within_segment)
        return self.f.read(size)

    def findCandidates(self, pattern):
        offset = 0
        while True:
            offset = self.data.find(pattern, offset)
            if offset == -1:
                break
            
            found_offset = offset
            offset += 1

            try:
                va = self._find_virtual_address_for_offset(found_offset)
                sn = self._find_section_for_address(va)

                #print(sn)
                if sn in ['.rela.dyn']: # Avoid relocations
                    continue

                yield va

            except:
                pass



def readElf(binPath):
    # Example usage:
    elf_reader = ELFReader(binPath)

    machine = elf_reader.elf.header['e_machine']
    print(machine)
            
    if machine == "EM_ARM": # (ARM architecture)
        plat = spike2
        imageBase = 0
    elif machine == "EM_AARCH64": # (AArch64 architecture)
        plat = spike3
        imageBase = 0x100000  
    else:
        print(f"Unknown architecture: {machine}")

    return imageBase, elf_reader, plat


def read(offset, size):
    return elf_reader.read(offset, size)

def readStr(offset):
    return elf_reader.readStrData(offset)

def readStrTable(ptr):
    result = []
    for i in range(5):
        result += [readStr(readPtr(ptr))]
        ptr += plat['PtrSize']
    return {
        'en': result[0],
        'de': result[1],
        'fr': result[2],
        'sp': result[3],
        'it': result[4]
    }
    

def readPtr(offset):
    reader = Reader(data)
    return reader.read32(offset) if plat['PtrSize'] == 4 else reader.read64(offset)

def getMessage(index):
    print("message", index)
    addr = game['MessageTable'] + index * plat['PtrSize'] - imageBase
    #print("Reading 0x%X" % addr)
    ptr = readPtr(addr) # FIXME: Reloc should not have to be applied!
    #print("Reading 0x%X" % ptr)
    #ptr = readPtr(ptr)
    #print("Reading 0x%X" % ptr)
    return readStrTable(ptr)


def findCandidates(pattern):
    for x in elf_reader.findCandidates(pattern):
        yield x



# Returns VA!
def findPtrCandidates(offset):
    pattern = struct.pack("<L" if plat['PtrSize'] == 4 else '<Q', offset)
    for candidate in findCandidates(pattern):
        yield candidate

def has(va, pattern):
    try:
        return elf_reader.read(va, len(pattern)) == pattern
    except:
        return False

# Returns VA!
def findCandidateStrTables(texts):
    for candidate in findCandidates(texts[0]):
        for ptr in findPtrCandidates(candidate): # Get XREF to string
            print("ptr", hex(ptr))

            i = 1
            isMatch = True
            for text in texts[1:]:
                # Check if this is a localized table
                if not has(readPtr(ptr + i * plat['PtrSize']), texts[i]):
                    isMatch = False
                    break
                i += 1
            if not isMatch:
                continue

            yield ptr

def findCandidateStrTablePtrs(texts):
    for ptr in findCandidateStrTables(texts):
        for ptr in findPtrCandidates(ptr): # Get XREF to table
            yield ptr



def getCount(containerSize, elementSize):
    assert(containerSize % elementSize == 0)
    return containerSize // elementSize


