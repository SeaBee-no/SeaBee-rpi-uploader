#!/usr/bin/env python3

import tkinter as tk
from tkinter import PhotoImage
import subprocess
import os
import glob
import threading
import queue
import re

# Global variables to store paths
sdcard_path = None
usbdrive_path = None
is_transfer_active = False
miniobucket = 'seabirds'

def check_storage_devices():
    try:
        global is_transfer_active
        # Return early if a transfer is in progress
        if is_transfer_active:
            return
        global sdcard_path, usbdrive_path
        mountdir = "/media/pi/"
        folders = os.listdir(mountdir)
        
        # Initialize status
        sd_card_ready = False
        harddrive_connected = False
        sd_card_mission_count = 0

        for folder in folders:
            folder_path = os.path.join(mountdir, folder)
            
            # Check for SD card based on specific content (e.g., "DCIM" directory and "DJI_*" files)
            if "DCIM" in os.listdir(folder_path):
                missionfolders = glob.glob(os.path.join(folder_path, "DCIM", "DJI_*"))
                sd_card_manual_count = 0
                sd_card_mission_count = 0

                for folder in missionfolders:
                    # Extract the folder name and split it by '_'
                    folder_name = os.path.basename(folder)
                    parts = folder_name.split('_')

                    # Count based on the number of parts
                    if len(parts) == 3:
                        sd_card_manual_count += 1
                    elif len(parts) == 4:
                        sd_card_mission_count += 1

                if missionfolders:
                    sd_card_ready = True
                    sdcard_path = folder_path  # Store the SD card path


            # Check for hard drive based on mount status and ensure it's not the SD card
            if os.path.ismount(folder_path) and "DCIM" not in os.listdir(folder_path):
                harddrive_connected = True
                usbdrive_path = folder_path  # Store the USB drive path

        # Update GUI based on device status
        if sd_card_ready:
            update_sd_card_status("READY", sd_card_mission_count, sd_card_manual_count)  # Update with actual numbers
        else:
            update_sd_card_status("Not connected")

        if harddrive_connected:
            update_harddrive_status("CONNECTED")
        else:
            update_harddrive_status("Not connected")
            
        # Enable the action button if both SD card and hard drive are ready/connected
        if sd_card_ready and harddrive_connected:
            action_button.config(state=tk.NORMAL, text="Do Both")
        else:
            action_button.config(state=tk.DISABLED, text="Do Both")
    except Exception as e:
        print("Error:", e)

    # Schedule this function to run again after some time (e.g., 5000 milliseconds)
    root.after(5000, check_storage_devices)


def update_sd_card_status(status, missions_count=0, manual_count=0):
    global sdcard_path  # Make sure to use the global variable
    if status == "READY":
        canvas.itemconfig(sd_card_box, fill="green")  # Change color of the canvas rectangle
        sd_card_label.config(bg="green", text=f"SD Card\n{missions_count} missions\n{manual_count} manual")
        sd_card_path_label.config(bg="green", text=f"{sdcard_path}")
    else:
        canvas.itemconfig(sd_card_box, fill="grey")  # Change color of the canvas rectangle
        sd_card_label.config(bg="grey", text="SD Card\nNot connected")
        sd_card_path_label.config(bg="grey", text="")  # Clear path text

def update_harddrive_status(status):
    global usbdrive_path  # Make sure to use the global variable
    if status == "CONNECTED":
        canvas.itemconfig(harddrive_box, fill="green")  # Change color of the canvas rectangle
        harddrive_label.config(bg="green", text="Hard Drive\nConnected")
        harddrive_path_label.config(bg="green", text=f"{usbdrive_path}")
    else:
        canvas.itemconfig(harddrive_box, fill="grey")  # Change color of the canvas rectangle
        harddrive_label.config(bg="grey", text="Hard Drive\nNot connected")
        harddrive_path_label.config(bg="grey", text="")  # Clear path text

