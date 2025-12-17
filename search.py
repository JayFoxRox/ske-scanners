# Vibe coded

def find_signature(mm, sig, offset):

    # ---- normalize signature (ignore spaces) ----
    sig = sig.replace(" ", "")
    if len(sig) % 2 != 0:
        raise ValueError("signature length must be even")

    tokens = [sig[i:i+2] for i in range(0, len(sig), 2)]

    # ---- parse signature ----
    pat = []
    mask = []
    for tok in tokens:
        if tok == "??":
            pat.append(0)
            mask.append(0)
        else:
            b = int(tok, 16)
            pat.append(b)
            mask.append(1)

    pattern = bytes(pat)
    plen = len(pattern)
    size = len(mm)

    # ---- collect valid known-byte runs ----
    runs = []
    i = 0
    while i < plen:
        if mask[i]:
            start = i
            buf = []
            while i < plen and mask[i]:
                buf.append(pattern[i])
                i += 1

            run = bytes(buf)

            # ignore all-00 or all-FF anchors
            if not (all(b == 0x00 for b in run) or
                    all(b == 0xFF for b in run)):
                runs.append((start, run))
        i += 1

    if not runs:
        raise ValueError("no usable anchor (all wildcards or 00/FF runs only)")

    # ---- choose best anchor: longest run ----
    anchor_off, anchor_bytes = max(runs, key=lambda r: len(r[1]))

    # ---- scan ----
    pos = offset + anchor_off
    while True:
        pos = mm.find(anchor_bytes, pos)
        if pos == -1:
            return -1

        start = pos - anchor_off
        if start < 0 or start + plen > size:
            pos += 1
            continue

        # masked verify (no slicing)
        for i in range(plen):
            if mask[i] and mm[start + i] != pattern[i]:
                break
        else:
            return start

        pos += 1
