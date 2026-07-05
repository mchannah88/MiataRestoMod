import serial
import serial.tools.list_ports
import subprocess
import time
import dbus

# Adafruit Huzzah32 (CP2104) Hardware IDs
TARGET_VID = 0x1a86
TARGET_PID = 0x55d4
BAUD_RATE = 115200

# Path configuration for system brightness toggles
BRIGHTNESS_FILE = "/sys/class/backlight/rpi_backlight/brightness" 
MIN_BRIGHT = "15"
MAX_BRIGHT = "255"
brightness_high = True

def skip_forward_dbus():
    bus = dbus.SessionBus()
    # This finds players that support the MPRIS interface
    for name in bus.list_names():
        if name.startswith('org.mpris.MediaPlayer2.'):
            player = bus.get_object(name, '/org/mpris/MediaPlayer2')
            player.Next(dbus_interface='org.mpris.MediaPlayer2.Player')
            
def find_esp32():
    """Scans all USB ports and returns the path to the ESP32."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == TARGET_VID and port.pid == TARGET_PID:
            return port.device
    return None

def run_cmd(cmd):
    """Runs a standard bash command."""
    try:
        subprocess.Popen(cmd, shell=True)
    except Exception as e:
        print(f"Error running command: {e}")

def focus_or_launch(window_name, launch_cmd):
    """
    Forces focus by filtering only for visible windows.
    """
    # Use --onlyvisible to filter out system/hidden windows that cause the error
    # We use head -n 1 to ensure we only get the first ID found
    search_cmd = f"xdotool search --onlyvisible --name '{window_name}' | head -n 1"
    
    try:
        # Get the ID
        window_id = subprocess.check_output(search_cmd, shell=True).decode().strip()
        
        if not window_id:
            raise subprocess.CalledProcessError(1, search_cmd)
        
        # Now activate it
        subprocess.run(f"xdotool windowmap {window_id}", shell=True)
        subprocess.run(f"xdotool windowraise {window_id}", shell=True)
        subprocess.run(f"xdotool windowactivate {window_id}", shell=True)
        print(f"Focused '{window_name}' (ID: {window_id})")
        
    except (subprocess.CalledProcessError, IndexError):
        print(f"'{window_name}' not running or visible. Launching...")
        subprocess.Popen(launch_cmd, shell=True)


print("Searching for Dashboard Controller...")
ser = None

# Keep searching until the device is found and connected
while True:
    port_path = find_esp32()
    
    if port_path:
        try:
            ser = serial.Serial(port_path, BAUD_RATE, timeout=1)
            print(f"Connected successfully on {port_path}!")
            break
        except serial.SerialException:
            print(f"Found ESP32 on {port_path}, but couldn't open it. Retrying...")
            time.sleep(2)
    else:
        print("ESP32 not found. Is it plugged in? Retrying in 2 seconds...")
        time.sleep(2)

# Main Listening Loop
try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            print(f"Received: {line}")
            
            if line == "VOL_UP":
                run_cmd("pactl set-sink-volume @DEFAULT_SINK@ +5%")
            elif line == "VOL_DOWN":
                run_cmd("pactl set-sink-volume @DEFAULT_SINK@ -5%")
            elif line == "MEDIA_PLAY_PAUSE":
                run_cmd("pactl set-sink-mute @DEFAULT_SINK@ toggle")
            elif line == "MEDIA_NEXT":
                skip_forward_dbus()
                
            elif line == "LAUNCH_OPENAUTO":
                # --- LIVI Switching Logic ---
                # Argument 1: The exact text that appears in the LIVI window title bar.
                # Argument 2: The terminal command to launch the app if it's closed.
                focus_or_launch("autoapp", "/home/pi/LIVI/LIVI7.AppImage") 
                
            elif line == "LAUNCH_TUNERSTUDIO":
                # The address below needs to be changed to the actual location for tunerstudio. The inputs to the function below are the same as for Launch_OpenAuto
                focus_or_launch("TunerStudio", "/home/pi/TunerStudioMS/TunerStudio.sh")
                
            elif line == "TOGGLE_BRIGHTNESS":
                try:
                    new_val = MIN_BRIGHT if brightness_high else MAX_BRIGHT
                    with open(BRIGHTNESS_FILE, "w") as f:
                        f.write(new_val)
                    brightness_high = not brightness_high
                except Exception as e:
                    print(f"Failed to set hardware brightness via sysfs: {e}")
                    
except KeyboardInterrupt:
    print("\nExiting script.")
finally:
    if ser:
        ser.close()
