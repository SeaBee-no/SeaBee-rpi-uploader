# SeaBee Raspberry Pi Uploader - README

## Overview
The SeaBee Raspberry Pi Uploader is a Python-based graphical application designed to facilitate the transfer of data from SD cards to USB drives and eventually to a MinIO server. It's tailored for use in Raspberry Pi systems, with a user-friendly interface that allows easy monitoring and control of the transfer process.

## Features
- **Device Monitoring**: Automatically detects and displays the connection status of SD cards and USB drives.
- **Data Transfer**: Facilitates the copying of data from the SD card to the USB drive and from the USB drive to the MinIO server.
- **Progress Monitoring**: Provides real-time feedback on the data transfer process, including speed, transferred amount, and estimated time of completion.
- **Fullscreen Toggle**: Includes a fullscreen mode for distraction-free operation, with the ability to toggle between fullscreen and windowed modes.

## Prerequisites
- Python 3.x
- Tkinter library for Python
- Access to the Raspberry Pi's terminal and GUI interface.

## Touch screen setup
    If you have a 3.5 inch touch screen, setup is as follows:
    
    ```git clone  https://github.com/goodtft/LCD-show.git
    chmod -R 755 LCD-show 
    cd LCD-show/
    sudo ./LCD35-show 180
    ```

## Installation
1. **Prepare the Environment**
    Ensure that your Raspberry Pi is set up with Python 3.x and the necessary permissions. Open the terminal and edit the `.profile` file:

    ```bash
    nano ~/.profile
    ```

    Add the following line to the end of the file:

    ```bash
    export DISPLAY=:0
    ```

    Save and exit the editor (Ctrl + O, Enter, Ctrl + X in nano).

2. **Clone the Repository**
    Clone the repository to a preferred directory, for example, `/home/pi/SeaBee-rpi-uploader/`.

3. **Set Script Permissions**
    Give execution permissions to the main Python script and the `.desktop` file:

    ```bash
    chmod +x /home/pi/SeaBee-rpi-uploader/guiapp.py
    chmod +x /home/pi/SeaBee-rpi-uploader/SeaBeeUploader.desktop
    ```

4. **Create Desktop Shortcut**
    Create a desktop shortcut for easy access:

    ```bash
    cp /home/pi/SeaBee-rpi-uploader/SeaBeeUploader.desktop /home/pi/Desktop/SeaBeeUploader.desktop
    ```

5. **Configure Autostart (Optional)**
    If you want the application to start automatically when the Raspberry Pi boots, create an autostart directory and copy the `.desktop` file there:

    ```bash
    mkdir /home/pi/.config/autostart
    cp /home/pi/SeaBee-rpi-uploader/SeaBeeUploader.desktop /home/pi/.config/autostart/SeaBeeUploader.desktop
    ```

## Usage
- Double-click the `SeaBeeUploader.desktop` shortcut on your Raspberry Pi desktop to start the application.
- The application's GUI will display the status of the SD card and USB drive.
- Once both devices are detected and ready, you can initiate the data transfer process.
- Monitor the transfer progress through the GUI.
- Use the "Toggle Fullscreen" button to switch between fullscreen and windowed modes.
