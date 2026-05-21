"""
Lambda: CreateItem
Seguridad aplicada:
- Validación estricta del body (schema validation)
- Sanitización de inputs
- Manejo seguro de errores
- Solo tiene permisos de ESCRITURA en DynamoDB (mínimo privilegio)
- Condición en S3: solo puede escribir con encriptación AES256
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Configuración de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

# Constantes de validación
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500


def build_response(status_code: int, body: dict, cors_origin: str = "*") -> dict:
    """Construye respuesta HTTP con headers de seguridad y CORS."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            # CORS headers
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            # Security headers
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body),
    }


def sanitize_string(value: str) -> str:
    """Sanitiza strings removiendo caracteres potencialmente peligrosos."""
    # Remover caracteres de control y trim
    sanitized = re.sub(r"[\x00-\x1f\x7f]", "", value.strip())
    return sanitized


def validate_body(body: dict) -> tuple[bool, str]:
    """Valida el body del request contra el schema esperado."""
    # Campos requeridos
    if "name" not in body:
        return False, "El campo 'name' es requerido"

    # Validar tipos
    if not isinstance(body.get("name"), str):
        return False, "El campo 'name' debe ser un string"

    if "description" in body and not isinstance(body["description"], str):
        return False, "El campo 'description' debe ser un string"

    # Validar longitudes
    if len(body["name"]) > MAX_NAME_LENGTH:
        return False, f"El campo 'name' no puede exceder {MAX_NAME_LENGTH} caracteres"

    if len(body.get("description", "")) > MAX_DESCRIPTION_LENGTH:
        return False, f"El campo 'description' no puede exceder {MAX_DESCRIPTION_LENGTH} caracteres"

    # Validar que no haya campos inesperados (whitelist)
    allowed_fields = {"name", "description", "tags"}
    unexpected = set(body.keys()) - allowed_fields
    if unexpected:
        return False, f"Campos no permitidos: {', '.join(unexpected)}"

    return True, ""


def lambda_handler(event, context):
    """Handler principal - crea un nuevo item."""
    logger.info("CreateItem invocado", extra={"method": event.get("httpMethod")})

    # 1. Parsear y validar body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return build_response(400, {"error": "El body debe ser JSON válido"})

    is_valid, error_msg = validate_body(body)
    if not is_valid:
        return build_response(400, {"error": error_msg})

    # 2. Sanitizar inputs
    item_id = str(uuid.uuid4())
    name = sanitize_string(body["name"])
    description = sanitize_string(body.get("description", ""))
    now = datetime.now(timezone.utc).isoformat()

    # 3. Escribir en DynamoDB
    try:
        item = {
            "PK": f"ITEM#{item_id}",
            "SK": "METADATA",
            "name": name,
            "description": description,
            "createdAt": now,
            "updatedAt": now,
            "environment": os.environ.get("ENVIRONMENT", "unknown"),
        }

        # Agregar tags si vienen
        if "tags" in body and isinstance(body["tags"], list):
            item["tags"] = [sanitize_string(str(t))[:50] for t in body["tags"][:10]]

        table.put_item(
            Item=item,
            # Condition para evitar sobreescritura accidental
            ConditionExpression="attribute_not_exists(PK)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning("Intento de sobreescritura", extra={"item_id": item_id})
            return build_response(409, {"error": "El item ya existe"})
        logger.error("Error escribiendo en DynamoDB", extra={"error": str(e)})
        return build_response(500, {"error": "Error interno del servidor"})

    # 4. Respuesta exitosa
    logger.info("Item creado exitosamente", extra={"item_id": item_id})
    return build_response(201, {
        "message": "Item creado exitosamente",
        "item": {"id": item_id, "name": name, "createdAt": now},
    })