def check_internet_connectivity():
    try:
        response = subprocess.run(['ping', '-c', '1', '8.8.8.8'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if response.returncode == 0:
            update_internet_status("Connected")
        else:
            update_internet_status("Disconnected")
    except Exception as e:
        print("Failed to check internet connectivity:", e)
        update_internet_status("Disconnected")

    root.after(10000, check_internet_connectivity)  # Check every 10 seconds

def update_internet_status(status):
    if status == "Connected":
        wifi_status_label.config(image=wifi_connected_icon)
    else:
        wifi_status_label.config(image=wifi_disconnected_icon)

# Function to create a rounded rectangle on the canvas
# this function currently dont work as intended, but is still in use
def create_rounded_rect(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    points = [
        x1+radius, y1,
        x1+radius, y1, x2-radius, y1,
        x2-radius, y1, x2, y1, x2, y1+radius,
        x2, y1+radius, x2, y2-radius,
        x2, y2-radius, x2, y2, x2-radius, y2,
        x2-radius, y2, x1+radius, y2,
        x1+radius, y2, x1, y2, x1, y2-radius,
        x1, y2-radius, x1, y1+radius,
        x1, y1+radius, x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)


def perform_action():
    global is_transfer_active

    # Disable the button to prevent multiple clicks
    action_button.config(state=tk.DISABLED, text="Transfering...")
    
    # Indicate that a transfer is now active
    is_transfer_active = True

    # Start the sequence of commands
    execute_command_sequence()

def execute_command_sequence():
    global sdcard_path, usbdrive_path, miniobucket
    # Ensure paths are set
    if not sdcard_path or not usbdrive_path:
        print("SD card or USB drive path not set.")
        return

    # Define the sequence of commands
    commands = [
        f"rclone copy {sdcard_path}/DCIM {usbdrive_path} --progress",
        f"umount {sdcard_path}",  # Uncomment and modify if needed
        f"rclone copy {usbdrive_path} minio:{miniobucket}/fielduploads --progress"
    ]

    # Start the first command. The rest will be triggered sequentially after each command completes
    if commands:
        process_thread = threading.Thread(target=run_command, args=(commands, 0))
        process_thread.start()


def run_command(commands, index):
    command = commands[index]
    # Store the command at the top
    showcommand = command.replace('rclone copy ', '').replace(' --progress', '').replace(' ', ' to ')
    command_display = f"Copying {showcommand}\n"
    output_queue.put(command_display)

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    # Regex pattern to match lines containing the progress information
    progress_pattern = re.compile(
        r'Transferred:\s+([\d.]+\s+[kMGTP]iB)\s+/.*?([\d.]+\s+[kMGTP]iB),\s*(\d+%).*?(\d+.\d+\s+[kMGTP]iB/s).*?ETA\s+(.+)'
    )

    # Initialize an empty string to store the progress information
    progress_info = ""

    while True:
        line = process.stdout.readline()
        if line == '' and process.poll() is not None:
            break
        
        # Check if the line contains the progress information
        match = progress_pattern.search(line)
        if match:
            # Extract transferred amount, total amount, percentage, transfer speed, and ETA
            transferred, total, percentage, speed, eta = match.groups()
            # Prepare the progress information
            progress_info = f"\nTransferred: {transferred} / {total} ({percentage})\nSpeed: {speed}\nETA: {eta}"
        
        # Update the output with the command followed by the latest progress information
        output_queue.put(command_display + progress_info)

    # When the command is finished, put a special message in the queue
    output_queue.put(f"{command_display}{progress_info}\nCommand completed")

    # if we umount, display it on the screen
    if "umount" in command:
        update_sd_card_status("Unmounted")
        sd_card_label.config(bg="grey", text="SD Card\nSafe to remove")
    
    # Check if there are more commands to run
    next_index = index + 1
    if next_index < len(commands):
        # If there are, start the next command
        next_process_thread = threading.Thread(target=run_command, args=(commands, next_index))
        next_process_thread.start()
    else:
        # If there are no more commands, put a special message indicating all commands are completed
        output_queue.put("ALL_COMMANDS_FINISHED")


def update_output():
    try:
        global is_transfer_active
        # Initialize the latest output
        latest_output = None
        
        # Loop to read all available messages in the queue, keeping only the last one
        while not output_queue.empty():
            latest_output = output_queue.get_nowait()
        
        if latest_output is None:
            # No new messages, so don't update the label
            pass
        elif latest_output == "ALL_COMMANDS_FINISHED":
            # All commands have finished, update the button status
            action_button.config(state=tk.NORMAL, text="Copy and Upload Data")
            is_transfer_active = False
        else:
            # Update the Label with the most recent output, including the command
            output_label.config(text=latest_output)
            
    except queue.Empty:
        pass

    # Schedule the next call
    root.after(100, update_output)

def toggle_fullscreen():
    global is_fullscreen  # Use a global variable to track the fullscreen state
    is_fullscreen = not is_fullscreen  # Toggle the state
    root.attributes('-fullscreen', is_fullscreen)
    # Update the button text based on the current state
    if is_fullscreen:
        toggle_button.config(text="Exit")
    else:
        toggle_button.config(text="Enter")

def copy_to_hard_drive():
    global sdcard_path, usbdrive_path
    if not sdcard_path or not usbdrive_path:
        print("SD card or USB drive path not set.")
        return
    command = f"rclone copy {sdcard_path}/DCIM {usbdrive_path} --progress"
    process_thread = threading.Thread(target=run_command, args=([command], 0))
    process_thread.start()

def upload_to_cloud():
    global usbdrive_path, miniobucket
    if not usbdrive_path:
        print("USB drive path not set.")
        return
    command = f"rclone copy {usbdrive_path} minio:{miniobucket}/fielduploads --progress"
    process_thread = threading.Thread(target=run_command, args=([command], 0))
    process_thread.start()

def update_gui_status():
    global sdcard_path, usbdrive_path
    if sdcard_path and usbdrive_path:
        copy_button.config(state=tk.NORMAL)
    else:
        copy_button.config(state=tk.DISABLED)
    
    if usbdrive_path:
        upload_button.config(state=tk.NORMAL)
    else:
        upload_button.config(state=tk.DISABLED)

    # Update statuses regularly
    root.after(5000, update_gui_status)

# Create the main window
root = tk.Tk()
is_fullscreen = True
root.attributes('-fullscreen', is_fullscreen)

# Hide the mouse cursor over the root window
root.config(cursor="none")

window_width = root.winfo_screenwidth()
window_height = root.winfo_screenheight()

# Create a Canvas
canvas = tk.Canvas(root, height=300, bg='white')
canvas.pack(fill='both', expand=True)

root.update()  # Force update of root dimensions

# Calculate positions for centering
box_width = 150
box_height = 120
action_button_width = 140
both_button_width = 100
action_button_height = 60
space_between_boxes = 50
total_width = 2 * box_width + space_between_boxes
start_x = (window_width - total_width) / 2
start_y = 10


# Draw rounded rectangles for SD Card and Hard Drive ONLY ONCE
sd_card_box = create_rounded_rect(canvas, start_x, start_y, start_x + box_width, start_y + box_height, radius=20, fill="grey")
harddrive_box = create_rounded_rect(canvas, start_x + box_width + space_between_boxes, start_y, start_x + 2 * box_width + space_between_boxes, start_y + box_height, radius=20, fill="grey")

# Label to display the SD card status
sd_card_label = tk.Label(root, text="", fg="white", bg="grey", font=('Helvetica', 14), anchor="center")
sd_card_label.place(x=start_x, y=start_y, width=box_width, height=box_height)

# Label to display the Hard Drive status
harddrive_label = tk.Label(root, text="Hard Drive\nNot connected", fg="white", bg="grey", font=('Helvetica', 14), anchor="center")
harddrive_label.place(x=start_x + box_width + space_between_boxes, y=start_y, width=box_width, height=box_height)

# Label to display the SD card path
sd_card_path_label = tk.Label(root, fg="white", bg="grey", font=('Helvetica', 7), anchor="center")
sd_card_path_label.place(x=start_x, y=start_y + box_height - 30, width=box_width, height=20)

# Label to display the Hard Drive path
harddrive_path_label = tk.Label(root, fg="white", bg="grey", font=('Helvetica', 7), anchor="center")
harddrive_path_label.place(x=start_x + box_width + space_between_boxes, y=start_y + box_height - 30, width=box_width, height=20)

# Button to toggle fullscreen mode
toggle_button = tk.Button(root, text="Exit", command=toggle_fullscreen, bg="#eee")
toggle_button.place(x=10, y=10, width=40, height=40)

# Using a Label for output
output_label = tk.Label(root, text="", fg="black", bg="white", font=('Helvetica', 10))
output_label.place(x=5, y=start_y + box_height + 80, width=window_width - 10, height=100)

# Button for performing an action when both SD card and hard drive are ready
action_button = tk.Button(root, text="Do Both", command=perform_action, state=tk.DISABLED)#, bg="lightgrey", fg="white")
action_button.place(x=window_width / 2 - both_button_width / 2, y=start_y + box_height + 10, width=both_button_width, height=action_button_height)

# Button for copying data from SD card to hard drive
copy_button = tk.Button(root, text="Copy to Hard Drive", command=copy_to_hard_drive, state=tk.DISABLED)
copy_button.place(x=window_width / 2 - action_button_width / 2 - 130, y=start_y + box_height + 10, width=action_button_width, height=action_button_height)

# Button for uploading data from hard drive to MinIO
upload_button = tk.Button(root, text="Upload to Cloud", command=upload_to_cloud, state=tk.DISABLED)
upload_button.place(x=window_width / 2 - action_button_width / 2 + 130, y=start_y + box_height + 10, width=action_button_width, height=action_button_height)

# Load WiFi icons
wifi_connected_icon = PhotoImage(file="/home/pi/SeaBee-rpi-uploader/wifi_connected.png")
wifi_disconnected_icon = PhotoImage(file="/home/pi/SeaBee-rpi-uploader/wifi_disconnected.png")

# Create a Label for the WiFi status
wifi_status_label = tk.Label(root, image=wifi_disconnected_icon)
wifi_status_label.place(x=440, y=10, width=30, height=30)  # Adjust size and position as needed

# Start the periodic update for SD card and hard drive
check_storage_devices()
output_queue = queue.Queue()
update_output()  # Start the periodic update loop
check_internet_connectivity()  # Start checking internet connectivity status
update_gui_status()


# Start the GUI event loop
root.mainloop()