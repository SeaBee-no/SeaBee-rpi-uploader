#!/usr/bin/env python3

import tkinter as tk
from tkinter import PhotoImage
import subprocess
import os
import glob
import threading
import queue
import re
import yaml

# Global variables to store paths
sdcard_path = None
usbdrive_path = None
internet_connected = False
is_transfer_active = False
miniobucket = 'seabirds'
default_config_path = "/home/pi/SeaBee-rpi-uploader/default_config.yaml"

# Load the default configuration
with open(default_config_path, 'r', encoding='utf-8') as file:
    default_config = yaml.safe_load(file)

def check_storage_devices():
    try:
        global is_transfer_active
        global internet_connected
        if is_transfer_active:
            return
        global sdcard_path, usbdrive_path
        mountdir = "/media/pi/"
        folders = os.listdir(mountdir)
        
        sd_card_ready = False
        harddrive_connected = False
        sd_card_mission_count = 0
        hd_mission_count = 0
        sd_card_manual_count = 0
        hd_manual_count = 0

        for folder in folders:
            folder_path = os.path.join(mountdir, folder)
            
            if "DCIM" in os.listdir(folder_path):
                missionfolders = glob.glob(os.path.join(folder_path, "DCIM", "DJI_*"))
                sd_card_manual_count = 0
                sd_card_mission_count = 0

                for mission_folder in missionfolders:
                    folder_name = os.path.basename(mission_folder)
                    parts = folder_name.split('_')

                    if len(parts) == 3:
                        sd_card_manual_count += 1
                    elif len(parts) == 4:
                        sd_card_mission_count += 1

                if missionfolders:
                    sd_card_ready = True
                    sdcard_path = folder_path

            elif os.path.ismount(folder_path):
                missionfolders = glob.glob(os.path.join(folder_path, "DJI_*"))
                hd_manual_count = 0
                hd_mission_count = 0

                for mission_folder in missionfolders:
                    folder_name = os.path.basename(mission_folder)
                    parts = folder_name.split('_')

                    if len(parts) == 3:
                        hd_manual_count += 1
                    elif len(parts) == 4:
                        hd_mission_count += 1

                harddrive_connected = True
                usbdrive_path = folder_path

        if sd_card_ready:
            update_sd_card_status("READY", sd_card_mission_count, sd_card_manual_count)
        else:
            update_sd_card_status("Not connected")

        if harddrive_connected:
            update_harddrive_status("CONNECTED", hd_mission_count, hd_manual_count)
        else:
            update_harddrive_status("Not connected")
        
        if internet_connected:
            uploadpossible = 1
        else:
            uploadpossible = 0

        if sd_card_ready and harddrive_connected:
            configure_buttons([1,1,uploadpossible])
        elif sd_card_ready and not harddrive_connected:
            configure_buttons([0,0,0])
        elif not sd_card_ready and harddrive_connected:
            configure_buttons([0,0,uploadpossible])
        else:
            configure_buttons([0,0,0])
    except Exception as e:
        print("Error:", e)

    root.after(5000, check_storage_devices)


def update_sd_card_status(status, missions_count=0, manual_count=0):
    global sdcard_path
    if status == "READY":
        canvas.itemconfig(sd_card_box, fill="green")
        sd_card_label.config(bg="green", text=f"SD Card\n{missions_count} missions\n{manual_count} manual")
        sd_card_path_label.config(bg="green", text=f"{sdcard_path}")
    else:
        canvas.itemconfig(sd_card_box, fill="grey")
        sd_card_label.config(bg="grey", text="SD Card\nNot connected")
        sd_card_path_label.config(bg="grey", text="")


def update_harddrive_status(status, missions_count=0, manual_count=0):
    global usbdrive_path
    if status == "CONNECTED":
        canvas.itemconfig(harddrive_box, fill="green")
        harddrive_label.config(bg="green", text=f"Hard Drive\n{missions_count} missions\n{manual_count} manual")
        harddrive_path_label.config(bg="green", text=f"{usbdrive_path}")
    else:
        canvas.itemconfig(harddrive_box, fill="grey")
        harddrive_label.config(bg="grey", text="Hard Drive\nNot connected")
        harddrive_path_label.config(bg="grey", text="")


