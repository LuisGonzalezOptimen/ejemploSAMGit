# 🚀 SAM + GitHub Actions - Clase de Seguridad

Proyecto SAM desplegado automáticamente con GitHub Actions. Cada alumno trabaja en su propia rama y el workflow despliega un stack independiente por alumno.

---

## 📋 Arquitectura del Proyecto

```
├── .github/
│   └── workflows/
│       └── sam-deploy.yml      # Workflow de GitHub Actions
├── src/
│   ├── get_item/
│   │   └── app.py             # Lambda GET /items/{id}
│   └── create_item/
│       └── app.py             # Lambda POST /items
├── events/                     # Eventos de prueba local
├── template.yaml               # Template SAM (CloudFormation)
├── samconfig.toml              # Configuración por ambiente
└── README.md
```

**Recursos desplegados por stack:**
- API Gateway con CORS y Access Logging
- 2 Lambda Functions (GetItem, CreateItem)
- DynamoDB Table con encriptación
- S3 Bucket con bloqueo público y HTTPS obligatorio
- CloudWatch Log Groups

---

## 🛠️ Pasos para Configurar el Repositorio

### Paso 1: El instructor crea el repositorio

1. Ir a [github.com/new](https://github.com/new)
2. Crear un repositorio (público o privado)
3. Subir este proyecto:

```bash
cd ejemploSAMGit
git init
git add .
git commit -m "feat: proyecto SAM inicial para clase de seguridad"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

---

### Paso 2: Configurar OIDC entre GitHub y AWS

Esto permite que GitHub Actions asuma un rol en tu cuenta AWS **sin access keys**.

#### 2.1 Crear el Identity Provider en AWS

1. Ir a **IAM → Identity Providers → Add Provider**
2. Seleccionar **OpenID Connect**
3. Provider URL: `https://token.actions.githubusercontent.com`
4. Audience: `sts.amazonaws.com`
5. Click **Add Provider**

#### 2.2 Crear el IAM Role para GitHub Actions

1. Ir a **IAM → Roles → Create Role**
2. Trusted entity: **Web identity**
3. Identity provider: `token.actions.githubusercontent.com`
4. Audience: `sts.amazonaws.com`
5. En la condición, agregar:
   - Condition: `StringLike`
   - Key: `token.actions.githubusercontent.com:sub`
   - Value: `repo:TU_USUARIO/TU_REPO:*`

6. Adjuntar las siguientes políticas (o crear una custom):
   - `AWSCloudFormationFullAccess`
   - `AmazonS3FullAccess`
   - `AWSLambda_FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AmazonAPIGatewayAdministrator`
   - `IAMFullAccess`
   - `CloudWatchLogsFullAccess`

   > ⚠️ En producción usarías permisos más restrictivos. Para la clase esto es suficiente.

7. Nombrar el rol: `github-actions-sam-deploy`
8. Copiar el **ARN del rol** (ej: `arn:aws:iam::123456789012:role/github-actions-sam-deploy`)

#### 2.3 Trust Policy del rol (JSON)

Verificar que la Trust Policy del rol se vea así:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::TU_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:TU_USUARIO/TU_REPO:*"
        }
      }
    }
  ]
}
```

---

### Paso 3: Configurar el Secret en GitHub

1. Ir al repositorio en GitHub → **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `AWS_ROLE_ARN`
4. Value: el ARN del rol creado en el paso anterior
   - Ejemplo: `arn:aws:iam::123456789012:role/github-actions-sam-deploy`
5. Click **Add secret**

---

### Paso 4: Los alumnos hacen fork/clone y crean su rama

#### Opción A: Colaboradores directos (recomendado para clase)

1. El instructor agrega a los alumnos como colaboradores:
   - **Settings → Collaborators → Add people**

2. Cada alumno clona el repo:
```bash
git clone https://github.com/INSTRUCTOR/REPO.git
cd REPO
```

3. Cada alumno crea su rama:
```bash
# Sebas
git checkout -b sebasBranch
git push -u origin sebasBranch

# Daniela
git checkout -b danielaBranch
git push -u origin danielaBranch

# Julian
git checkout -b julianBranch
git push -u origin julianBranch

# Luis (alumno)
git checkout -b luisBranch
git push -u origin luisBranch
```

#### Opción B: Fork (si no quieres dar acceso directo)

1. Cada alumno hace fork del repo
2. Crea su rama en su fork
3. Hace PR al repo original en la rama correspondiente

---

### Paso 5: Flujo de trabajo del alumno

```bash
# 1. Asegurarse de estar en su rama
git checkout sebasBranch

# 2. Hacer cambios en el código (ej: modificar una Lambda)
# ... editar archivos ...

# 3. Commit y push
git add .
git commit -m "feat: mi cambio en la lambda"
git push

# 4. El workflow se ejecuta automáticamente y despliega su stack
```

---

## 🔄 Cómo funciona el Workflow

```
Push a rama "alumno1"
    ↓
GitHub Actions detecta el push
    ↓
Determina config-env = "alumno1" (del samconfig.toml)
    ↓
sam build --config-env alumno1
    ↓
sam deploy --config-env alumno1
    ↓
Stack desplegado: "seguridad-sam-dev-alumno1"
```

**Mapeo rama → stack:**

| Rama           | Config Env | Stack Name                    | Environment      |
|----------------|------------|-------------------------------|------------------|
| main           | default    | seguridad-sam-dev-luis         | dev-luis         |
| sebasBranch    | sebas      | seguridad-sam-dev-sebas       | dev-sebas        |
| danielaBranch  | daniela    | seguridad-sam-dev-daniela     | dev-daniela      |
| julianBranch   | julian     | seguridad-sam-dev-julian      | dev-julian       |
| luisBranch     | luis       | seguridad-sam-dev-luis-alumno  | dev-luis-alumno   |

---

## 🧪 Probar localmente (opcional)

```bash
# Build
sam build

# Invocar Lambda local
sam local invoke GetItemFunction --event events/event_get_item.json
sam local invoke CreateItemFunction --event events/event_create_item.json

# Levantar API local
sam local start-api
```

---

## 📝 Agregar un nuevo alumno

1. Agregar el valor en `AllowedValues` del parámetro `Environment` en `template.yaml`
2. Agregar una nueva sección en `samconfig.toml` con el config-env del alumno
3. Agregar la rama en el trigger del workflow (`.github/workflows/sam-deploy.yml`)
4. El alumno crea su rama y hace push

---

## 🗑️ Limpiar recursos

Para eliminar el stack de un alumno:

```bash
aws cloudformation delete-stack --stack-name seguridad-sam-dev-sebas --region us-east-1
```

---

## ⚠️ Troubleshooting

| Problema | Solución |
|----------|----------|
| `Error: No identity-based policy allows sts:AssumeRoleWithWebIdentity` | Verificar la Trust Policy del rol y que el nombre del repo sea correcto |
| `Stack already exists` | El workflow usa `--no-fail-on-empty-changeset`, debería actualizar sin error |
| `Parameter Environment is not valid` | Agregar el nuevo valor en `AllowedValues` del template |
| El workflow no se ejecuta | Verificar que la rama esté listada en el trigger `on.push.branches` |

---

## 📚 Referencias

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/)
- [GitHub Actions + AWS OIDC](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [aws-actions/configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)
