"""QR de descarga local: generación nativa, sin enviar la URL a otro servicio."""
import struct
import zlib
import qrcode


def png_qr(url,scale=7):
    qr=qrcode.QRCode(border=4,error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url);qr.make(fit=True)
    matrix=qr.get_matrix();size=len(matrix)*scale
    raw=b''.join((b'\0'+bytes(0 if c else 255 for c in row for _ in range(scale)))*scale for row in matrix)
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
