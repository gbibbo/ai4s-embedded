#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Athor: Gabriel Bibbo

"""
-This code is a modification of the AI4S demo written by Andres Fernandez
https://github.com/yinkalario/General-Purpose-Sound-Recognition-Demo

-This version incorporates the on/off control through the button, the LED
illumination of the button, the voice feedback of the demo status, the storage
of the detected tags in a .json file, the sending of notifications by mail
in case of detecting any specific event.

-This module is the main entry point to the app. It contains the specific class
to run the app, and a way of feeding custom parameters through the CLI.

-Usage example (ensure that python can ``import sed_demo``):

python m sed_demo TOP_K=10 TABLE_FONTSIZE=25
"""


from threading import Thread
import os
from dataclasses import dataclass
from typing import Optional
#
import torch
from omegaconf import OmegaConf
#
from sed_demo import AI4S_BANNER_PATH, SURREY_LOGO_PATH, CVSSP_LOGO_PATH, \
    EPSRC_LOGO_PATH, AUDIOSET_LABELS_PATH
from sed_demo.utils import load_csv_labels
from sed_demo.models import Cnn9_GMP_64x64
from sed_demo.audio_loop import AsynchAudioInputStream
from sed_demo.inference import AudioModelInference, PredictionTracker
from sed_demo.gui import DemoFrontend

from datetime import datetime, timedelta
import time
import json
import re

