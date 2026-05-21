"""
Lambda: GetItem
Seguridad aplicada:
- Validación de input (path parameters)
- Manejo seguro de errores (no exponer detalles internos)
- Logging estructurado
- Solo tiene permisos de LECTURA en DynamoDB (mínimo privilegio)
"""

import json
import logging
import os
import re

import boto3
from botocore.exceptions import ClientError

# Configuración de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS (reutilizados entre invocaciones)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def build_response(status_code: int, body: dict, cors_origin: str = "*") -> dict:
    """Construye respuesta HTTP con headers de seguridad y CORS."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            # CORS headers
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            # Security headers
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body),
    }


def validate_id(item_id: str) -> bool:
    """Valida que el ID sea alfanumérico (previene inyección)."""
    return bool(re.match(r"^[a-zA-Z0-9\-_]{1,128}$", item_id))


def lambda_handler(event, context):
    """Handler principal - obtiene un item por ID."""
    logger.info("GetItem invocado", extra={"path": event.get("path")})

    # 1. Extraer y validar input
    path_params = event.get("pathParameters") or {}
    item_id = path_params.get("id", "")

    if not item_id:
        return build_response(400, {"error": "El parámetro 'id' es requerido"})

    if not validate_id(item_id):
        logger.warning("ID inválido recibido", extra={"item_id": item_id[:20]})
        return build_response(400, {"error": "El formato del ID no es válido"})

    # 2. Consultar DynamoDB
    try:
        response = table.get_item(
            Key={"PK": f"ITEM#{item_id}", "SK": "METADATA"},
            # Solo traer atributos necesarios (no exponer todo)
            ProjectionExpression="PK, SK, #n, description, createdAt",
            ExpressionAttributeNames={"#n": "name"},
        )
    except ClientError as e:
        logger.error("Error consultando DynamoDB", extra={"error": str(e)})
        # No exponer detalles del error al cliente
        return build_response(500, {"error": "Error interno del servidor"})

    # 3. Verificar si existe
    item = response.get("Item")
    if not item:
        return build_response(404, {"error": "Item no encontrado"})

    # 4. Respuesta exitosa
    logger.info("Item encontrado", extra={"item_id": item_id})
    return build_response(200, {"item": item})
