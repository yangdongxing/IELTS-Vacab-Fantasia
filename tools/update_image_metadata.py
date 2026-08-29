#!/usr/bin/env python3
"""
Batch Metadata Updater for IELTS-Vocab-Fantasia Images
Losslessly updates XMP / IPTC metadata across all JPEG images:
- Sets Credit: "IELTS-Vocab-Fantasia"
- Sets Creator: "yangdongxing"
- Sets Copyright: "© yangdongxing"
- Strips legacy AI generation tags (Made with Google AI / Created using Generative AI)
"""

import os
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "assets" / "images"

CREDIT_TEXT = "IELTS-Vocab-Fantasia"
CREATOR_TEXT = "yangdongxing"
COPYRIGHT_TEXT = "© yangdongxing"

XMP_XML = f'''<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 6.0.0">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
    xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"
    photoshop:Credit="{CREDIT_TEXT}"
    xmpRights:Marked="True">
   <dc:creator>
    <rdf:Seq>
     <rdf:li>{CREATOR_TEXT}</rdf:li>
    </rdf:Seq>
   </dc:creator>
   <dc:rights>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{COPYRIGHT_TEXT}</rdf:li>
    </rdf:Alt>
   </dc:rights>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''.strip()

XMP_PAYLOAD = b'http://ns.adobe.com/xap/1.0/\x00' + XMP_XML.encode('utf-8')
XMP_MARKER = b'\xff\xe1' + (len(XMP_PAYLOAD) + 2).to_bytes(2, 'big') + XMP_PAYLOAD


def process_jpeg(file_path: Path) -> bool:
    try:
        data = file_path.read_bytes()
        if len(data) < 4 or data[:2] != b'\xff\xd8':
            return False

        pos = 2
        out = [b'\xff\xd8']
        inserted_xmp = False

        while pos < len(data) - 1:
            if data[pos] != 0xFF:
                out.append(data[pos:])
                break
            marker = data[pos + 1]
            if marker in (0xD8, 0xD9):
                pos += 2
                continue
            if marker == 0xDA:  # Start of Scan (SOS)
                if not inserted_xmp:
                    out.append(XMP_MARKER)
                    inserted_xmp = True
                out.append(data[pos:])
                break

            if pos + 4 > len(data):
                out.append(data[pos:])
                break

            length = (data[pos + 2] << 8) | data[pos + 3]
            seg = data[pos:pos + 2 + length]
            pos += 2 + length

            # Replace existing XMP segment
            if marker == 0xE1 and seg[4:].startswith(b'http://ns.adobe.com/xap/1.0/'):
                out.append(XMP_MARKER)
                inserted_xmp = True
                continue

            # Strip legacy Photoshop IPTC segment (containing Google AI tags)
            if marker == 0xED and seg[4:].startswith(b'Photoshop 3.0'):
                continue

            out.append(seg)

        new_data = b''.join(out)
        if new_data != data:
            file_path.write_bytes(new_data)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path.name}: {e}", file=sys.stderr)
        return False


def main():
    if not IMAGES_DIR.exists():
        print(f"Images directory not found: {IMAGES_DIR}", file=sys.stderr)
        sys.exit(1)

    files = [IMAGES_DIR / f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg'))]
    print(f"Found {len(files)} JPEG images in {IMAGES_DIR}")
    print(f"Applying metadata:")
    print(f"  • Credit:            {CREDIT_TEXT}")
    print(f"  • Creator:           {CREATOR_TEXT}")
    print(f"  • Copyright:         {COPYRIGHT_TEXT}")
    print(f"  • Legacy AI tags:    Stripped")

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_jpeg, files))

    updated_count = sum(1 for r in results if r)
    print(f"\nDone! Successfully updated metadata for {updated_count}/{len(files)} images.")


if __name__ == "__main__":
    main()