def check_internet_connectivity():
    global internet_connected
    try:
        response = subprocess.run(['ping', '-c', '1', '8.8.8.8'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if response.returncode == 0:
            update_internet_status("Connected")
            internet_connected = True
        else:
            update_internet_status("Disconnected")
            internet_connected = False
    except Exception as e:
        print("Failed to check internet connectivity:", e)
        update_internet_status("Disconnected")
        internet_connected = False

    root.after(10000, check_internet_connectivity)


def update_internet_status(status):
    if status == "Connected":
        wifi_status_label.config(image=wifi_connected_icon)
    else:
        wifi_status_label.config(image=wifi_disconnected_icon)


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


def perform_action(action):
    global is_transfer_active

    configure_buttons([0,0,0])
    is_transfer_active = True

    execute_command_sequence(action)


def execute_command_sequence(action):
    global sdcard_path, usbdrive_path, miniobucket
    if not sdcard_path or not usbdrive_path:
        print("SD card or USB drive path not set.")
        return

    if action == 'both':
        commands = [
            f"rclone copy {sdcard_path}/DCIM/ {usbdrive_path} --progress",
            f"umount {sdcard_path}",
            f"rclone copy {usbdrive_path} minio:{miniobucket}/fielduploads --progress"
        ]
    elif action == 'copy':
        commands = [
            f"rclone copy {sdcard_path}/DCIM/ {usbdrive_path} --progress",
            f"umount {sdcard_path}",
        ]
    elif action == 'upload':
        commands = [
            f"rclone copy {usbdrive_path} minio:{miniobucket}/fielduploads --progress"
        ]

    if commands:
        process_thread = threading.Thread(target=run_command, args=(commands, 0))
        process_thread.start()


def create_config_file(folder_path, nfiles):
    config_data = default_config.copy()  # Start with the default configuration
    config_data.update({
        'nfiles': nfiles,
        'datetime': '',  # Always set datetime to an empty string
    })
    config_path = os.path.join(folder_path, 'config.seabee.yaml')
    with open(config_path, 'w', encoding='utf-8') as config_file:
        yaml.dump(config_data, config_file, default_flow_style=False, allow_unicode=True)


def run_command(commands, index):
    command = commands[index]
    showcommand = command.replace('rclone copy ', '').replace(' --progress', '').replace(' ', ' to ')
    command_display = f"Copying {showcommand}\n"
    output_queue.put(command_display)

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    progress_pattern = re.compile(
        r'Transferred:\s+([\d.]+\s+[kMGTP]iB)\s+/.*?([\d.]+\s+[kMGTP]iB),\s*(\d+%).*?(\d+.\d+\s+[kMGTP]iB/s).*?ETA\s+(.+)'
    )

    progress_info = ""

    while True:
        line = process.stdout.readline()
        if line == '' and process.poll() is not None:
            break
        
        match = progress_pattern.search(line)
        if match:
            transferred, total, percentage, speed, eta = match.groups()
            progress_info = f"\nTransferred: {transferred} / {total} ({percentage})\nSpeed: {speed}\nETA: {eta}"
        
        output_queue.put(command_display + progress_info)

    output_queue.put(f"{command_display}{progress_info}\nCommand completed")

    if "rclone copy" in command and "DCIM" in command:
        destination_path = usbdrive_path
        for folder in glob.glob(os.path.join(destination_path, "DJI_*")):
            nfiles = len([file for file in os.listdir(folder) if not file.endswith('.yaml')])
            create_config_file(folder, nfiles)

    if "umount" in command:
        update_sd_card_status("Unmounted")
        sd_card_label.config(bg="grey", text="SD Card\nSafe to remove")
    
    next_index = index + 1
    if next_index < len(commands):
        next_process_thread = threading.Thread(target=run_command, args=(commands, next_index))
        next_process_thread.start()
    else:
        output_queue.put("ALL_COMMANDS_FINISHED")


def update_output():
    try:
        global is_transfer_active
        latest_output = None
        
        while not output_queue.empty():
            latest_output = output_queue.get_nowait()
        
        if latest_output is None:
            pass
        elif latest_output == "ALL_COMMANDS_FINISHED":
            configure_buttons([1,1,1])
            is_transfer_active = False
            output_label.config(text="All commands completed")
            check_storage_devices()
        else:
            output_label.config(text=latest_output)
            
    except queue.Empty:
        pass

    root.after(100, update_output)


def configure_buttons(newstate=[1,1,1]):
    if newstate[0] == 1:
        copy_button.config(state=tk.NORMAL)
    else:
        copy_button.config(state=tk.DISABLED)
    if newstate[1] == 1:
        action_button.config(state=tk.NORMAL)
    else:
        action_button.config(state=tk.DISABLED)
    if newstate[2] == 1:
        upload_button.config(state=tk.NORMAL)
    else:
        upload_button.config(state=tk.DISABLED)


def toggle_fullscreen():
    global is_fullscreen
    is_fullscreen = not is_fullscreen
    root.attributes('-fullscreen', is_fullscreen)
    if is_fullscreen:
        toggle_button.config(text="Exit")
    else:
        toggle_button.config(text="Enter")


def unmount_devices():
    global sdcard_path, usbdrive_path
    if sdcard_path:
        try:
            subprocess.run(['umount', sdcard_path], check=True)
        except:
            pass
    if usbdrive_path:
        try:
            subprocess.run(['umount', usbdrive_path], check=True)
        except:
            pass


root = tk.Tk()
is_fullscreen = True
root.attributes('-fullscreen', is_fullscreen)
root.config(cursor="none")

window_width = root.winfo_screenwidth()
window_height = root.winfo_screenheight()

canvas = tk.Canvas(root, height=300, bg='white')
canvas.pack(fill='both', expand=True)

root.update()

box_width = 150
box_height = 120
action_button_width = 140
both_button_width = 100
action_button_height = 60
space_between_boxes = 50
total_width = 2 * box_width + space_between_boxes
start_x = (window_width - total_width) / 2
start_y = 10

sd_card_box = create_rounded_rect(canvas, start_x, start_y, start_x + box_width, start_y + box_height, radius=20, fill="grey")
harddrive_box = create_rounded_rect(canvas, start_x + box_width + space_between_boxes, start_y, start_x + 2 * box_width + space_between_boxes, start_y + box_height, radius=20, fill="grey")

sd_card_label = tk.Label(root, text="", fg="white", bg="grey", font=('Helvetica', 14), anchor="center")
sd_card_label.place(x=start_x, y=start_y, width=box_width, height=box_height)

harddrive_label = tk.Label(root, text="Hard Drive\nNot connected", fg="white", bg="grey", font=('Helvetica', 14), anchor="center")
harddrive_label.place(x=start_x + box_width + space_between_boxes, y=start_y, width=box_width, height=box_height)

sd_card_path_label = tk.Label(root, fg="white", bg="grey", font=('Helvetica', 7), anchor="center")
sd_card_path_label.place(x=start_x, y=start_y + box_height - 30, width=box_width, height=20)

harddrive_path_label = tk.Label(root, fg="white", bg="grey", font=('Helvetica', 7), anchor="center")
harddrive_path_label.place(x=start_x + box_width + space_between_boxes, y=start_y + box_height - 30, width=box_width, height=20)

toggle_button = tk.Button(root, text="Exit", command=toggle_fullscreen, bg="#eee")
toggle_button.place(x=10, y=10, width=40, height=40)

output_label = tk.Label(root, text="", fg="black", bg="white", font=('Helvetica', 10))
output_label.place(x=5, y=start_y + box_height + 80, width=window_width - 10, height=100)

action_button = tk.Button(root, text="Do Both", command=lambda: perform_action('both'), state=tk.DISABLED)
action_button.place(x=window_width / 2 - both_button_width / 2, y=start_y + box_height + 10, width=both_button_width, height=action_button_height)

copy_button = tk.Button(root, text="Copy to Hard Drive", command=lambda: perform_action('copy'), state=tk.DISABLED)
copy_button.place(x=window_width / 2 - action_button_width / 2 - 130, y=start_y + box_height + 10, width=action_button_width, height=action_button_height)

upload_button = tk.Button(root, text="Upload to Cloud", command=lambda: perform_action('upload'), state=tk.DISABLED)
upload_button.place(x=window_width / 2 - action_button_width / 2 + 130, y=start_y + box_height + 10, width=action_button_width, height=action_button_height)

wifi_connected_icon = PhotoImage(file="/home/pi/SeaBee-rpi-uploader/wifi_connected.png")
wifi_disconnected_icon = PhotoImage(file="/home/pi/SeaBee-rpi-uploader/wifi_disconnected.png")

wifi_status_label = tk.Label(root, image=wifi_disconnected_icon)
wifi_status_label.place(x=440, y=10, width=30, height=30)

unmount_icon = PhotoImage(file="/home/pi/SeaBee-rpi-uploader/unmount_icon.png")
unmount_button = tk.Button(root, image=unmount_icon, command=unmount_devices, state=tk.NORMAL)
unmount_button.place(x=435, y=50, width=40, height=40)

check_storage_devices()
output_queue = queue.Queue()
update_output()
check_internet_connectivity()

root.mainloop()
