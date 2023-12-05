#!/bin/bash

# Log the start time
echo "Script started at $(date)" >> /home/ai4s/ai4s-embedded/sed_demo.log

# Set the PYTHONPATH
# export PYTHONPATH="/home/pi/Downloads/General-Purpose-Sound-Recognition-Demo-master:$PYTHONPATH"
cd /home/ai4s/ai4s-embedded

# Run sed_demo and log the output and errors
python3 -m sed_demo MODEL_PATH='Cnn9_GMP_64x64_300000_iterations_mAP=0.37.pth?download=1' # >> /home/ai4s/ai4s-embedded/sed_demo.log 2>&1


# Luego, hay que hacer lo siguiente
# Hacer que el script sea ejecutable:
#
# chmod +x ~/run_sed_demo.sh
# 
# Crear un archivo .desktop que se encargue de ejecutar este script al iniciar el sistema:
# 
# nano ~/.config/autostart/run_sed_demo.desktop
#
# Agrega las siguientes líneas al archivo:
# 
#[Desktop Entry]
#Type=Application
#Name=Run sed_demo
#Exec=/home/pi/AI4S-demo/run_sed_demo.sh



