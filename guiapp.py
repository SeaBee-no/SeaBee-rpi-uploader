import tkinter as tk
import subprocess
import os
import glob
import threading
import queue
import re
from tkinter import simpledialog, messagebox

class WifiManagementWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('WiFi Management')
        
        # Set fullscreen
        self.attributes('-fullscreen', True)
        
        # Hide the mouse cursor over the window
        self.config(cursor="none")
        
        # Add a button to close the window
        self.close_button = tk.Button(self, text="Close Window", command=self.close_window)
        self.close_button.pack()

        # Create widgets (listbox, buttons, labels, etc.)
        self.create_widgets()

    def close_window(self):
        # Close the window
        self.destroy()

    def create_widgets(self):
        # Button to scan for WiFi networks
        self.scan_button = tk.Button(self, text="Scan for Networks", command=self.scan_wifi_networks)
        self.scan_button.pack()

        # Listbox to display the list of networks
        self.networks_listbox = tk.Listbox(self)
        self.networks_listbox.pack()

        # Button to connect to the selected network
        self.connect_button = tk.Button(self, text="Connect to Selected Network", command=self.connect_to_selected_network)
        self.connect_button.pack()

        # Label to show connection status
        self.status_label = tk.Label(self, text="Not Connected")
        self.status_label.pack()

    def scan_wifi_networks(self):
        # Clear the listbox
        self.networks_listbox.delete(0, tk.END)
        
        # Command to scan for WiFi networks
        command = ['nmcli', '-f', 'SSID', 'device', 'wifi', 'list']
        try:
            # Run the command
            scan_result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
            # Decode and split the output to get the list of networks
            networks = scan_result.stdout.strip().split('\n')
            # Skip the first line (it's the header)
            for network in networks[1:]:
                network_name = network.strip()
                if network_name:  # Check if the network name is not empty
                    self.networks_listbox.insert(tk.END, network_name)
        except Exception as e:
            print(f"An error occurred while scanning for WiFi networks: {e}")

    def connect_to_selected_network(self):
        # Get the selected network
        selection = self.networks_listbox.curselection()
        if selection:
            selected_network = self.networks_listbox.get(selection)
            
            # Prompt for the password using the custom dialog
            password = get_password(self, title="Password", message=f"Enter password for {selected_network}")
            
            if password is not None and password != "":
                # Attempt to connect to the network using the provided password
                try:
                    # Command to connect to the WiFi network with a password
                    connect_command = ['nmcli', 'device', 'wifi', 'connect', selected_network, 'password', password]
                    connect_result = subprocess.run(connect_command, stdout=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
                    
                    if connect_result.returncode == 0:
                        # Successfully connected
                        self.status_label.config(text=f"Connected to {selected_network}")
                    else:
                        # Failed to connect
                        messagebox.showerror("Connection Failed", f"Failed to connect to {selected_network}\n{connect_result.stderr}")
                except Exception as e:
                    messagebox.showerror("Error", f"An error occurred while connecting to the WiFi network: {e}")
            elif password == "":
                messagebox.showwarning("No Password", "No password was entered. Please try again.")
        else:
            messagebox.showerror("Selection Error", "Please select a network from the list.")


class OnScreenKeyboard(tk.Toplevel):
    def __init__(self, parent, entry_widget):
        super().__init__(parent)
        self.entry_widget = entry_widget  # The text entry widget where the keys will be sent
        self.title('On-Screen Keyboard')
        self.create_keyboard()

    def create_keyboard(self):
        # Define keyboard layout
        rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Backspace'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', '-', '_'],
            ['Space']
        ]

        for r_index, row in enumerate(rows):
            for k_index, key in enumerate(row):
                button = tk.Button(self, text=key, command=lambda key=key: self.key_press(key))
                button.grid(row=r_index, column=k_index, sticky="nsew", padx=5, pady=5)
                
        # Make the buttons expand
        for r_index in range(len(rows)):
            self.grid_rowconfigure(r_index, weight=1)
        for c_index in range(len(rows[0])):
            self.grid_columnconfigure(c_index, weight=1)

    def key_press(self, key):
        if key == 'Backspace':
            current_text = self.entry_widget.get()
            # remove the last character
            new_text = current_text[:-1]
            self.entry_widget.delete(0, tk.END)
            self.entry_widget.insert(0, new_text)
        elif key == 'Space':
            self.entry_widget.insert(tk.END, ' ')
        else:
            self.entry_widget.insert(tk.END, key)

class PasswordDialog(tk.Toplevel):
    def __init__(self, parent, title="Enter password", message="Enter password for the network"):
        super().__init__(parent)
        self.title(title)
        self.result = None

        # Message label
        tk.Label(self, text=message).pack(pady=10)

        # Password entry
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack(pady=10)
        self.password_entry.focus_set()  # Focus on the entry widget

        # Submit button
        submit_button = tk.Button(self, text="Submit", command=self.on_submit)
        submit_button.pack(pady=10)

        # Open on-screen keyboard when the entry widget is focused
        self.password_entry.bind("<FocusIn>", self.open_on_screen_keyboard)

    def open_on_screen_keyboard(self, event):
        OnScreenKeyboard(self, self.password_entry)

    def on_submit(self):
        self.result = self.password_entry.get()
        self.destroy()

def get_password(parent, title="Enter password", message="Enter password for the network"):
    dialog = PasswordDialog(parent, title, message)
    parent.wait_window(dialog)
    return dialog.result

# Global variables to store paths
sdcard_path = None
usbdrive_path = None
is_transfer_active = False

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
            action_button.config(state=tk.NORMAL, text="Copy and Upload Data")
        else:
            action_button.config(state=tk.DISABLED, text="Waiting...")
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

# Function to create a rounded rectangle on the canvas
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
    global sdcard_path, usbdrive_path
    # Ensure paths are set
    if not sdcard_path or not usbdrive_path:
        print("SD card or USB drive path not set.")
        return

    # Define the sequence of commands
    commands = [
        f"rclone copy {sdcard_path}/DCIM {usbdrive_path} --progress",
        f"umount {sdcard_path}",  # Uncomment and modify if needed
        f"rclone copy {usbdrive_path} minio:seabirds/fielduploads --progress"
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

# Function to open the WiFi management window
def open_wifi_management():
    WifiManagementWindow(root)




# Create the main window
root = tk.Tk()
root.attributes('-fullscreen', True)

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
action_button_width = 170
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

# Button for WiFi management
wifi_button = tk.Button(root, text="Manage WiFi", command=open_wifi_management, bg="lightgrey", fg="black")
wifi_button.place(x=start_x + 2 * box_width + 2 * space_between_boxes, y=start_y, width=box_width, height=box_height)

# Button for performing an action when both SD card and hard drive are ready
action_button = tk.Button(root, text="Waiting...", command=perform_action, state=tk.DISABLED)#, bg="lightgrey", fg="white")
action_button.place(x=window_width / 2 - action_button_width / 2, y=start_y + box_height + 10, width=action_button_width, height=action_button_height)

# Using a Label for output
output_label = tk.Label(root, text="", fg="black", bg="white", font=('Helvetica', 10))
output_label.place(x=5, y=start_y + box_height + 80, width=window_width - 10, height=100)

# Start the periodic update for SD card and hard drive
check_storage_devices()
output_queue = queue.Queue()
update_output()  # Start the periodic update loop


# Start the GUI event loop
root.mainloop()