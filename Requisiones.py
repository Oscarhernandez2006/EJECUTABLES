import numpy as np
import pandas as pd
import datetime
import openpyxl
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
import requests
import os

class Req:
    def __init__(self, path):   
        self.Req = pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='TRASNFERENCIA', dtype={'N.I.T / C.C.':str, 'CODIGO':str,'BOD ENTRADA':str,	'BOD SALIDA':str})
        self.EQUIVALENCIA = pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='EQUIVALENTES', dtype={ 'CODIGO':str,'REF_SIESA':str }, skiprows=1)
        self.data2= pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='PARAMETROS', dtype={ 'CODIGO_PARAMETRO':str,'REF_SIESA':str }, skiprows=1)
        self.d0 = []
        self.data2.to_excel(path + 'v_dat2.xlsx')
        self.CIA =  self.data2['CODIGO_PARAMETRO'].iloc[0] 
        self.CO = self.data2['CODIGO_PARAMETRO'].iloc[1]
        self.TERCERO = self.data2['CODIGO_PARAMETRO'].iloc[2]
        self.SOLICITANTE = self.data2['CODIGO_PARAMETRO'].iloc[3]
        self.UN = self.data2['CODIGO_PARAMETRO'].iloc[4]
        self.CCOSTOS = self.data2['CODIGO_PARAMETRO'].iloc[5]
        self.FECHA = self.data2['CODIGO_PARAMETRO'].iloc[6]
       
        self.MOTIVO = '02'
        self.TIPO_DOC = 'RQI'
        self.CONCEPTO = '605'
        self.CLASE_DOCUMENTO = '76'
      

        self.URL = "https://wscarnesantacruz.siesacloud.com:8043/wsUNOEE/wsUNOEE.asmx"
        self.CONEXION = 'UnoEE_Carnesantacruz_Real'
        self.CIA_CONEXION = str(int(self.CIA))
        self.USER = 'alexander.anillo'
        self.PASSWORD = 'Director2026*'
        
    def crear_dataframes(self):
        self.CIA = int(self.CIA)
        self.Req['Número de documento'] = self.Req['NUM_DOC']
        map_ref_siesa = dict(zip(self.EQUIVALENCIA['CODIGO'], self.EQUIVALENCIA['REF_SIESA']))
        self.Req['REF_SIESA'] = self.Req['CODIGO'].map(map_ref_siesa)
        self.Req2 = self.Req.copy()
        self.Req.drop_duplicates('Número de documento', keep="first", inplace=True)
      
      
    def validar_datos(self):
        self.Req.to_excel(path + 'v_df.xlsx')
        self.Req2.to_excel(path + 'v_df2.xlsx')
        self.data2.to_excel(path + 'v_data2.xlsx')
        
        
    def generar_cons(self, i, t):
        tamaño = ""
        for j in range(t):
            tamaño = tamaño + "0"     
        n_car = len(str(i))
        consecutivo = str(tamaño[0:(len(tamaño)-n_car)]+str(i))
        return consecutivo
    
    def generar_consecutivo(self, i):
        tamaño = "0000000"
        n_car = len(str(i))
        consecutivo = str(tamaño[0:(len(tamaño)-n_car)]+str(i))
        return consecutivo
    
    def generar_trama(self):
        reg_ini = 1
        self.trama = self.generar_consecutivo(reg_ini) + "00000001" + str("{:0>3.0f}".format(self.CIA) )
        self.d0.append(self.trama)
        c = 2
        t = 7
        ci = 1
        ti = 10
        row = ""
        for indice, fila in self.Req.iterrows():
            row = (
                    self.generar_cons(c, t)                                 +  #Numero de registro  7  7
                    "{:0>4.0f}".format(440)                                 +  #Tipo de registro  4  11
                    "{:0>2.0f}".format(0)                                   +  #Subtipo de registro  2  13
                    "{:0>2.0f}".format(2)                                   +  #Version del tipo de registro  2  15
                    "{:0>3.0f}".format(self.CIA)                            +  #Compañía  3  18
                    "{:0>1.0f}".format(1)                                   +  #Indica si el número consecutivo de docto es manual o automático  1  19
                    "{:3}".format(self.CO)                                  +  #Centro de operación  3  22
                    "{:3}".format(self.TIPO_DOC)                            +  #Tipo de documento   3  25
                    "{:0>8.0f}".format(fila["Número de documento"])         +  #Consecutivo de documento   8  33
                    "{:8}".format(self.FECHA)                               +  #Fecha del documento  8  41
                    "{:15}".format(' ')                            +  #Tercero  15  56
                    "{:5}".format(self.SOLICITANTE)                         +  #Tercero solicitante  5  61
                    "{:8}".format(self.FECHA)                               +  #Fecha de entrega  8  69
                    "{:0>3.0f}".format(1)                                   +  #Número días de entraga  3  72
                    "{:3}".format(self.CLASE_DOCUMENTO)                     +  #Clase de documento  3  75
                    "{:0>1.0f}".format(0)                                   +  #Estado del documento  1  76
                    "{:0>1.0f}".format(0)                                   +  #Estado de impresión  1  77
                    "{:255}".format(' ')                                    +  #Notas  255  332
                    "{:3}".format(self.CONCEPTO)                            +  #Concepto  3  335
                    "{:5}".format(fila["BOD ENTRADA"])                      +  #Bodega salida  5  340
                    "{:5}".format(fila["BOD SALIDA"])                       +  #Bodega entrada  5  345
                    "{:20}".format(" ")                                     +  #Documento referencia  20  365
                    "{:10}".format(" ")                                        #Ubicación de entrada  10  375
        
                )
            self.d0.append(row)
            c = c+1
        for indice, fila in self.Req2.iterrows():
            row = (
                    self.generar_cons(c, t)                                 +  #Numero de registro  7  7
                    "{:0>4.0f}".format(441)                                 +  #Tipo de registro  4  11
                    "{:0>2.0f}".format(0)                                   +  #Subtipo de registro  2  13
                    "{:0>2.0f}".format(2)                                   +  #Version del tipo de registro  2  15
                    "{:0>3.0f}".format(self.CIA)                            +  #Compañía  3  18
                    "{:3}".format( self.CO)                                 +  #Centro de operación  3  21
                    "{:3}".format(self.TIPO_DOC)                            +  #Tipo de documento   3  24
                    "{:0>8.0f}".format(fila["Número de documento"])[:8]     +  #Consecutivo de documento   8  32
                    "{:0>10.0f}".format(fila["No."])[:10]                   +  #Numero de registro  10  42
                    "{:0>7.0f}".format(0)                                   +  #Item  7  49
                    "{:50}".format(fila["REF_SIESA"])                       +  #Referencia item  50  99
                    "{:20}".format(' ')                                     +  #Codigo de barras  20  119
                    "{:20}".format(' ')                                     +  #Extension 1  20  139
                    "{:20}".format(' ')                                     +  #Extension 2  20  159
                    "{:5}".format(fila["BOD ENTRADA"])                       +  #Bodega  5  164
                    "{:3}".format(self.CONCEPTO)                            +  #Concepto  3  167
                    "{:2}".format(self.MOTIVO)                              +  #Motivo  2  169
                    "{:<4}".format('KG')                                    +  #Unidad de medida  4  173
                    "{:0>20.4f}".format(fila['CANT.(kg)'])                  +  #Cantidad base  20  213                    
                    "{:0>20.4f}".format(0)                                  +  #Cantidad adicional  20  213
                    "{:8}".format(self.FECHA)                               +  #Fecha de entrega  8  221
                    "{:0>3.0f}".format(1)                                   +  #Número días de entraga  3  224
                    "{:3}".format(self.CO)                                  +  #Centro de operación movimiento  3  227
                    "{:0>2}".format(" ")                                    +  #Campos vacios   2  229
                    "{:15}".format(' ')                                     +  #Centro de costo movimiento  15  244
                    "{:15}".format(" ")                                     +  #Proyecto  15  259
                    "{:255}".format(" ")                                    +  #Notas  255  514
                    "{:2000}".format(" ")                                   +  #Descripcion  2000  2514
                    "{:20}".format(self.UN)                                    #Unidad de negocio movimiento  20  2534

                 )
            self.d0.append(row)
            c = c+1
            ci = ci +1 
        self.trama_final = self.generar_consecutivo(c) + "99990001" + str("{:0>3.0f}".format(self.CIA) )
        self.d0.append(self.trama_final)
    def guardar_archivo(self, ruta_archivo):
        precios = open(ruta_archivo, "w")
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
Requisiones = Req(path)
Requisiones.crear_dataframes()
Requisiones.validar_datos()
Requisiones.generar_trama()
Requisiones.guardar_archivo(path + 'Req.txt')
Requisiones.g_xml(path + 'Req.txt', path2)
Requisiones.consumir_servicio_web()