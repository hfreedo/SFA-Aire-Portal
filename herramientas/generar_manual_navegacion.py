"""Manual de navegación de GitHub. Requiere reportlab y Pillow; no consulta cuentas."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import shutil
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'docs/navegacion-repositorio'
SHOTS = FOLDER / 'capturas'
OUTPUT = ROOT / 'output/pdf/Manual_de_navegacion_SFA_Aire.pdf'
REPO = 'https://github.com/hfreedo/SFA-Aire-Portal'
DATE = '28 de octubre de 2026'
W, H = A4
M = 42
CW = W - 2*M
INK = colors.HexColor('#213C35')
GREEN = colors.HexColor('#246B57')
MUTED = colors.HexColor('#53655F')
PALE = colors.HexColor('#ECF4EF')
LINE = colors.HexColor('#D7E2DB')
BLUE = colors.HexColor('#1D5F94')
GOLD = colors.HexColor('#A26418')
FONT_DIR = Path('C:/Windows/Fonts')
for name, filename in [('Body','arial.ttf'), ('Bold','arialbd.ttf'), ('Italic','ariali.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR/filename)))

styles = {
    'body': ParagraphStyle('body', fontName='Body', fontSize=10.2, leading=14.5, textColor=INK, spaceAfter=7),
    'small': ParagraphStyle('small', fontName='Body', fontSize=8.3, leading=11.4, textColor=MUTED),
    'cell': ParagraphStyle('cell', fontName='Body', fontSize=9.2, leading=12.5, textColor=INK),
    'head': ParagraphStyle('head', fontName='Bold', fontSize=21, leading=25, textColor=INK),
    'sub': ParagraphStyle('sub', fontName='Bold', fontSize=12, leading=16, textColor=GREEN),
}
for s in styles.values():
    s.bulletFontName='Body'
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='Bold')


def link(label, url):
    return f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#1D5F94"><u>{escape(label)}</u></link>'


class Manual:
    def __init__(self):
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        self.c=canvas.Canvas(str(OUTPUT),pagesize=A4,pageCompression=1)
        self.c.setTitle('SFA Aire - Manual de navegación del repositorio')
        self.c.setAuthor('Proyecto escolar SFA Aire')
        self.c.setSubject('Guías, descargas, código Arduino y navegación en GitHub')
        self.page=0
        self.used=set()
        self.records=[]

    def new(self, title, subtitle, key):
        if self.page:
            self.end()
            self.c.showPage()
        self.page+=1
        self.c.bookmarkPage(key)
        self.c.addOutlineEntry(title,key,0,False)
        self.c.setFillColor(GREEN)
        self.c.rect(0,H-10,W,10,fill=1,stroke=0)
        self.c.setFont('Bold',8)
        self.c.drawString(M,H-32,'SFA AIRE  /  APRENDER A RECORRER EL REPOSITORIO')
        self.y=H-58
        self.p(title,'head',gap=8)
        self.p(subtitle,'small',gap=15)

    def p(self,text,style='body',x=None,width=None,y=None,gap=7):
        x=M if x is None else x
        width=CW if width is None else width
        y=self.y if y is None else y
        p=Paragraph(text, styles[style])
        _,height=p.wrap(width,H)
        assert y-height>47, f'Text outside page {self.page}: {text[:60]} at {y-height}'
        p.drawOn(self.c,x,y-height)
        result=y-height-gap
        if x==M and width==CW:self.y=result
        return result

    def sub(self,text):
        self.y-=4
        self.p(text,'sub',gap=6)

    def note(self,title,text):
        p=Paragraph(f'<b>{title}</b><br/>{text}',styles['body'])
        _,h=p.wrap(CW-24,H)
        total=h+20
        assert self.y-total>47,f'Note outside page {self.page}'
        self.c.setFillColor(PALE)
        self.c.roundRect(M,self.y-total,CW,total,7,fill=1,stroke=0)
        p.drawOn(self.c,M+12,self.y-10-h)
        self.y-=total+12

    def table(self, rows, widths=None):
        widths=widths or [CW*.32,CW*.68]
        data=[[Paragraph(str(cell),styles['cell']) for cell in row] for row in rows]
        t=Table(data,colWidths=widths,hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),PALE),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
            ('LINEBELOW',(0,0),(-1,-1),.45,LINE),
        ]))
        _,height=t.wrap(CW,H)
        assert self.y-height>47,f'Table outside page {self.page}: {height}'
        t.drawOn(self.c,M,self.y-height)
        self.y-=height+12

    def shot(self,name,caption,crop=None,width=None,maxh=300,x=None,y=None,marks=()):
        image=Image.open(SHOTS/name).convert('RGB')
        if crop:image=image.crop(crop)
        iw,ih=image.size
        width=CW if width is None else width
        scale=min(width/iw,maxh/ih)
        dw,dh=iw*scale,ih*scale
        x=M+(width-dw)/2 if x is None else x+(width-dw)/2
        y=self.y if y is None else y
        assert y-dh>70,f'Screenshot outside page {self.page}'
        raw=BytesIO();image.save(raw,format='PNG');raw.seek(0)
        self.c.drawImage(ImageReader(raw),x,y-dh,width=dw,height=dh)
        self.c.setStrokeColor(LINE);self.c.setLineWidth(.6)
        self.c.rect(x,y-dh,dw,dh,fill=0,stroke=1)
        for number,rect in marks:
            rx,ry,rw,rh=rect
            self.c.setStrokeColor(GOLD);self.c.setLineWidth(1.5)
            self.c.roundRect(x+rx*scale,y-(ry+rh)*scale,rw*scale,rh*scale,3,fill=0,stroke=1)
            bx=x+rx*scale+8;by=y-ry*scale+1
            self.c.setFillColor(GOLD);self.c.circle(bx,by,8,fill=1,stroke=0)
            self.c.setFillColor(colors.white);self.c.setFont('Bold',8)
            self.c.drawCentredString(bx,by-2.6,str(number))
        bottom=y-dh-7
        bottom=self.p(caption,'small',x=x,width=dw,y=bottom,gap=10)
        self.y=bottom
        self.used.add(name)
        self.records.append({'page':self.page,'file':name,'crop':crop,'caption':caption})

    def end(self):
        self.c.setStrokeColor(LINE);self.c.setLineWidth(.5)
        self.c.line(M,38,W-M,38)
        self.c.setFillColor(MUTED);self.c.setFont('Body',8)
        self.c.drawString(M,25,'Capturas reales de GitHub y del portal | 28/10/2026')
        self.c.drawRightString(W-M,25,f'{self.page:02d} / 14')

    def save(self):
        assert self.page==14
        self.end();self.c.save()
        canonical=FOLDER/OUTPUT.name
        shutil.copyfile(OUTPUT,canonical)
        record={'date':DATE,'repository':REPO,'pages':self.page,
            'pdf':canonical.name,'sha256':hashlib.sha256(canonical.read_bytes()).hexdigest(),
            'screenshots':self.records,
            'originals':[{ 'file':n,'sha256':hashlib.sha256((SHOTS/n).read_bytes()).hexdigest()} for n in sorted(self.used)]}
        (FOLDER/'FUENTES_Y_CAPTURAS.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Created {self.page} pages; {len(self.used)} original screenshots; {canonical.stat().st_size} bytes.')


def build():
    d=Manual()
    d.new('Tu mapa para recorrer SFA Aire','Manual de navegación de GitHub para estudiantes | '+DATE,'inicio')
    d.p('Aquí están los documentos, las descargas y el código del proyecto. Esta guía te ayuda a llegar a cada lugar sin tener que aprender primero todas las funciones de GitHub.')
    d.note('Empieza por este enlace',link('github.com/hfreedo/SFA-Aire-Portal',REPO)+'<br/>Puedes leer el repositorio público y descargar sus archivos sin crear una cuenta de GitHub.')
    d.sub('Elige lo que necesitas')
    d.table([
        ['<b>Quiero...</b>','<b>Ir a la página</b>'],
        ['Orientarme en la portada','2. Reconocer carpetas, About y Releases'],
        ['Encontrar las guías','3 y 4. README y carpeta docs'],
        ['Leer un archivo .md','5. Preview, índice y búsqueda'],
        ['Guardar el manual en PDF','6. Leer en línea o descargar'],
        ['Descargar el programa','7 a 9. Releases, Windows y Android'],
        ['Encontrar el sketch Arduino','10. Ruta y descarga del archivo .ino'],
        ['Entender carpetas y lenguajes','11 y 12. Código fuente y Languages'],
        ['Entrar al portal del proyecto','13. Enlace del sector About'],
        ['Resolver una duda rápida','14. Ayuda y enlaces de consulta'],
    ])
    d.p('Los enlaces azules de este PDF se pueden pulsar. También puedes usar los marcadores del visor para saltar de tema. Los recuadros y números sobre las capturas son indicaciones añadidas para este manual. La interfaz y los nombres de archivos se conservaron tal como aparecen en el sitio.','small')
    d.p('Las versiones y capturas corresponden a esta edición. En una entrega futura pueden cambiar los archivos disponibles, su posición y los porcentajes de lenguajes.','small')

    d.new('1. Reconoce la portada','Antes de abrir carpetas, ubica tres puntos de referencia.','portada')
    d.shot('18-portada-amplia.png','Portada real del repositorio. En una ventana ancha, About y Releases aparecen a la derecha.',crop=(16,102,1235,640),maxh=260,
        marks=[(1,(17,265,855,82)),(2,(925,73,280,160)),(3,(925,397,280,120))])
    d.p('<b>1. Carpetas y archivos.</b> La pestaña <b>Code</b> es la entrada habitual. Una carpeta se abre con un clic; un archivo muestra su contenido. El nombre <b>main</b> identifica la rama principal del código.')
    d.p('<b>2. About.</b> Resume el proyecto y contiene el enlace al portal de monitoreo. Ese enlace abre la aplicación web, no otra carpeta de GitHub.')
    d.p('<b>3. Releases.</b> Lleva a las entregas preparadas para descargar. Es el lugar que necesitas para obtener el programa de Windows o la APK de Android.')
    d.note('Si tu pantalla se ve diferente','En una ventana estrecha o desde el celular, About puede aparecer encima de los archivos. Algunas pestañas se agrupan en <b>More</b>. No necesitas ver opciones como Settings, editar o crear archivos para estudiar el proyecto.')
    d.p(link('Volver a la portada del repositorio',REPO))

    d.new('2. Empieza por el README','Es la presentación del proyecto y el punto de partida más sencillo.','readme')
    d.shot('19-readme-guias.png','El README aparece al bajar por la portada, debajo de la lista de archivos.',crop=(32,10,910,680),maxh=345,
        marks=[(1,(20,204,800,95)),(2,(20,373,800,133)),(3,(20,627,560,40))])
    d.p('<b>1. Guía del stack tecnológico:</b> explica qué tecnologías se usaron y cómo se relacionan. Empieza aquí si estás preparando una explicación técnica.')
    d.p('<b>2. Manual de usuario:</b> enseña a instalar, ingresar y usar SFA Aire. Puedes leerlo en GitHub o abrir su PDF.')
    d.p('<b>3. Enlaces de acceso rápido:</b> Windows portable, Android, portal y guía de uso. Evitan recorrer todas las carpetas.')
    d.p('Si llegaste a otra carpeta, vuelve pulsando <b>SFA-Aire-Portal</b> en la ruta superior. También puedes usar el botón Atrás del navegador.')

    d.new('3. Encuentra la guía adecuada','La carpeta docs reúne la documentación; no hace falta leerla toda de una vez.','documentos')
    d.shot('07-docs-guias.png','Detalle real de docs: los documentos se abren pulsando su nombre.',crop=(340,269,717,590),maxh=190)
    d.table([
        ['<b>Documento</b>','<b>Úsalo para...</b>'],
        [link('MANUAL_DE_USUARIO.md',REPO+'/blob/main/docs/MANUAL_DE_USUARIO.md'),'Aprender la instalación y el uso de las pantallas.'],
        [link('GUIA_STACK_TECNOLOGICO.md',REPO+'/blob/main/docs/GUIA_STACK_TECNOLOGICO.md'),'Estudiar Arduino, Python, React, Kotlin, Supabase y Firebase.'],
        [link('HARDWARE.md',REPO+'/blob/main/docs/HARDWARE.md'),'Consultar los sensores y sus conexiones.'],
        [link('CONEXION_ARDUINO.md',REPO+'/blob/main/docs/CONEXION_ARDUINO.md'),'Seguir la conexión del Arduino con la PC.'],
        [link('ARQUITECTURA.md',REPO+'/blob/main/docs/ARQUITECTURA.md'),'Comprender el recorrido general del sistema.'],
        [link('PROTOCOLO.md',REPO+'/blob/main/docs/PROTOCOLO.md'),'Ver los mensajes y contratos de comunicación.'],
    ],[CW*.43,CW*.57])
    d.p('Los nombres con versiones, como ANDROID_082..., explican una entrega particular. Antes de seguir instrucciones antiguas, revisa la fecha y el alcance del documento. Las auditorías son material de consulta más avanzado.','small')

    d.new('4. Lee los archivos .md con comodidad','MD significa Markdown: texto con títulos, listas, enlaces y ejemplos de código.','markdown')
    d.shot('09-markdown.png','En Preview se ve el documento con su formato, en lugar de las marcas del texto.',crop=(335,222,1232,540),maxh=190,
        marks=[(1,(7,7,75,38)),(2,(84,7,58,38)),(3,(694,7,98,38))])
    d.p('<b>Preview</b> es la vista recomendada para leer. <b>Code</b> muestra el texto fuente del Markdown. <b>Raw</b> abre el archivo sin formato; no es un botón para iniciar el sistema.')
    d.shot('10-indice-markdown.png','Outline abre un índice de títulos. Pulsa uno para saltar a esa sección.',crop=(920,222,1235,710),width=184,maxh=218,x=M)
    y=440
    d.p('<b>Para encontrar una explicación</b>','sub',x=M+203,width=CW-203,y=y)
    d.p('1. Abre <b>Outline</b>, el icono de lista del archivo.<br/><br/>2. Elige un título, como Arduino o Supabase.<br/><br/>3. También puedes usar <b>Ctrl + F</b> y escribir una palabra visible en la página.<br/><br/>4. Si una tabla o un diagrama queda pequeño, amplía el navegador o abre la imagen.',x=M+203,width=CW-203,y=y-28)
    d.y=170
    d.note('Conserva el lugar donde estabas','Para comparar dos guías, abre un enlace en otra pestaña: clic derecho y <b>Abrir enlace en una pestaña nueva</b>. Así puedes volver al documento anterior sin perderlo.')

    d.new('5. Guarda el manual en PDF','Puedes leerlo desde GitHub o tener una copia sin conexión.','pdf')
    d.shot('14-manual-usuario.png','La página del manual ofrece accesos al PDF, Word y paquete completo.',crop=(333,220,1232,635),maxh=255)
    d.p('<b>1.</b> Desde el README, pulsa <b>Descargar PDF</b>. Si ya abriste MANUAL_DE_USUARIO.md, usa su enlace <b>Descargar PDF</b> al comienzo del texto.')
    d.p('<b>2.</b> Se abrirá el archivo PDF en GitHub o en el visor del navegador. Para guardarlo, usa la flecha de descarga del archivo o del visor; puede aparecer como <b>Download raw file</b>.')
    d.p('<b>3.</b> Busca el archivo en la carpeta Descargas y comprueba que termine en <b>.pdf</b>. Ábrelo para verificar que la descarga se completó.')
    d.note('Cada descarga tiene una finalidad','<b>PDF:</b> leer o imprimir.<br/><b>Word editable:</b> trabajar con una copia del documento.<br/><b>Paquete con HTML sin conexión:</b> extraer y abrir su HTML con las imágenes incluidas. Ese ZIP contiene documentación, no el programa Windows.')
    d.p('Un archivo HTML abierto dentro del repositorio puede mostrar su código. Para usar la versión sin conexión, descarga el paquete completo y extráelo antes de abrir el HTML.')
    d.p(link('Abrir el manual de usuario en PDF',REPO+'/raw/refs/heads/main/docs/manual-usuario/Manual_de_usuario_SFA_Aire.pdf'))

    d.new('6. Qué es una release','Una entrega publicada reúne una versión del programa, sus notas y sus archivos.','releases')
    d.shot('03-windows-release.png','Cabecera de la entrega Windows 0.8.0. La etiqueta Latest significa que fue marcada como entrega principal.',crop=(16,192,535,495),maxh=195)
    d.p('Abre <b>Releases</b> desde la portada. En cada entrega verás un título, una versión, las novedades y el bloque <b>Assets</b>, donde están los archivos adjuntos. Si Assets está cerrado, pulsa para desplegarlo.')
    d.table([
        ['<b>Lo que ves</b>','<b>Cómo interpretarlo</b>'],
        ['Release','Entrega publicada para consultar o descargar.'],
        ['Tag','Etiqueta que señala una versión concreta del código, por ejemplo v0.8.0.'],
        ['Latest','Etiqueta de la entrega principal. No garantiza que todos los componentes tengan el mismo número.'],
        ['Assets','Archivos descargables de esa entrega.'],
        ['Source code','Copia del código de esa versión; no equivale al programa portable.'],
    ])
    d.note('En esta edición del manual','<b>Windows:</b> portable 0.8.0.<br/><b>Android:</b> actualización independiente 0.8.2.<br/>El portable 0.8.0 conserva su APK original 0.8.0. Para actualizar solo Android, busca su entrega específica.')
    d.p(link('Abrir la lista de releases',REPO+'/releases'))

    d.new('7. Descarga para Windows','Busca el ZIP portable, no cualquier archivo que termine en .zip.','windows')
    top=d.y
    d.shot('04-windows-assets.png','Assets de la entrega Windows. El recuadro señala el portable.',crop=(20,72,535,552),width=250,maxh=280,x=M,
        marks=[(1,(14,231,482,52))])
    d.p('<b>Ruta</b><br/>Portada → Releases → <b>SFA Aire 0.8.0</b> → Assets.',x=M+268,width=CW-268,y=top)
    d.p('Pulsa el archivo:<br/><b>SFA_Aire_Windows_0.8.0_portable_x64.zip</b><br/><br/>Su tamaño publicado es aproximadamente <b>37,6 MB</b>. El nombre y la versión son mejores referencias que la posición de la fila.',x=M+268,width=CW-268,y=top-88)
    d.y=top-272
    d.sub('Después de descargar')
    d.p('<b>1.</b> Busca el ZIP en Descargas.<br/><b>2.</b> Usa <b>Extraer todo</b> y conserva la carpeta completa.<br/><b>3.</b> Abre <b>Panel SFA Aire.exe</b> desde la carpeta extraída.<br/><b>4.</b> Sigue el manual de usuario para el acceso y la conexión del Arduino.')
    d.note('Para evitar una confusión frecuente','<b>Source code (zip)</b> contiene fuentes. <b>Paquete con HTML sin conexión</b> contiene documentación. El archivo que se usa para ejecutar SFA Aire en Windows lleva <b>Windows</b>, <b>portable</b> y <b>x64</b> en su nombre.')
    d.p('Las imágenes PNG, los videos DEMO y los informes JSON de la release sirven como referencias y evidencias; no son el programa. Los archivos SHA256 contienen huellas para comprobar integridad, no instaladores.','small')
    d.p(link('Ir a la entrega de Windows 0.8.0',REPO+'/releases/tag/v0.8.0'))

    d.new('8. Descarga para Android','La aplicación móvil se entrega como archivo APK.','android')
    top=d.y
    d.shot('08-android-assets.png','En la entrega Android 0.8.2, selecciona el archivo .apk.',crop=(20,214,535,550),width=250,maxh=220,x=M,
        marks=[(1,(14,59,482,65))])
    d.p('<b>Ruta</b><br/>Portada → enlace <b>Android 0.8.2</b> del README.<br/><br/>También puedes buscar <b>Android 0.8.2 · Avisos y bandeja personal</b> en Releases.',x=M+268,width=CW-268,y=top)
    d.p('El archivo es:<br/><b>SFA_Aire_0.8.2.apk</b><br/><br/>Tamaño aproximado: <b>3,34 MB</b>.',x=M+268,width=CW-268,y=top-129)
    d.y=top-219
    d.p('<b>APK</b> es el archivo que Android utiliza para instalar la aplicación. Un PNG o un SVG es una imagen; el QR de la release no es la aplicación.')
    d.p('La entrega indica <b>Android 8 o posterior con Google Play Services</b>. La instalación y los permisos del teléfono se explican en el manual de usuario; aquí solo ubicamos la descarga correcta.')
    d.note('No te guíes únicamente por Latest','Al capturar este manual, Latest lleva a Windows 0.8.0. Android 0.8.2 está publicado por separado y es la actualización móvil indicada. Los números de Windows y Android no tienen que coincidir.')
    d.p('Lee también las notas de la entrega: explican cambios y límites de las pruebas. Una captura DEMO no demuestra que se haya recibido un aviso real en un teléfono.','small')
    d.p(link('Ir a la entrega Android 0.8.2',REPO+'/releases/tag/android-v0.8.2'))

    d.new('9. Encuentra el programa Arduino','El archivo del sketch termina en .ino.','arduino')
    d.p('<b>Ruta:</b> Code → arduino → SFA_Aire_Aulas → <b>SFA_Aire_Aulas.ino</b>. GitHub puede mostrar las dos carpetas unidas como <b>arduino/SFA_Aire_Aulas</b>; es la misma ubicación.')
    d.shot('11-arduino-carpeta.png','Carpeta del sketch: pulsa SFA_Aire_Aulas.ino.',crop=(334,104,1232,350),maxh=140)
    d.shot('12-arduino-codigo.png','Arriba del código aparecen Raw, copiar y la flecha de descarga.',crop=(333,222,1232,520),maxh=175,
        marks=[(1,(699,8,99,37))])
    d.p('<b>Para estudiarlo:</b> lee los comentarios y busca <b>setup()</b>, <b>loop()</b> y <b>muestra()</b>. <b>Raw</b> abre el texto sin la interfaz de GitHub; la flecha <b>Download raw file</b> descarga el archivo.')
    d.p('<b>Para abrirlo en Arduino IDE:</b> conserva el nombre SFA_Aire_Aulas.ino dentro de una carpeta llamada SFA_Aire_Aulas. Leer o descargar el sketch no lo carga a la placa. Las conexiones y la librería DHT se consultan en HARDWARE.md y en la guía tecnológica.')
    d.p(link('Abrir el sketch Arduino',REPO+'/blob/main/arduino/SFA_Aire_Aulas/SFA_Aire_Aulas.ino'))

    d.new('10. Código fuente y programa son distintos','El código permite estudiar cómo está construido el proyecto.','codigo')
    top=d.y
    d.shot('15-code-zip.png','El botón verde Code ofrece Download ZIP para descargar las fuentes.',crop=(138,130,535,454),width=235,maxh=200,x=M,
        marks=[(1,(17,277,356,35))])
    d.p('Para obtener una copia del código actual, vuelve a la portada, pulsa el botón verde <b>Code</b> y elige <b>Download ZIP</b>.<br/><br/>La pestaña <b>Code</b> y el botón verde <b>Code</b> tienen nombres iguales, pero no son el mismo control.',x=M+254,width=CW-254,y=top)
    d.y=top-230
    d.table([
        ['<b>Descarga</b>','<b>Qué contiene</b>'],
        ['Code → Download ZIP','Fuentes de la rama seleccionada; en este recorrido, main.'],
        ['Release → Source code','Fuentes vinculadas al tag de esa entrega.'],
        ['ZIP Windows portable','Programa preparado para ejecutar en Windows.'],
        ['Archivo .apk','Aplicación preparada para instalar en Android.'],
    ])
    d.sub('Lee la extensión para reconocer el archivo')
    d.p('<b>.md:</b> documentación. <b>.ino:</b> sketch Arduino. <b>.py:</b> Python. <b>.kt:</b> Kotlin. <b>.ts / .tsx:</b> TypeScript y componentes web. <b>.sql:</b> base de datos. <b>.json:</b> datos o configuración. <b>.png:</b> imagen.')
    d.p('Para estudiar no necesitas clonar, hacer un fork ni abrir un codespace. Si vas a reutilizar material, consulta AUTORIA.md y la licencia de uso del repositorio. Que sea público no significa que carezca de condiciones.','small')

    d.new('11. Interpreta Languages y las carpetas','La barra de lenguajes describe archivos; no mide la importancia de cada tecnología.','lenguajes')
    top=d.y
    d.shot('13-lenguajes.png','Detalle real de Languages. Los porcentajes pueden cambiar con nuevas publicaciones.',crop=(940,326,1225,478),width=245,maxh=140,x=M)
    d.p('Baja por la portada hasta <b>Languages</b>. GitHub estima la proporción a partir del tamaño de los archivos que clasifica por lenguaje.<br/><br/>No representa horas de trabajo, dificultad, autoría ni porcentaje de funciones del sistema.',x=M+264,width=CW-264,y=top)
    d.y=top-157
    d.table([
        ['<b>Carpeta</b>','<b>Qué puedes encontrar</b>'],
        ['arduino','Firmware del montaje. Puede aparecer dentro de Other en la barra.'],
        ['servidor_pc','Python: recepción USB, validación y reglas del receptor.'],
        ['interfaz_web','TypeScript, React y CSS: portal web y su presentación.'],
        ['android_app','Kotlin: aplicación nativa para el teléfono.'],
        ['supabase','SQL/PLpgSQL para la base y TypeScript para Edge Functions.'],
        ['docs','Guías, manuales, capturas y referencias de versiones.'],
        ['tests / herramientas','Pruebas y utilidades de desarrollo o distribución.'],
    ],[CW*.30,CW*.70])
    d.note('React, Supabase y Firebase no son lenguajes','Son una librería y plataformas, respectivamente. Por eso sus nombres no tienen que aparecer en Languages. La guía del stack explica su papel aunque no aparezcan en esa barra.')

    d.new('12. Abre el portal desde About','GitHub conserva el proyecto; el portal es la aplicación que se usa.','portal')
    top=d.y
    d.shot('18-portada-amplia.png','Enlace del portal en About.',crop=(938,186,1225,347),width=250,maxh=145,x=M,
        marks=[(1,(11,117,267,29))])
    d.p('<b>1.</b> Vuelve a la portada.<br/><b>2.</b> Busca <b>About</b>.<br/><b>3.</b> Pulsa <b>sfa-aire-aulas.web.app/remoto</b>.<br/><br/>También está como <b>Abrir el portal</b> en el README.',x=M+268,width=CW-268,y=top)
    d.y=top-174
    d.shot('16-portal.png','Pantalla real de acceso al portal. No se ingresaron cuentas durante las capturas.',crop=(180,24,1107,651),maxh=250)
    d.p('La cuenta de GitHub y la cuenta institucional de SFA Aire son distintas. Para entrar a un aula necesitas el acceso que autorice su administrador.')
    d.p('Si solo quieres conocer las pantallas, usa <b>Explorar demostración sin cuenta</b>. Allí se muestran datos ficticios; no se realizan mediciones físicas ni se envían notificaciones.')
    d.p(link('Abrir el portal de SFA Aire','https://sfa-aire-aulas.web.app/remoto'))

    d.new('13. Si te pierdes, vuelve a estas rutas','Una lista breve para usar mientras recorres el sitio.','ayuda')
    d.table([
        ['<b>Situación</b>','<b>Qué hacer</b>'],
        ['No encuentro una guía','Vuelve al README o abre docs. Busca el nombre exacto.'],
        ['Veo símbolos como # o **','Activa Preview: estás viendo el código del Markdown.'],
        ['Assets no muestra archivos','Despliega Assets y espera a que termine de cargar. Si falla, vuelve a abrir la entrega.'],
        ['Descargué un ZIP y no hay programa','Comprueba si era Source code o el paquete de documentación. Busca el ZIP Windows portable.'],
        ['No encuentro la APK actual','Usa el enlace Android del README o su release específica; no solo Latest.'],
        ['GitHub pide iniciar sesión','Para leer este repositorio público no necesitas cuenta. Revisa que no hayas entrado a una acción como editar, comentar o crear.'],
        ['La pantalla no coincide con la captura','Amplía la ventana, desplázate o busca More. La posición puede cambiar entre escritorio y celular.'],
    ])
    d.sub('Prueba este recorrido por tu cuenta')
    d.p('1. Abre la guía tecnológica y busca la sección de Firebase.<br/>2. Encuentra el pin del DHT en HARDWARE.md.<br/>3. Ubica la APK 0.8.2 sin descargar una imagen por error.<br/>4. Abre el sketch Arduino y localiza el comando MONITOR.<br/>5. Explica la diferencia entre GitHub y el portal de monitoreo.')
    d.p('<b>Enlaces para guardar:</b> '+link('Repositorio',REPO)+' · '+link('Documentación',REPO+'/tree/main/docs')+' · '+link('Releases',REPO+'/releases')+' · '+link('Guía tecnológica',REPO+'/blob/main/docs/GUIA_STACK_TECNOLOGICO.md'))
    d.p('Fuentes: navegación y capturas reales del repositorio y del portal, realizadas el 28/10/2026. Conceptos contrastados con '+link('Releases','https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases')+', '+link('README e índices','https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes')+' y '+link('visualización de archivos','https://docs.github.com/en/repositories/working-with-files/using-files/viewing-and-understanding-files')+' en la documentación oficial de GitHub.','small')
    d.save()


if __name__=='__main__':
    build()
