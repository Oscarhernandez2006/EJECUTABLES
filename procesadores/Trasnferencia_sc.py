

import numpy as np
import pandas as pd
import openpyxl
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
import requests
import os

class Doc:
    
    def __init__(self, ruta):   
        self.mov = pd.read_excel(ruta + 'TRANSFERENCIA DESPOSTE.xlsx', sheet_name='DESPOSTE',dtype={'LOTE':str,
        'BODEGA ORIGEN':str, 'BODEGA DESTINO':str}, skiprows=2)
        self.equivalencias = pd.read_excel(ruta + 'Equivalentes.xlsx', sheet_name='EQUIVALENTES',dtype={'REF_SIESA':str})
        self.parametros = pd.read_excel(ruta + 'Equivalentes.xlsx', sheet_name='PARAMETROS',dtype={'CODIGO_PARAMETRO':str},skiprows=1)
        
        self.d0                 = []
        self.cia                = self.parametros['CODIGO_PARAMETRO'].iloc[0]
        self.CIA                = self.parametros['CODIGO_PARAMETRO'].iloc[0]
        self.un                 = self.parametros['CODIGO_PARAMETRO'].iloc[4]
        self.CO                 = self.parametros['CODIGO_PARAMETRO'].iloc[1]
        self.TIPO_DOC           = self.parametros['CODIGO_PARAMETRO'].iloc[11]               
        self.fecha              = self.parametros['CODIGO_PARAMETRO'].iloc[6]
        self.tercero            =' '         #   cambiar por le nit de la empresa
        self.clase_doc          = 67           #   61 para entrada y 62 para salida
        self.concepto           = 607              #   601 para entrada Y 602 para salida
        self.motivo             = '01'                #   cambiar para la salida

        self.URL = "https://wscarnesantacruz.siesacloud.com:8043/wsUNOEE/wsUNOEE.asmx"
        self.CONEXION = 'UnoEE_Carnesantacruz_Real'
        self.CIA_CONEXION = str((self.CIA))
        self.USER = 'webservices'
        self.PASSWORD = 'Santacruz2026*'
     
    def dataframe(self):
        self.doc = self.mov.copy()
        self.doc.drop_duplicates(subset=['BODEGA ORIGEN', 'BODEGA DESTINO' ], keep="first", inplace=True)
        map_referencia = dict(zip(self.equivalencias['PRODUCTO'], self.equivalencias['REF_SIESA']))
        self.mov['REFERENCIA'] = self.mov['TIPO'].map(map_referencia)

    def consecutivo_reg(self):
        count = 0
        for i, row in self.mov.iterrows():
            count = count + 1
            self.mov.at[i,'numero_registro'] = count
                     
    def Verificacion(self, path):
        self.mov.to_excel(path + 'v_items_saldos.xlsx')

    def generar_cons(self, i, t):
        tamaño = ""
        
        for j in range(t):
            tamaño = tamaño + "0"     
        n_car = len(str(i))
        consecutivo = str(tamaño[0:(len(tamaño)-n_car)]+str(i))
        return consecutivo       

    def generar_trama(self):
        reg_ini = 1
        self.trama = self.generar_cons(reg_ini, 7) + "00000001" + str("{:<3}".format(self.CIA))
        self.d0.append(self.trama)
        c = 2
        t = 7
        ci = 1
        ti = 10
        row = ""
        for indice, fila in self.doc.iterrows():
         
      
            row = (

                    self.generar_cons(c, t)                                                +  #Numero de registro  7  7
                    "{:0>4.0f}".format(450)                                                +  #Tipo de registro  4  11
                    "{:0>2.0f}".format(0)                                                  +  #Subtipo de registro  2  13
                    "{:0>2.0f}".format(2)                                                  +  #Version del tipo de registro  2  15
                    "{:<3}".format(self.CIA)                                               +  #Compañía  3  18
                    "{:0>1.0f}".format(1)                                                  +  #Indica si el número consecutivo de docto es manual o automático  1  19
                    "{:3}".format(self.CO)                                                 +  #Centro de operación  3  22
                    "{:3}".format(self.TIPO_DOC)                                           +  #Tipo de documento   3  25
                    "{:0>8.0f}".format(1)                                                  +  #Consecutivo de documento   8  33
                    "{:8}".format(self.fecha)                                              +  #Fecha del documento  8  41
                    "{:15}".format(self.tercero)                                           +  #Tercero  15  56
                    "{:0>3.0f}".format(self.clase_doc)                                     +  #Clase de documento  3  59
                    "{:0>1.0f}".format(0)                                                  +  #Estado del documento  1  60
                    "{:0>1.0f}".format(0)                                                  +  #Estado de impresión  1  61
                    "{:255}".format(' ')                                                   +  #Notas  255  316
                    "{:0>3.0f}".format(self.concepto)                                      +  #Concepto  3  319
                    "{:5}".format(fila['BODEGA ORIGEN'])                                   +  #Bodega salida  5  324
                    "{:5}".format(fila['BODEGA DESTINO'])                                  +  #Bodega entrada  5  329
                    "{:15}".format(' ')                                                    +  #Documento alterno  15  344
                    "{:3}".format(' ')                                                     +  #Centro de operación  3  347
                    "{:3}".format(' ')                                                     +  #Tipo de documento   3  350
                    "{:0>8.0f}".format(0  )                                                +  #Consecutivo de documento   8  358
                    "{:10}".format(' ')                                                    +  #Código de vehiculo  10  368
                    "{:15}".format(' ')                                                    +  #Código transportador  15  383
                    "{:3}".format(' ')                                                     +  #Código sucursal transportador  3  386
                    "{:15}".format(' ')                                                    +  #Código conductor  15  401
                    "{:50}".format(' ')                                                    +  #Nombre conductor  50  451
                    "{:15}".format(' ')                                                    +  #Identificación del conductor  15  466
                    "{:0>30.0f}".format(0)                                                 +  #Numero de guia  30  496
                    "{:0>15.0f}".format(0)                                                 +  #Cajas/Bultos  15  511
                    "{:0>20.0f}".format(0)                                                 +  #Peso  20  531
                    "{:0>20.0f}".format(0)                                                 +  #Volumen  20  551
                    "{:0>20.0f}".format(0)                                                 +  #Valor asegurado  20  571
                    "{:255}".format(' ')                                                     #Notas  255  826
                    #"{:15}".format(' ')                                                      #Proyecto   15  841                  
            )
                
            self.d0.append(row)
            c = c+1

        for indice, fila in self.mov.iterrows():
            row = (
                    self.generar_cons(c, t)                                                +  #Numero de registro  7  7
                    "{:0>4.0f}".format(470)                                                +  #Tipo de registro  4  11
                    "{:0>2.0f}".format(0)                                                  +  #Subtipo de registro  2  13
                    "{:0>2.0f}".format(12)                                                 +  #Version del tipo de registro  2  15
                    "{:<3}".format(self.cia)                                               +  #Compañía  3  18
                    "{:3}".format(self.CO)                                                 +  #Centro de operación  3  21
                    "{:3}".format(self.TIPO_DOC)                                           +  #Tipo de documento   3  24
                    "{:0>8.0f}".format(1)                                                  +  #Consecutivo de documento   8  32
                    "{:0>10.0f}".format(fila['numero_registro'])                           +  #Numero de registro  10  42
                    "{:55}".format(' ')                                                    +  #Espacios  55  97
                    "{:5}".format(fila['BODEGA ORIGEN'])                                   +  #Bodega  5  102
                    "{:10}".format(' ')                                                    +  #Ubicación  10  112
                    "{:15}".format(fila['LOTE'])                                           +  #Lote  15  127
                    "{:0>3.0f}".format(self.concepto)                                      +  #Concepto  3  130
                    "{:2}".format(self.motivo)                                             +  #Motivo  2  132
                    "{:3}".format(self.CO)                                                 +  #Centro de operación movimiento  3  135
                    "{:2}".format(' ')                                                     +  #Espacios  2  137
                    "{:15}".format(' ')                                                    +  #Centro de costo movimiento  15  152
                    "{:15}".format(' ')                                                    +  #Proyecto  15  167
                    "{:4}".format('kg')                                                    +  #Unidad de medida  4  171
                    "{:0>20.4f}".format(fila['FRÍO(kg)'])                                  +  #Cantidad base  20  191
                    "{:0>20.4f}".format(0)                                                 +  #Cantidad adicional  20  211
                    "{:0>20.4f}".format(0)                                                 +  #Costo promedio unitario  20  231
                    "{:255}".format('ENTRADA PRODUCTOS TERMINADOS')                        +  #Notas  255  486
                    "{:2000}".format(' ')                                                  +  #Descripcion  2000  2486
                    "{:40}".format(' ')                                                    +  #Descripción del item  40  2526
                    "{:4}".format(' ')                                                     +  #Unidad de medida de inventario del item.  4  2530
                    "{:10}".format(' ')                                                    +  #Ubicación Entrada  10  2540
                    "{:15}".format(' ')                                                    +  #Lote Entrada  15  2555
                    "{:0>7}".format('0')                                                   +  #Item  7  2562
                    "{:<50}".format(fila['REFERENCIA'])                                    +  #Referencia item  50  2612
                    "{:20}".format(' ')                                                    +  #Codigo de barras  20  2632
                    "{:<20}".format(' ')                                                    +  #Extension 1  20  2652
                    "{:<20}".format(' ')                                                    +  #Extension 2  20  2672
                    "{:<20}".format(self.un)                                               +  #Unidad de negocio movimiento  20  2692
                    "{:0>10.0f}".format(0)                                                    #Rowid del movto.  10  2702
                
                 )
            self.d0.append(row)
            c = c+1
            ci = ci +1 
            
        self.trama_final = self.generar_cons(c, 7) + "99990001" + str("{:<3}".format(self.CIA))
        self.d0.append(self.trama_final)

    def guardar_archivo(self, ruta_archivo):
        precios = open(ruta_archivo, "w", encoding='utf-8')
        for fila in self.d0:
            linea = ''.join(str(fila))
            precios.write(linea + "\n")
        precios.close()

    def g_xml(self, path, ruta):
        importar = Element('Importar')
        nombre_conexion = SubElement(importar, 'NombreConexion')
        nombre_conexion.text = self.CONEXION
        
        id_cia = SubElement(importar, 'IdCia')
        id_cia.text = self.CIA_CONEXION
        
        usuario = SubElement(importar, 'Usuario')
        usuario.text = self.USER
        
        clave = SubElement(importar, 'Clave')
        clave.text = self.PASSWORD
        
        datos = SubElement(importar, 'Datos')
        with open(path , "r") as archivo:
            for linea in archivo:
                linea_elemento = SubElement(datos, 'Linea')
                linea_elemento.text = linea
        
        xml_content = tostring(importar, encoding='utf-8').decode('utf-8')
        
        # Combinar la ruta de destino con el nombre del archivo
        ruta_completa = os.path.join(ruta, "archivo.xml")
        
        # Escribir el XML en el archivo
        with open(path2 + 'doc.xml', "w") as xml_file:
            xml_file.write(xml_content)

    def consumir_servicio_web(self):
 
        # Leer el contenido del archivo XML
        with open(path + 'doc.xml', 'r') as f:
            xml_content = f.read()

        # Construir el cuerpo de la solicitud SOAP
        soap_body = '''
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
           <soapenv:Header/>
           <soapenv:Body>
              <tem:ImportarXML>
                 <tem:pvstrDatos><![CDATA[{xml_content}]]></tem:pvstrDatos>
                 <tem:printTipoError>0</tem:printTipoError>
              </tem:ImportarXML>
           </soapenv:Body>
        </soapenv:Envelope>
        '''.format(xml_content=xml_content)

        # Headers de la solicitud
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://tempuri.org/ImportarXML'
        }

        # Enviar la solicitud SOAP
        response = requests.post(self.URL, data=soap_body, headers=headers)

        # Verificar la respuesta
        if response.status_code == 200:
            print("Solicitud exitosa_dj:")
            print(response.text)
        else:
            print("Error al realizar la solicitud:", response.status_code)
            try:
                print("Contenido del error:", response.text)
            except Exception as e:
                print("Error al obtener el contenido del error:", e) 


path = '/Users/yorkysmurillo/Library/Mobile Documents/com~apple~CloudDocs/Ayudas/Santa_cruz/Proyectos/'
path2 = '/Users/yorkysmurillo/Library/Mobile Documents/com~apple~CloudDocs/Ayudas/Santa_cruz/Proyectos/'
doc = Doc(path)
doc.dataframe()
doc.consecutivo_reg()
doc.Verificacion(path)
doc.generar_trama()
doc.guardar_archivo(path + 'doc_entrada_sin_lotes.txt')
doc.g_xml(path + 'doc_entrada_sin_lotes.txt', path2)
doc.consumir_servicio_web()
