#!/bin/bash

# Script para crear usuarios IAM en AWS CloudShell
# Crea grupo, usuarios, contraseñas y asigna permisos de administrador

# Contraseña por defecto para todos los usuarios
PASSWORD_DEFAULT="Participante2025!"

echo "=== Creando grupo de participantes ==="

# Crear el grupo
aws iam create-group --group-name participantes
echo "✓ Grupo 'participantes' creado"

# Adjuntar política de AdministratorAccess al grupo
aws iam attach-group-policy \
    --group-name participantes \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
echo "✓ Política AdministratorAccess adjuntada al grupo"

echo ""
echo "=== Creando usuarios con contraseñas ==="
echo "Contraseña por defecto: $PASSWORD_DEFAULT"
echo ""

# Array de usuarios (username:nombre_completo)
usuarios=(
    "jose.huapaya:Jose Alberto Huapaya Vasquez"
    "liz.quiroz:Liz Fiorella Quiroz Sotelo"
    "lizell.condori:Lizell Nieves Condori Cabana"
    "nataly.vasquez:Nataly Grace Vasquez Saenz"
    "monica.rantes:Monica Tahiz Rantes Garcia"
    "manuel.ochoa:Manuel Alejandro Ochoa Bolaños"
    "jhennyfer.zarate:Jhennyfer Zarate Villar"
    "maricielo.nestares:Maricielo Abigail Nestares Flores"
    "jose.reveron:Jose Gregorio Reveron Garcia"
    "geraldine.curipaco:Geraldine Nisbeth Curipaco Huayllani"
    "jose.julca:Jose Luis Julca Huarca"
    "kattya.garcia:Kattya Isabel Garcia Velasquez"
    "omar.quesquen:Omar Ernesto Quesquen Terrones"
    "camila.falcon:Camila Jasmin Falcon Cordova"
    "alexis.almeyda:Alexis Almeyda Napa"
    "kaori.murakami:Kaori Murakami Nako"
    "henry.torero:Henry Jesus Torero Ramirez"
    "oscar.duenas:Oscar Eduardo Dueñas Damian"
    "nicolle.acosta:Nicolle Acosta Huarcaya"
    "richard.tijero:Richard Tijero Lozano"
    "genaro.martinez:Genaro Alfredo Martinez Medina"
    "jimena.ruiz:Jimena Alexandra Ruiz Cerna"
    "luis.flores:Luis Alberto Flores Chavez"
    "gustavo.ramos:Gustavo Andres Ramos Montalvo"
    "hector.huapaya:Hector Daniel Huapaya Vasquez"
    "frank.diaz:Frank Diaz Soto"
    "hector.quispe:Hector Alvaro Quispe Abanto"
    "victor.ramirez:Víctor Angel Ramírez Ramírez"
    "eduardo.barron:Eduardo Ciro Barron Lopez"
    "marianella.caycho:Marianella Del Carmen Caycho Herrera"
    "jeronimo.enciso:Jeronimo Yoel Enciso Saravia"
    "jhoel.lucero:Jhoel Hugo Lucero Herrera"
    "billy.polo:Billy Polo Torres"
    "genesis.fernandez:Genesis Maria Fernandez Sifuentes"
    "delsy.banda:Delsy Banda Vargas"
    "artemio.perlacios:Artemio Harold Perlacios Luque"
    "braulio.molleapaza:Braulio Molleapaza Quea"
    "jose.alegre:Jose Alegre Argomedo"
    "rodrigo.loayza:Rodrigo Ireneo Loayza Abal"
)

# Crear cada usuario, agregar al grupo y crear contraseña
contador=0
for usuario_info in "${usuarios[@]}"; do
    username=$(echo $usuario_info | cut -d':' -f1)
    nombre_completo=$(echo $usuario_info | cut -d':' -f2)
    
    # Crear usuario
    aws iam create-user --user-name "$username" --tags Key=Name,Value="$nombre_completo" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✓ Usuario creado: $username ($nombre_completo)"
        
        # Agregar usuario al grupo
        aws iam add-user-to-group --user-name "$username" --group-name participantes
        
        # Crear perfil de login con contraseña (sin requerir cambio)
        aws iam create-login-profile \
            --user-name "$username" \
            --password "$PASSWORD_DEFAULT" \
            --no-password-reset-required 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "  ✓ Contraseña configurada"
        else
            echo "  ✗ Error al configurar contraseña (posiblemente ya existe)"
        fi
        
        contador=$((contador + 1))
    else
        echo "✗ Error al crear: $username (posiblemente ya existe)"
    fi
    echo ""
done

echo ""
echo "=== Resumen ==="
echo "Total de usuarios creados: $contador"
echo "Grupo: participantes"
echo "Permisos: AdministratorAccess"
echo "Contraseña por defecto: $PASSWORD_DEFAULT"
echo ""
echo "=== Información de acceso ==="
echo "Los usuarios pueden iniciar sesión en:"
echo "https://$(aws sts get-caller-identity --query Account --output text).signin.aws.amazon.com/console"
echo ""
echo "Usuario: [nombre_usuario]"
echo "Contraseña: $PASSWORD_DEFAULT"
echo ""
echo "Nota: La contraseña NO requiere cambio obligatorio"
