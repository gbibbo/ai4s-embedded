# flask_app.py

from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import socket
import json
import os

app = Flask(__name__)
CORS(app)

# Archivo para almacenar el estado
state_file = 'state.json'

def load_state():
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f).get('state', 'stop')
    else:
        return 'stop'

#def save_state(state):
#    with open(state_file, 'w') as f:
#        json.dump({'state': state}, f)

def send_command(command):
    print('sendCommand called with', command)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 12345))  # reemplaza 'localhost' y '12345' con tu dirección y puerto
    sock.sendall(command.encode('utf-8'))
    sock.close()
    # Actualizar el estado
    # save_state(command)

@app.route('/')
def home():
    return """
<button onclick="updateState()">Toggle</button>
<script>
        function sendCommand(command) {
            fetch('http://raspberrypi.local:5000/command', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command }),
            });
        }
        function getState() {
            return fetch('http://raspberrypi.local:5000/state')
            .then(response => response.json())
            .then(data => data.state);
        }
        function updateState() {
            getState().then(state => {
                if (state === 'stop') {
                    sendCommand('start');
                } else {
                    sendCommand('stop');
                }
            });
        }
</script>
    """

@app.route('/command', methods=['POST'])
def command():
    data = json.loads(request.data)
    send_command(data['command'])
    return "Command sent"

@app.route('/state')
def get_state():
    state = load_state()
    return jsonify({'state': state})

if __name__ == "__main__":
    print('flask_app!!!')
    app.run(host='0.0.0.0', port=5000)
