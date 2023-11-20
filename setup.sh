#Instrucciones para usar el script:

# Guarda este código en un archivo llamado setup.sh.
# Dale permisos de ejecución con el comando: chmod +x setup.sh.
# Ejecuta el script con: sudo ./setup.sh.

#!/bin/bash

# Actualizar los paquetes del sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar dependencias
sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev libcairo2-dev libgirepository1.0-dev python3-cryptography cython3 python3-numpy python3-pil python3-gi python3-gi-cairo gir1.2-gtk-3.0 libglib2.0-dev gcc pkg-config arandr python3-pygame portaudio19-dev python3-pil.imagetk libttspico-utils apache2 php avahi-daemon

# Clonar el repositorio de GitHub
git clone https://github.com/gbibbo/ai4s-embedded.git

# Cambiar al directorio clonado
cd ai4s-embedded

# Actualizar pip y setuptools
pip3 install --upgrade pip setuptools wheel

# Instalar Flask y dependencias adicionales
pip3 install Flask Flask-CORS pycairo PyGObject

# Instalar requisitos desde el archivo
pip3 install -r requirements.txt
pip3 install --upgrade colorama

# Descargar el archivo .pth
wget https://zenodo.org/record/3576599/files/Cnn9_GMP_64x64_300000_iterations_mAP%3D0.37.pth?download=1

# Copiar y configurar archivo index.html
sudo cp /home/ai4s/ai4s-embedded/index.html /var/www/html/index.html
sudo chown www-data:www-data /var/www/html/index.html
sudo chmod 644 /var/www/html/index.html
sudo chmod 777 /var/www/html/

# Configuración de scripts de Python para autoinicio
mkdir -p ~/.config/autostart

echo -e "[Desktop Entry]\nType=Application\nName=Run Temperature\nExec=python3 /home/ai4s/ai4s-embedded/temperature.py" > ~/.config/autostart/run_temperature.desktop
chmod +x /home/ai4s/ai4s-embedded/temperature.py

echo -e "[Desktop Entry]\nType=Application\nName=Run sed_demo\nExec=/home/ai4s/ai4s-embedded/run_sed_demo.sh" > ~/.config/autostart/run_sed_demo.desktop
chmod +x /home/ai4s/ai4s-embedded/run_sed_demo.sh

echo -e "[Desktop Entry]\nType=Application\nName=Run Flask\nExec=python3 /home/ai4s/ai4s-embedded/flask_app.py" > ~/.config/autostart/run_flask.desktop
chmod +x /home/ai4s/ai4s-embedded/flask_app.py

# Mover el logo a la carpeta pública
sudo mv /home/ai4s/ai4s-embedded/assets/logo.png /var/www/html/logo.png

# Reiniciar el sistema
sudo reboot
