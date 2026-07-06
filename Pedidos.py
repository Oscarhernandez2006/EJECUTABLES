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
        self.Ped = pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='PEDIDO', dtype={'N.I.T / C.C.':str, 'CODIGO':str,'BOD ENTRADA':str,	'BOD SALIDA':str, 'SUCURSAL':str}, skiprows=2)
        self.EQUIVALENCIA = pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='EQUIVALENTES', dtype={ 'CODIGO':str,'REF_SIESA':str }, skiprows=1)
        self.data2= pd.read_excel(path + 'PEDIDOS-SOBRECOSTOS.xlsx', sheet_name='PARAMETROS', dtype={ 'CODIGO_PARAMETRO':str,'REF_SIESA':str, 'LISTA PRECIOS':StopAsyncIteration }, skiprows=1)
        self.d0 = []
        self.data2.to_excel(path + 'v_dat2.xlsx')
        self.Ped.to_excel(path + 'v_ped.xlsx')
        self.CIA =  self.data2['CODIGO_PARAMETRO'].iloc[0] 
        self.CO = self.data2['CODIGO_PARAMETRO'].iloc[1]
        self.TERCERO = self.data2['CODIGO_PARAMETRO'].iloc[2]
        self.SOLICITANTE = self.data2['CODIGO_PARAMETRO'].iloc[3]
        self.UN = self.data2['CODIGO_PARAMETRO'].iloc[4]
        self.CCOSTOS = self.data2['CODIGO_PARAMETRO'].iloc[5]
        self.FECHA = self.data2['CODIGO_PARAMETRO'].iloc[6]
        self.VENDEDOR = self.data2['CODIGO_PARAMETRO'].iloc[7]
        self.LISTA_PRECIO = self.data2['CODIGO_PARAMETRO'].iloc[8]
        
       
        self.MOTIVO = '01'
        self.TIPO_DOC = '1PV'
        self.TIPO_CLIENTE = '001'
        self.CLASE_DOCUMENTO = '502'
        self.PUNTO_ENVIO = '000'
        

        self.URL = "https://wscarnesantacruz.siesacloud.com:8043/wsUNOEE/wsUNOEE.asmx"
        self.CONEXION = 'UnoEE_Carnesantacruz_Real'
        self.CIA_CONEXION = str(int(self.CIA))
        self.USER = 'Alexander.anillo'
        self.PASSWORD = 'Director2026*'
        
    def crear_dataframes(self):
        self.CIA = int(self.CIA)
        #self.Ped['Número de documento'] = self.Ped['NUM_DOC']
        self.Ped['Número de documento'] = self.Ped.index + 1
        map_ref_siesa = dict(zip(self.EQUIVALENCIA['CODIGO'], self.EQUIVALENCIA['REF_SIESA']))
        self.Ped['REF_SIESA'] = self.Ped['CODIGO'].map(map_ref_siesa)
        self.Ped2 = self.Ped.copy()
        self.Ped.drop_duplicates(['N.I.T / C.C.'], keep="first", inplace=True)
      
      
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
                
                    self.generar_cons(c, 7)                                   +           #Numero de registro
                    "{:0>4.0f}".format(430)                                   +           #Tipo de registro
                    "{:0>2.0f}".format(0)                                     +           #Subtipo de registro
                    "{:0>2.0f}".format(2)                                     +           #Versión del tipo de registro
                    "{:0>3.0f}".format(self.CIA)                              +           #Compañía
                    "{:0>1.0f}".format(1)                                     +           #Indicador para liquidar impuestos
                    "{:0>1.0f}".format(1)                                     +           #Indica si el numero consecutivo de docto es manual o automático
                    "{:0>1.0f}".format(1)                                     +           #Indicador de contacto
                    "{:3}".format(self.CO)                                    +           #Centro de operación del documento
                    "{:3}".format(self.TIPO_DOC)                              +           #Tipo de documento
                    "{:0>8.0f}".format(fila['NUM_DOC'])                       +           #Numero de documento
                    "{:8}".format(self.FECHA)                                 +           #Fecha del documento
                    "{:0>3.0f}".format(502)                                   +           #Clase interna del documento
                    "{:0>1.0f}".format(0)                                     +           #Estado del documento
                    "{:0>1.0f}".format(0)                                     +           #Indicador backorder del documento
                    "{:15}".format(fila['N.I.T / C.C.'])[:15]                 +           #Tercero cliente a facturar
                    "{:3}".format(fila['SUCURSAL'])[:3]                       +           #Sucursal cliente a facturar
                    "{:15}".format(fila["N.I.T / C.C."])[:15]                 +           #Tercero cliente a despachar
                    "{:3}".format(fila['SUCURSAL'])[:3]                       +           #Sucursal cliente a despachar
                    "{:4}".format(self.TIPO_CLIENTE)                          +           #Tipo de cliente
                    "{:3}".format(self.CO)                                    +           #Centro de operación de la factura
                    "{:8}".format(self.FECHA)                                 +           #Fecha entrega del pedido
                    "{:0>3.0f}".format(3)                                     +           #Nro. dias de entrega del documento
                    "{:<15}".format(1)                                        +           #Orden de compra del Documento
                    "{:<10}".format(1)                                        +           #Referencia del documento
                    "{:10}".format(" ")                                       +           #Codigo de cargue del documento
                    "{:3}".format("COP")                                      +           #Codigo de moneda del documento
                    "{:3}".format("COP")                                      +           #Moneda base de conversión
                    "{:0>13.4f}".format(1)                                    +           #Tasa de conversión
                    "{:3}".format("COP")                                      +           #Moneda local
                    "{:0>13.4f}".format(1)                                    +           #Tasa local
                    "{:3}".format(fila['CON_PAGO'])                           +           #Condicion de pago
                    "{:0>1.0f}".format(0)                                     +           #Estado de impresión del documento
                    "{:2000}".format('VENTAS')                                +           #Observaciones del documento
                    "{:15}".format(" ")                                       +           #Cliente de contado
                    "{:3}".format(self.PUNTO_ENVIO)                           +           #Punto de envio
                    "{:15}".format(self.VENDEDOR)                             +           #Vendedor del pedido
                    "{:50}".format(".")                                       +           #Contacto
                    "{:40}".format("Sitio de entrega")                        +           #Direccion 1
                    "{:40}".format(" ")                                       +           #Direccion 2
                    "{:40}".format(" ")                                       +           #Direccion 3
                    "{:3}".format("169")                                      +           #Pais
                    "{:2}".format('08')                                       +           #Departamento/Estado
                    "{:3}".format("001")                                      +           #Ciudad
                    "{:40}".format(" ")                                       +           #Barrio
                    "{:20}".format("5460000")                                 +           #Telefono
                    "{:20}".format(" ")                                       +           #Fax
                    "{:10}".format(" ")                                       +           #Codigo postal
                    "{:50}".format("facturacionelectronica@o.co")              +           # email
                    "{:0>1.0f}".format(0)                                                 #Indicador de precio  

        
                )
            self.d0.append(row)
            c = c+1
        for indice, fila in self.Ped2.iterrows():
            row = (
                self.generar_cons(c, t)                                       +           #Numero de registro
                    "{:0>4.0f}".format(431)                                   +           #Tipo de registro
                    "{:0>2.0f}".format(0)                                     +           #Indicador para liquidar impuestos
                    "{:0>2.0f}".format(2)                                     +           #Version del tipo de registro
                    "{:0>3.0f}".format(self.CIA)                              +           #Compañía
                    "{:3}".format(self.CO)                                    +           #Centro de operación
                    "{:3}".format(self.TIPO_DOC)                              +           #Tipo de documento 
                    "{:0>8.0f}".format(fila['NUM_DOC'])                       +           #Consecutivo de documento 
                    self.generar_cons(ci , ti )                               +           #Numero de registro
                    "{:0>7.0f}".format(0)                                     +           #Item
                    "{:<50}".format(fila['REF_SIESA'])                        +           #Referencia item
                    "{:20}".format(' ')                                       +           #Codigo de barras
                    "{:20}".format(' ')                                       +           #Extension 1
                    "{:20}".format(' ')                                       +           #Extension 2
                    "{:5}".format(fila['BOD SALIDA'])                         +           #Bodega
                    "{:0>3.0f}".format(501)                                   +           #Concepto
                    "{:2}".format(self.MOTIVO)                                +           #Motivo
                    "{:0>1.0f}".format(0)                                     +           #Indicador de obsequio
                    "{:3}".format(self.CO)                                    +           #Centro de operación movimiento
                    "{:20}".format(self.UN)                                   +           #Unidad de negocio movimiento
                    "{:<15}".format(' ')                                      +           #Centro de costo movimiento
                    "{:15}".format(" ")                                       +           #Proyecto
                    "{:8}".format(self.FECHA)                                 +           #Fecha entrega del pedido
                    "{:0>3.0F}".format(0)                                     +           #Nro. dias de entrega del documento
                    "{:3}".format(self.LISTA_PRECIO)                          +           #Lista de precio
                    "{:<4}".format("KG")                                     +           #Unidad de medida
                    "{:0>20.4f}".format(fila['CANT.(kg)'])                    +           #Cantidad base
                    "{:0>20.4f}".format(0)                                    +           #Cantidad adicional 
                    "{:0>20.4f}".format(0)                                    +           #Precio unitario
                    "{:0>1.0f}".format(0)                                     +           #Impuestos asumidos
                    "{:255}".format(" ")                                      +           #Notas
                    "{:2000}".format(" ")                                     +           #Descripcion
                    "{:0>1.0f}".format(5)                                     +           #Indicador backorder del movimiento 
                    "{:0>1.0f}".format(1)                                                 #Indicador de precio


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
Pedidos.guardar_archivo(path + 'Ped_p.txt')
Pedidos.g_xml(path + 'Ped_p.txt', path2)
Pedidos.consumir_servicio_web()