from tts import say
from aiy.board import Board, Led
import pyttsx3

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ##############################################################################
# # SED DEMO APP CLASS
# ##############################################################################
class DemoApp(DemoFrontend):
    """
    This class extends the Tk ``DemoFrontend`` with the specific functionality
    to run the sound event detection demo, i.e.:

    1. Instantiate an ``AsynchAudioInputStream`` to write an audio ring buffer
      from the microphone.
    2. Instantiate a ``Cnn9_GMP_64x64`` to detect categories from audio
    3. Instantiate an ``AudioModelInference`` that uses the CNN to periodically
      detect categories from the ring buffer.
    4. Instantiate a ``PredictionTracker`` to filter out undesired categories
      from the CNN output and return the top K, sorted by confidence.
    """

    # Custom theme colors
    BG_COLOR = "#fff8fa"
    BUTTON_COLOR = "#ffcc99"
    BAR_COLOR = "#ffcc99"
    
    # Define the tags you want to search for on email notification
    tags = ['Explosion', 'Baby cry, infant cry', 'Smoke detector, smoke alarm']
    # Define the threshold value to send email notification
    pval_threshold = 0.5
    # Email addresses to send notifications
    email_sender = 'ai4sound.test@gmail.com'
    email_receiver = 'ai4sound.test@gmail.com'
    email_sender_pass = 'fazblwlyhermslps'
                            

    def __init__(
            self,
            top_banner_path, logo_paths, model_path,
            all_labels, tracked_labels=None,
            samplerate=32000, audio_chunk_length=1024, ringbuffer_length=40000,
            model_winsize=1024, stft_hopsize=512, stft_window="hann",
            n_mels=64, mel_fmin=50, mel_fmax=14000,
            top_k=5, title_fontsize=22, table_fontsize=18):
        """
        :param top_banner_path: Path to the image showed at the top
        :param logo_paths: list of paths with images showed at the bottom
        :param all_labels: list of categories in same quantity and
          order as used during model training. See files in the ``assets`` dir.
        :param tracked_labels: optionally, a subset of ``all_labels``
          specifying the labels to track (rest will be ignored).
        :param samplerate: Audio samplerate. Ideally it should match the one
          used during model training.
        :param audio_chunk_length: number of samples that the audio recording
          will write at once. Not relevant for the model, but larger chunks
          impose larger delays for the real-time system.
        :param ringbuffer_length: The recorder will continuously update a ring
          buffer. To perform inference, the model will read the whole ring
          buffer, therefore this length determines the duration of the model
          input. E.g. ``length=samplerate`` corresponds to 1 second. Too short
          lengths may miss some contents, too large lengths may take too long
          for real-time computations.
        :param model_winsize: We have waveforms, but the model expects
          a time-frequency representation (log mel spectrogram). This is the
          window size for the STFT and mel operations. Should match training
          settings.
        :param n_mels: Number of mel bins. Should match training settings.
        :param mel_fmin: Lowest mel bin. Should match training settings.
        :param mel_fmax: Highest mel bin. Should match training settings.
        :param top_k: For each prediction, the app will show only the ``top_k``
          categories with highest confidence, in descending order.
        """
        super().__init__(top_k, top_banner_path, logo_paths,
                         title_fontsize=title_fontsize,
                         table_fontsize=table_fontsize)
        # 1. Input stream from microphone
        self.audiostream = AsynchAudioInputStream(
            samplerate, audio_chunk_length, ringbuffer_length)
        # 2. DL pretrained model to predict tags from ring buffer
        num_audioset_classes = len(all_labels)
        self.model = Cnn9_GMP_64x64(num_audioset_classes)
        checkpoint = torch.load(model_path,
                                map_location=lambda storage, loc: storage)
        self.model.load_state_dict(checkpoint["model"])
        # 3. Inference: periodically read the input stream with the model
        self.inference = AudioModelInference(
            self.model, model_winsize, stft_hopsize, samplerate, stft_window,
            n_mels, mel_fmin, mel_fmax)
        # 4. Tracker: process predictions, return the top K among allowed ones
        self.tracker = PredictionTracker(all_labels, allow_list=tracked_labels)
        #
        self.top_k = top_k
        self.thread = None
        # 5. Handle when user closes window
        self.protocol("WM_DELETE_WINDOW", self.exit_demo)
        # 6. Handle button press
        self._board = Board()
        self._board.button.when_pressed = self.on_button_press
        # 7. Time of the last sent email notification
        self.last_email_sent = datetime.min

    
        
    def on_button_press(self):
        """
        This function is called when the button on the device is pressed.
        It first initializes a speech synthesis engine (pyttsx3). Then it checks 
        whether a recording process is currently running. 
        If a recording is running, it:
            - Announces "Recording" using the speech synthesis engine.
            - Turns on the LED on the device to indicate that recording is in progress.
        If a recording is not running, it:
            - Announces "Stop Recording" using the speech synthesis engine.
            - Turns off the LED on the device to indicate that recording has stopped.
        """
        # Initialize the speech synthesis engine
        engine = pyttsx3.init()
        # Dispatch start (This line could use more context for a more specific comment)
        self.dispatch_start()
        # Check if a recording is currently running
        if self.is_running():
            # If a recording is running, print "Recording" to the console
            print("Recording")
            # Use the speech synthesis engine to say "Recording"
            engine.say("Recording")
            # Make the speech synthesis engine say the prepared text
            engine.runAndWait()
            # Turn on the LED on the device
            self._board.led.state = Led.ON
        else:
            # If a recording is not running, print "Stop Recording" to the console
            print("Stop Recording")
            # Use the speech synthesis engine to say "Stop Recording"
            engine.say("Stop Recording")
            # Make the speech synthesis engine say the prepared text
            engine.runAndWait()
            # Turn off the LED on the device
            self._board.led.state = Led.OFF

            
    def process_and_save_data(self, value):
        """
        This function processes the input data and saves it to a JSON file.
        The input data is expected to be a string with the following format:
            - Timestamp in the format HH:MM:SS.sss
            - Multiple tuples in the format '(label, confidence)'

        The function saves the processed data to a file named 'sound_datalog.json' 
        in the '/var/www/html' directory. Each data entry in the file will have a 
        'timestamp' key and a 'sounds' key which is a list of dictionaries, each 
        dictionary containing a 'label' key and a 'confidence' key.
        Parameters:
        value (str): The input data to process.

        """
        time_pattern = r'\d{2}:\d{2}:\d{2}\.\d{3}'
        data_pattern = r'\(\'(.+?)\',\s(.+?)\)'
        timestamp = re.search(time_pattern, value).group()
        data_list = re.findall(data_pattern, value)
        data = {
            'timestamp': timestamp,
            'sounds': [{ 'label': label, 'confidence': float(confidence)} for label, confidence in data_list]
        }
        # Change the path here to save the file in /var/www/html
        file_path = '/var/www/html/sound_datalog.json'
        # Check if the file exists and load the existing content
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                content = file.read()
                if content:
                    json_data = json.loads(content)
                else:
                    json_data = []
        else:
            json_data = []
        # Add the new data object to the array
        json_data.append(data)
        # Overwrite the file with the new content
        with open(file_path, 'w') as file:
            file.write(json.dumps(json_data, ensure_ascii=False))

    def send_email(self, subject, message, from_addr, to_addr, from_password):
        # Create the message object
        msg = MIMEMultipart()
        # Configure message attributes
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Subject'] = subject
        # Add message body
        msg.attach(MIMEText(message, 'plain'))
        # Create SMTP server connection
        server = smtplib.SMTP('smtp.gmail.com', 587)
        # Securely initiate the connection to the server
        server.starttls()
        # Login to the server
        server.login(from_addr, from_password)
        # Send the mail
        text = msg.as_string()
        server.sendmail(from_addr, to_addr, text)
        # Closing the server connection
        server.quit()


    def inference_loop(self):
        # Delete the sound_datalog.json file at the beginning of each iteration
        file_path = '/var/www/html/sound_datalog.json'
        while self.is_running():
            dl_inference = self.inference(self.audiostream.read())
            top_preds = self.tracker(dl_inference, self.top_k)
            for label, bar, (clsname, pval) in zip(
                    self.sound_labels, self.confidence_bars, top_preds):
                label["text"] = clsname
                bar["value"] = pval
                
                # Checks if any tag, with confidence > pval_threshold has been detected.
                if (clsname in self.tags) and pval > self.pval_threshold:
                    print(clsname + ' Detected')
                    # Checks if more than 30 seconds have passed since the last email was sent
                    if datetime.now() - self.last_email_sent > timedelta(seconds=30):
                        # If so, send the mail and update the time of the last mailing.
                        self.send_email(
                            clsname + ' Detected', 
                            'A ' + clsname + ' has been detected with confidence ' + str(pval),
                            self.email_sender,
                            self.email_receiver,
                            self.email_sender_pass
                        )
                        self.last_email_sent = datetime.now()
                
            dataframe = datetime.now().strftime("%H:%M:%S.%f")[:-3] + str(top_preds)
            self.process_and_save_data(dataframe)

    def start(self):
        """
        Starts ring buffer recording and ``inference_loop``, each on its own
        thread.
        """
        self.audiostream.start()
        self.thread = Thread(target=self.inference_loop)
        self.thread.daemon = True
        self.thread.start()  # will end automatically if is_running=False
        self._board.led.state = Led.ON

    def stop(self):
        """
        Stops the ring buffer recording (the inference loop stops as well)
        when user presses stop button.
        """
        # Note that the superclass already handles the update of the
        # ``is_running()`` method, so the thread will stop based on that.
        # Here we only need to stop the audio stream.
        self.audiostream.stop()
        self._board.led.state = Led.OFF

    def exit_demo(self):
        """
        """
        # if DL inference is running, give order to pause
        if self.is_running():
            print("Waiting for threads to finish...")
            self.toggle_start()
        # thread may take some time to finish, wait to prevent crash
        self.after(0, self.terminate_after_thread)

    def terminate_after_thread(self, wait_loop_ms=50):
        """
        If thread is still alive, wait for ``wait_loop_ms`` and check again.
        Once thread finished, exit app.
        """
        if self.thread is not None and self.thread.is_alive():
            self.after(wait_loop_ms, self.terminate_after_thread)
        else:
            print("Exiting...")
            self.audiostream.terminate()
            self.destroy()


