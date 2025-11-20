"""Modelos de datos para facturas"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class FacturaDetalle:
    """Modelo para un item/producto en el detalle de la factura"""
    codigo: Optional[str] = None
    descripcion: Optional[str] = None
    cantidad: Optional[float] = None
    unidad_medida: Optional[str] = None
    precio_unitario: Optional[float] = None
    descuento: Optional[float] = None
    subtotal: Optional[float] = None
    impuesto: Optional[float] = None
    total_item: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convierte el detalle a diccionario"""
        return {
            'Código': self.codigo or '',
            'Descripción': self.descripcion or '',
            'Cantidad': self.cantidad or '',
            'Unidad Medida': self.unidad_medida or '',
            'Precio Unitario': self.precio_unitario or '',
            'Descuento': self.descuento or '',
            'Subtotal': self.subtotal or '',
            'Impuesto': self.impuesto or '',
            'Total Item': self.total_item or ''
        }


@dataclass
class FacturaCabecera:
    """Modelo para la cabecera de la factura"""
    numero_factura: Optional[str] = None
    tipo_documento: Optional[str] = None
    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    
    # Información del proveedor/emisor
    proveedor_nombre: Optional[str] = None
    proveedor_rut: Optional[str] = None
    proveedor_actividad: Optional[str] = None  # Giro/Actividad del proveedor
    proveedor_direccion: Optional[str] = None
    proveedor_telefono: Optional[str] = None
    proveedor_email: Optional[str] = None
    
    # Información del cliente/receptor
    cliente_nombre: Optional[str] = None
    cliente_rut: Optional[str] = None
    cliente_direccion: Optional[str] = None
    cliente_comuna: Optional[str] = None
    cliente_ciudad: Optional[str] = None
    cliente_giro: Optional[str] = None
    cliente_codigo: Optional[str] = None
    cliente_telefono: Optional[str] = None
    cliente_patente: Optional[str] = None
    
    # Información de origen/destino
    direccion_origen: Optional[str] = None
    ciudad_origen: Optional[str] = None
    comuna_origen: Optional[str] = None
    direccion_destino: Optional[str] = None
    ciudad_destino: Optional[str] = None
    comuna_destino: Optional[str] = None
    
    # Información adicional
    codigo_vendedor: Optional[str] = None
    tipo_despacho: Optional[str] = None
    forma_pago: Optional[str] = None
    condiciones_pago: Optional[str] = None
    observaciones: Optional[str] = None
    
    # Totales
    subtotal: Optional[float] = None
    descuento_total: Optional[float] = None
    impuesto_porcentaje: Optional[float] = None
    impuesto_monto: Optional[float] = None
    total: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convierte la cabecera a diccionario"""
        return {
            'Número Factura': self.numero_factura or '',
            'Tipo Documento': self.tipo_documento or '',
            'Fecha Emisión': self.fecha_emision or '',
            'Fecha Vencimiento': self.fecha_vencimiento or '',
            'Proveedor Nombre': self.proveedor_nombre or '',
            'Proveedor RUT': self.proveedor_rut or '',
            'Proveedor Actividad': self.proveedor_actividad or '',
            'Proveedor Dirección': self.proveedor_direccion or '',
            'Proveedor Teléfono': self.proveedor_telefono or '',
            'Proveedor Email': self.proveedor_email or '',
            'Cliente Nombre': self.cliente_nombre or '',
            'Cliente RUT': self.cliente_rut or '',
            'Cliente Dirección': self.cliente_direccion or '',
            'Cliente Comuna': self.cliente_comuna or '',
            'Cliente Ciudad': self.cliente_ciudad or '',
            'Cliente Giro': self.cliente_giro or '',
            'Cliente Código': self.cliente_codigo or '',
            'Cliente Teléfono': self.cliente_telefono or '',
            'Cliente Patente': self.cliente_patente or '',
            'Dirección Origen': self.direccion_origen or '',
            'Ciudad Origen': self.ciudad_origen or '',
            'Comuna Origen': self.comuna_origen or '',
            'Dirección Destino': self.direccion_destino or '',
            'Ciudad Destino': self.ciudad_destino or '',
            'Comuna Destino': self.comuna_destino or '',
            'Código Vendedor': self.codigo_vendedor or '',
            'Tipo Despacho': self.tipo_despacho or '',
            'Forma Pago': self.forma_pago or '',
            'Condiciones Pago': self.condiciones_pago or '',
            'Observaciones': self.observaciones or '',
            'Subtotal': self.subtotal or '',
            'Descuento Total': self.descuento_total or '',
            'Impuesto %': self.impuesto_porcentaje or '',
            'Impuesto Monto': self.impuesto_monto or '',
            'Total': self.total or ''
        }


@dataclass
class Factura:
    """Modelo completo de factura que agrupa cabecera y detalle"""
    cabecera: FacturaCabecera = field(default_factory=FacturaCabecera)
    detalle: List[FacturaDetalle] = field(default_factory=list)
    
    def agregar_item(self, item: FacturaDetalle):
        """Agrega un item al detalle"""
        self.detalle.append(item)
    
    def to_dict(self) -> dict:
        """Convierte la factura completa a diccionario"""
        return {
            'cabecera': self.cabecera.to_dict(),
            'detalle': [item.to_dict() for item in self.detalle]
        }

