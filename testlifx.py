import time
from lifxlan import Light

def test_lifx():
    ip = "192.168.1.108"
    mac = "d0:73:d5:6e:69:e5"

    try:
        print(f"Connecting to LIFX bulb at {ip} ({mac})...")
        bulb = Light(mac, ip)
        
        # Get original state
        original_power = bulb.get_power()
        original_color = bulb.get_color()
        print(f"Original power: {original_power} (0 = OFF, 65535 = ON)")
        print(f"Original color: {original_color}")
        
        print("\n--- TEST 1: Simple Power ON & Color ---")
        bulb.set_color([0, 0, 65535, 6500], rapid=True)
        bulb.set_power(65535, rapid=True) # Force it ON
        print("Bulb should now be ON and bright WHITE.")
        time.sleep(2)
        
        bulb.set_power(0, rapid=True)
        print("Bulb should now be OFF.")
        time.sleep(2)

        print("\n--- TEST 2: Pulse Waveform (from OFF state) ---")
        bulb.set_waveform(is_transient=1, color=[0, 0, 65535, 6500], period=100, cycles=3, duty_cycle=0, waveform=4)
        print("Sent pulse waveform. Did it flash while being OFF?")
        time.sleep(2)
        
        print("\n--- TEST 3: Power ON -> Pulse Waveform ---")
        bulb.set_power(65535, rapid=True)
        bulb.set_color([40000, 65535, 30000, 3500], rapid=True) # Dim blueish color
        print("Bulb should be ON with a dim color.")
        time.sleep(2)
        
        print("Sending Pulse Waveform...")
        bulb.set_waveform(is_transient=1, color=[0, 0, 65535, 6500], period=100, cycles=3, duty_cycle=0, waveform=4)
        print("Did it flash?")
        time.sleep(2)

        print("\n--- Restoring original state ---")
        bulb.set_color(original_color, rapid=True)
        bulb.set_power(original_power, rapid=True)
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_lifx()