# ##############################################################################
# # OMEGACONF
# ##############################################################################
@dataclass
class ConfDef:
    """
    Check ``DemoApp`` docstring for details on the parameters. Defaults should
    work reasonably well out of the box.
    """
    ALL_LABELS_PATH: str = AUDIOSET_LABELS_PATH
    SUBSET_LABELS_PATH: Optional[str] = None
    MODEL_PATH: str = os.path.join(
        "models", "Cnn9_GMP_64x64_300000_iterations_mAP=0.37.pth")
    #
    SAMPLERATE: int = 32000
    AUDIO_CHUNK_LENGTH: int = 1024
    RINGBUFFER_LENGTH: int = int(32000 * 2)
    #
    MODEL_WINSIZE: int = 1024
    STFT_HOPSIZE: int = 512
    STFT_WINDOW: str = "hann"
    N_MELS: int = 64
    MEL_FMIN: int = 50
    MEL_FMAX: int = 14000
    # frontend
    TOP_K: int = 6
    TITLE_FONTSIZE: int = 28
    TABLE_FONTSIZE: int = 22
    
    


# ##############################################################################
# # MAIN ROUTINE
# ##############################################################################
if __name__ == '__main__':
    
    file_path = '/var/www/html/sound_datalog.json'
    CONF = OmegaConf.structured(ConfDef())
    cli_conf = OmegaConf.from_cli()
    CONF = OmegaConf.merge(CONF, cli_conf)
    print("\n\nCONFIGURATION:")
    print(OmegaConf.to_yaml(CONF), end="\n\n\n")

    _, _, all_labels = load_csv_labels(CONF.ALL_LABELS_PATH)
    if CONF.SUBSET_LABELS_PATH is None:
        subset_labels = None
    else:
        _, _, subset_labels = load_csv_labels(CONF.SUBSET_LABELS_PATH)
    logo_paths = [SURREY_LOGO_PATH, CVSSP_LOGO_PATH, EPSRC_LOGO_PATH]

    demo = DemoApp(
        AI4S_BANNER_PATH, logo_paths, CONF.MODEL_PATH,
        all_labels, subset_labels,
        CONF.SAMPLERATE, CONF.AUDIO_CHUNK_LENGTH, CONF.RINGBUFFER_LENGTH,
        CONF.MODEL_WINSIZE, CONF.STFT_HOPSIZE, CONF.STFT_WINDOW,
        CONF.N_MELS, CONF.MEL_FMIN, CONF.MEL_FMAX,
        CONF.TOP_K, CONF.TITLE_FONTSIZE, CONF.TABLE_FONTSIZE)
    
    if os.path.exists(file_path):
        os.remove(file_path)
    # Plays welcome audio through the loudspeaker
    text = "This is the A I for Sound demo. Press the button to start recording sounds."
    say(text, lang='en-US', volume=60, pitch=130, speed=100, device='default')

    demo.mainloop()
