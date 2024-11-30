# Variables
$dockerImageName = "fasmrobotics/api-arduino"  # Nom de l'image Docker
$containerName = "mon-container"  # Nom du conteneur
$cloneDir = "C:\Users\moh\Desktop\TEMP"  # Répertoire temporaire pour cloner le dépôt

# Installation des outils nécessaires
winget install usbipd
winget install -e --id Docker.DockerDesktop

if (Test-Path $cloneDir) {
    Write-Host "Suppression de l'ancien répertoire temporaire..."
    Remove-Item -Recurse -Force $cloneDir
}

Write-Host "Recuperation de l'image Docker $dockerImageName..."
docker pull fasmrobotics/api-arduino

Write-Host "Obtention de la liste des ports USB disponibles..."
$output = usbipd list

Write-Output "Liste des ports USB disponibles :"
Write-Output $output

$keyword = Read-Host "Entrez un mot-clé ou identifiant du périphérique que vous recherchez"

$selectedPort = $output | Where-Object { $_ -match $keyword }

if ($selectedPort) {
    Write-Output "Port USB sélectionné : $selectedPort"
    $portID = ($selectedPort -split '\s+')[0]

    $command = "usbipd attach --wsl --busid=$portID; Read-Host -Prompt 'Appuyez sur Entrée pour continuer...'"

    Write-Host "Exécution de la commande en tant qu'administrateur : $command"
    Start-Process powershell -ArgumentList "-NoProfile -Command $command" -Verb RunAs
} else {
    Write-Output "Aucun port USB ne correspond au mot-clé spécifié."
}

Write-Host "Lancement du conteneur $containerName..."
docker run --rm -d --device=/dev/ttyUSB0:/dev/ttyUSB0 --name $containerName $dockerImageName

Write-Host "Conteneur lancé avec succès. Nom: $containerName"

Read-Host -Prompt "Appuyez sur Entrée pour continuer..."
