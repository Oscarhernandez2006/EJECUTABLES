<#
  Despliegue por SSH de EJECUTABLES a un servidor Ubuntu con Docker Swarm + Traefik (Dokploy).

  Qué hace:
    1. Se conecta por SSH al servidor.
    2. Clona el repo si no existe, o lo actualiza (git reset --hard) si ya está.
    3. Ejecuta deploy.sh, que construye la imagen y despliega el stack de swarm.

  Requisitos en el servidor:
    - Docker en modo Swarm (Dokploy ya lo tiene) y la red overlay "dokploy-network".

  Uso (desde PowerShell, en la carpeta del proyecto EJECUTABLES):
    ./deploy.ps1 -Server "usuario@IP_O_HOST"

  Ejemplos:
    ./deploy.ps1 -Server "adminsvr@190.131.223.74"
    ./deploy.ps1 -Server "adminsvr@servidor" -Branch main
#>

param(
  # Usuario y host del servidor: "usuario@ip" o "usuario@dominio".
  [Parameter(Mandatory = $true)]
  [string]$Server,

  # Carpeta del repo en el servidor.
  [string]$RepoDir = "/opt/ejecutables",

  # URL del repositorio git.
  [string]$RepoUrl = "https://github.com/Oscarhernandez2006/suite-santacruz.git",

  # Rama a desplegar.
  [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

# Comandos que se ejecutarán en el servidor remoto (Ubuntu).
$remote = @"
set -e
if [ ! -d "$RepoDir/.git" ]; then
  echo '==> Clonando repositorio...'
  sudo mkdir -p "$RepoDir"
  sudo chown -R \$(id -u):\$(id -g) "$RepoDir"
  git clone "$RepoUrl" "$RepoDir"
fi
cd "$RepoDir"
echo '==> Actualizando codigo...'
git fetch origin "$Branch"
git checkout "$Branch"
git reset --hard origin/"$Branch"

echo '==> Construyendo imagen y desplegando...'
cd EJECUTABLES
docker stack deploy -c docker-compose.yml ejecutables --prune

echo '==> Ejecución completada!'
echo '==> La app estará disponible en: https://ejecutables.grupo-santacruz.com'
"@

Write-Host "Conectando a $Server..." -ForegroundColor Green
ssh $Server $remote

Write-Host "Despliegue completado exitosamente" -ForegroundColor Green
