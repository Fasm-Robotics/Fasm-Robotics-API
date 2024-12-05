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
docker pull fasmrobotics/releases-api-arduino:latest

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

    # Attente de la fin de Start-Process
    $process = Start-Process powershell -ArgumentList "-NoProfile -Command $command" -Verb RunAs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Error "Erreur lors de l'exécution de la commande en mode administrateur."
        exit 1
    }
} else {
    Write-Output "Aucun port USB ne correspond au mot-clé spécifié."
    exit 1
}

Write-Host "Lancement du conteneur $containerName..."
# Récupération de l'ID du conteneur lancé
$containerID = docker run --rm -d -p 5000:5000 --device=/dev/ttyUSB0:/dev/ttyUSB0 --name $containerName $dockerImageName

if (!$containerID) {
    Write-Error "Erreur lors du lancement du conteneur Docker."
    exit 1
}

Write-Host "Conteneur lancé avec succès. Nom: $containerName, ID: $containerID"

try {
    Write-Host "Affichage des logs du conteneur (Appuyez sur Ctrl+C pour arrêter les logs)..."
    # Démarre `docker logs --follow` dans un nouveau processus
    Start-Process -NoNewWindow -Wait powershell -ArgumentList "docker logs --follow $containerID"
} catch {
    Write-Warning "Interruption des logs détectée. Fermeture des ressources..."
} finally {
    Write-Host "Arrêt du conteneur Docker et détachement du port USB..."
    docker stop $containerID
    usbipd detach --busid=$portID
    Write-Host "Ressources libérées avec succès."
}
