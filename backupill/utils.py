import os
import qrcode
import logging
from pyx import *
import subprocess
from tempfile import mkstemp


__all__ = ["generate_backup", "restore_backup"]

TEXT_X_OFFSET = 0.6
TEXT_Y_OFFSET = 8.2
PLAINTEXT_MAXLINECHARS = 73

QRCODE_HEIGHT = 8
QRCODE_PER_PAGE = 6
QRCODE_MAX_BYTE = 140
QRCODE_X_POS = [1.5, 11, 1.5, 11, 1.5, 11]
QRCODE_Y_POS = [18.7, 18.7, 10, 10, 1.2, 1.2]

PF_STR = "A4"
PF_OBJ = document.paperformat.A4

# suppressing all the warnings
for name in logging.Logger.manager.loggerDict.keys():
    logging.getLogger(name).setLevel(logging.CRITICAL)


def _generate_barcode(chunkdata: str) -> object:
    """Generates data barcode image."""

    qr = qrcode.QRCode(
        version=1,
        border=4,
        box_size=10,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
    )
    qr.add_data(chunkdata)
    qr.make(fit=True)

    im = qr.make_image(fill_color="black", back_color="white")

    return im


def _finish_page(pdf: object, canvas: object, pageno: int) -> None:
    """Adds numbers to bottom of the page."""

    canvas.text(10, 0.6, "Page {}".format(pageno + 1))
    pdf.append(document.page(canvas, paperformat=PF_OBJ, fittosize=0, centered=0))


def generate_backup(file: str) -> None:
    """Generates PDF backup file

    Args:
        file (str): File path
    """

    pageno = 0
    pageid = 0
    codeblocks = []
    chunkdata = "^1 "
    c = canvas.canvas()

    with open(file) as f:
        ASCDATA = f.read()

    unit.set(defaultunit="cm")
    pdf = document.document()

    for char in list(ASCDATA):
        if len(chunkdata) + 1 > QRCODE_MAX_BYTE:
            codeblocks.append(_generate_barcode(chunkdata))
            chunkdata = "^" + str(len(codeblocks) + 1) + " "
        chunkdata += char

    codeblocks.append(_generate_barcode(chunkdata))

    for bc in range(len(codeblocks)):
        if pageid >= QRCODE_PER_PAGE:
            _finish_page(pdf, c, pageno)
            c = canvas.canvas()
            pageno += 1
            pageid = 0

        c.text(
            QRCODE_X_POS[pageid] + TEXT_X_OFFSET,
            QRCODE_Y_POS[pageid] + TEXT_Y_OFFSET,
            "{} ({}/{})".format(
                text.escapestring(file.split(os.sep)[-1]), bc + 1, len(codeblocks)
            ),
        )

        c.insert(
            bitmap.bitmap(
                QRCODE_X_POS[pageid],
                QRCODE_Y_POS[pageid],
                codeblocks[bc],
                height=QRCODE_HEIGHT,
            )
        )

        pageid += 1

    _finish_page(pdf, c, pageno)

    fd, temp_barcode_path = mkstemp(".pdf", "qr_", ".")
    pdf.writetofile(temp_barcode_path)
    os.rename(temp_barcode_path.split(os.sep)[-1], "{}.pdf".format(file))


def restore_backup(file: str) -> int:
    """Restore PDF backup file

    Args:
        file (str): File path

    Returns:
        int: Return code
    """

    cmd = (
        "zbarimg --raw -Sdisable -Sqrcode.enable {}" + " | "
        r"sed -e 's/\^/\x0/g'" + " | "
        "sort -z -n" + " | "
        r"sed ':a;N;$!ba;s/\n\x0[0-9]* //g;s/\x0[0-9]* //g;s/\n\x0//g'".format(file)
    )

    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    p.communicate()[0]

    return p.returncode
