import numpy as np
import pandas as pd
import datetime
import openpyxl
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
import requests
import os

class Ped:
    def __init__(self, path):   
        self.Ped = pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='SOBRECOSTOS', dtype={'N.I.T / C.C.':str, 'CODIGO':str,'BOD ENTRADA':str, 'BOD SALIDA':str, 'SUCURSAL':str}, skiprows=1)
        self.EQUIVALENCIA = pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='EQUIVALENTES', dtype={ 'CODIGO':str,'REF_SIESA':str }, skiprows=1)
        self.data2= pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='PARAMETROS', dtype={ 'CODIGO_PARAMETRO':str,'REF_SIESA':str, 'LISTA PRECIOS':StopAsyncIteration }, skiprows=1)
        self.d0 = []
        self.data2.to_excel(path + 'v_dat2.xlsx')
        self.Ped.to_excel(path + 'v_ped.xlsx')
        self.CIA                            = self.data2['CODIGO_PARAMETRO'].iloc[0] 
        self.CO                             = self.data2['CODIGO_PARAMETRO'].iloc[1]
        self.TERCERO                        = self.data2['CODIGO_PARAMETRO'].iloc[2]
        self.SOLICITANTE                    = self.data2['CODIGO_PARAMETRO'].iloc[3]
        self.UN                             = self.data2['CODIGO_PARAMETRO'].iloc[4]
        self.CCOSTOS                        = self.data2['CODIGO_PARAMETRO'].iloc[5]
        self.FECHA                          = self.data2['CODIGO_PARAMETRO'].iloc[6]
        self.VENDEDOR                       = self.data2['CODIGO_PARAMETRO'].iloc[7]
        self.LISTA_PRECIO                   = self.data2['CODIGO_PARAMETRO'].iloc[8]
        self.COMPRADOR                      = self.data2['CODIGO_PARAMETRO'].iloc[9]
       
        self.MOTIVO                         = '01'
        self.CONCEPTO                       = '402'
        self.TIP_DOC                        = 'AJS'
        self.TIPO_PROVEEDOR                 = '0001'
        self.CLASE_DOCUMENTO                = '410'
        self.MODO_LIQUIDACION_COSTO         = 1
        self.REFERENCIA_SOBRECOSTO          = '1520'
        self.UM                             = 'U'
     
       
        self.URL = "https://wscarnesantacruz.siesacloud.com:8043/wsUNOEE/wsUNOEE.asmx"
        self.CONEXION = 'UnoEE_Carnesantacruz_Real'
        self.CIA_CONEXION = str(int(self.CIA))
        self.USER = 'webservices'
        self.PASSWORD = 'Santacruz2026*'
        
    def crear_dataframes(self):
        self.CIA = int(self.CIA)
        self.Ped2 = self.Ped.copy()
       
      
    def validar_datos(self):
        self.Ped.to_excel(path + 'v_df.xlsx')
        self.Ped2.to_excel(path + 'v_df2.xlsx')
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
        for indice, fila in self.Ped.iterrows():
            row = (
                
                    self.generar_cons(c, t)                                     +  #Numero de registro  7  7
                    "{:0>4.0f}".format(451)                                     +  #Tipo de registro  4  11
                    "{:0>2.0f}".format(1)                                       +  #Subtipo de registro  2  13
                    "{:0>2.0f}".format(1)                                       +  #Version del tipo de registro  2  15
                    "{:0>3.0f}".format(self.CIA)                                +  #Compañía  3  18
                    "{:0>1.0f}".format(1)                                       +  #Indicador para liquidar impuestos  1  19
                    "{:0>1.0f}".format(1)                                       +  #Indica si el número consecutivo de docto es manual o automático  1  20
                    "{:3}".format(self.CO)                                      +  #Centro de operación  3  23
                    "{:3}".format(self.TIP_DOC)                                 +  #Tipo de documento   3  26
                    "{:0>8.0f}".format(fila['NUM_DOC'])                         +  #Consecutivo de documento   8  34
                    "{:8}".format(self.FECHA)                                   +  #Fecha del documento  8  42
                    "{:15}".format(fila['N.I.T / C.C.'])                        +  #Tercero  15  57
                    "{:3}".format(self.CLASE_DOCUMENTO)                         +  #Clase de documento  3  60
                    "{:0>1.0f}".format(0)                                       +  #Estado del documento  1  61
                    "{:0>1.0f}".format(0)                                       +  #Estado de impresión  1  62
                    "{:255}".format(' ')                                        +  #Notas  255  317
                    "{:3}".format(self.CONCEPTO)                                +  #Concepto  3  320
                    "{:3}".format(self.CLASE_DOCUMENTO)                         +  #Grupo de clase de documento  3  323
                    "{:3}".format(fila['SUCURSAL'])                             +  #Sucursal del proveedor  3  326
                    "{:15}".format(self.COMPRADOR)                              +  #Tercero comprador  15  341
                    "{:0>12.0f}".format(fila["NUM_DOC"])                        +  #Documento referencia  12  353
                    "{:3}".format('COP')                                        +  #Moneda del documento  3  356
                    "{:3}".format('COP')                                        +  #Moneda base de conversión  3  359
                    "{:0>13.4f}".format(1)                                      +  #Tasa de conversión  13  372
                    "{:3}".format('COP')                                        +  #Moneda local  3  375
                    "{:0>13.4f}".format(1)                                      +  #Tasa local   13  388
                    "{:3}".format(fila["TIPO_DOC_BASE"])                        +  #Tipo de documento   3  391
                    "{:0>8.0f}".format(fila["NUM_DOC_BASE"])                    +  #Consecutivo de documento   8  399
                    "{:2}".format(self.MOTIVO)                                  +  #Motivo  2  401
                    "{:0>1.0f}".format(self.MODO_LIQUIDACION_COSTO)             +  #Modo de sobrecosto  1  402
                    "{:10}".format(" ")                                         +  #Código de vehiculo  10  412
                    "{:15}".format(" ")                                         +  #Código transportador  15  427
                    "{:3}".format(" ")                                          +  #Código sucursal transportador  3  430
                    "{:15}".format(" ")                                         +  #Código conductor  15  445
                    "{:50}".format(" ")                                         +  #Nombre conductor  50  495
                    "{:15}".format(" ")                                         +  #Identificación del conductor  15  510
                    "{:30}".format(" ")                                         +  #Numero de guia  30  540
                    "{:0>15.4f}".format(0)                                      +  #Cajas/Bultos  15  555
                    "{:0>20.4f}".format(0)                                      +  #Peso  20  575
                    "{:0>20.4f}".format(0)                                      +  #Volumen  20  595
                    "{:0>20.4f}".format(0)                                      +  #Valor asegurado  20  615
                    "{:255}".format(' ')                                            #Notas  255  870                


                )
            self.d0.append(row)
            c = c+1
        for indice, fila in self.Ped2.iterrows():
            row = (
                    self.generar_cons(c, t)                                     +  #Numero de registro  7  7
                    "{:0>4.0f}".format(452)                                     +  #Tipo de registro  4  11
                    "{:0>2.0f}".format(0)                                       +  #Subtipo de registro  2  13
                    "{:0>2.0f}".format(2)                                       +  #Version del tipo de registro  2  15
                    "{:0>3.0f}".format(self.CIA)                                +  #Compañía  3  18
                    "{:3}".format(self.CO)                                      +  #Centro de operación  3  21
                    "{:3}".format(self.TIP_DOC)                                 +  #Tipo de documento   3  24
                    "{:0>8.0f}".format(fila['NUM_DOC'])                         +  #Consecutivo de documento   8  32
                    "{:0>10.0f}".format(fila["NUM_DOC"])                        +  #Numero de registro  10  42
                    "{:47}".format(" ")                                         +  #Campos vacios  47  89
                    "{:0>20.4f}".format(fila["VALOR"])                          +  #Valor bruto   20  109
                    "{:3}".format(" ")                                        +  #Lista de precio  3  112
                    "{:40}".format(fila["DESCRIPCION"])                                         +  #Descripción del item  40  152
                    "{:4}".format(self.UM)                                      +  #Unidad de medida de inventario del item.  4  156
                    "{:0>7.0f}".format(0)                                       +  #Item  7  163
                    "{:<50}".format(fila["REF_SOBRECOSTOS"])                     +  #Referencia item  50  213
                    "{:20}".format(" ")                                            #Codigo de barras  20  233
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
Pedidos = Ped(path)
Pedidos.crear_dataframes()
Pedidos.validar_datos()
Pedidos.generar_trama()
Pedidos.guardar_archivo(path + 'SOBRE_COSTOS.txt')
Pedidos.g_xml(path + 'SOBRE_COSTOS.txt', path2)
Pedidos.consumir_servicio_web()