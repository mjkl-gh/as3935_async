"""
    (C) 2019 Eloi Codina Torras

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import asyncpio
import time
import asyncio


INT_NH = 0b0001
INT_D = 0b0100
INT_L = 0b1000


class AS3935:
    def __init__(self, irq, bus=1, address=0x03):
        """
        Configure the main parameters of AS3935.

        :param irq: (int) GPIO pin number the IRQ is connected at (BCM number)
        :param bus: (int, optional) the bus the AS3935 is connected at. Default = 1
        :param address: (int, optional) the address of the AS3935. Default = 0x03
        """
        self.address = address
        self.bus = bus
        self.irq = irq
        self.pi = asyncpio.pi()
        if self.sl.s is None:
            # Maybe there is a better test to check for active connection?
            raise ValueError("The pi value should contain an already connected pi")
        self.i2c_device = await self.pi.i2c_open(bus, address)

    # ------ CROSS FUNCTIONS ------ #

    async def read_byte(self, address):
        """
        Returns the value of the byte stored at address.

        :param address: (int) the address to read from
        :return: (int) the value of the address
        """
        return await self.pi.i2c_read_byte_data(self.i2c_device, address)

    async def write_byte(self, address, value):
        """
        Writes value at address. Raises ValueError if the value is not correct.

        :param address: (int) the address to write to
        :param value: (int) the byte value (between 0x00 and 0xFF)
        """
        if not 0 <= value <= 255:
            raise ValueError("The value should be between 0x00 and 0xFF")
        await self.pi.i2c_write_byte_data(self.i2c_device, address, value)


    async def full_calibration(self, tuning_cap):
        """
        Performs a full calibration: antenna and RCO

        :param tuning_cap: int: tuning number for the antenna. Can be calculated with self.calculate_tuning_cap()
        """
        await self.set_tune_antenna(tuning_cap)
        await self.calibrate_trco()

    # ------ 8.2- OPERATING MODES ------ #

    async def power_down_mode(self):
        """
        Sets the AS3935 on power down mode (PWD)
        """
        original_byte = await self.read_byte(0x00)
        await self.write_byte(0x00, original_byte & 0b11111111)

    async def listening_mode(self):
        """
        Sets the AS3935 on listening mode (PWD)
        """
        original_byte = await self.read_byte(0x00)
        await self.write_byte(0x00, original_byte & 0b11111110)

    # ------------- 8.5- I2C ------------ #
    # ------ 8.5.3- DIRECT COMMAND ------ #

    async def set_default_values(self):
        """
        Sends a direct command to 0x3C to reset to default values.
        """
        await self.write_byte(0x3C, 0x96)

    async def calibrate_rco(self):
        """
        Sends a direct command to 0x3D to calibrate the RCO (CALIB_RCO)
        """
        await self.write_byte(0x3D, 0x96)

    # ------------- 8.7- AFE AND WATCHDOG ------------ #

    async def get_indoors(self):
        """
        Checks whether the device is configured to be run indoors. (AFE_GB)

        :return: (bool) whether the device is configured to be run indoors
        """
        return await self.read_byte(0x00) & 0b100000 == 0b100000

    async def set_indoors(self, indoors):
        """
        Configures the device to be run indoors or outdoors. (AFE_GB)

        :param indoors: (bool) configure the AS3935 to be run indoors
        """
        current_value = await self.read_byte(0x00)
        if indoors:
            write_value = (current_value & 0b11000001) | 0b100100
        else:
            write_value = (current_value & 0b11000001) | 0b11100
        await self.write_byte(0x00, write_value)

    async def get_watchdog_threshold(self):
        """
        Returns the watchdog threshold (WDTH)

        :return: (int) the current watchdog threshold
        """
        return await self.read_byte(0x01) & 0b00001111

    async def set_watchdog_threshold(self, value=0b0001):
        """
        Sets the watchdog threshold to value (WDTH). If called without parameters,
        it sets it to the default configuration.
        Can raise a ValueError if not 0 <= value <= 0b1111

        :param value: (int, optional) The value to be set. From 0b0000 to 0b1111. Default=0b0001
        """
        if not 0 <= value <= 0b1111:
            raise ValueError("Value should be from 0b0010 to 0b1111")
        original_byte = await self.read_byte(0x01)
        await self.write_byte(0x01, original_byte & 0x11110000) | value)

    # ------------- 8.8- NOISE FLOOR GENERATOR ------------ #

    async def get_noise_floor(self):
        """
        Checks the current noise floor threshold (NF_LEV).

        :return: (int) the current noise floor threshold
        """
        return (await self.read_byte(0x01) & 0b1110000) >> 4

    async def set_noise_floor(self, noise_floor=0b010):
        """
        Sets a new noise floor threshold (NF_LEV). If called without parameters, it sets it to the default configuration.
        Can raise a ValueError if not 0 <= noise_floor <= 0b111

        :param noise_floor: (int, optional) The value to be set. From 0b000 to 0b111
        """
        if not 0 <= noise_floor <= 0b1111:
            raise ValueError("noise_floor should be from 0b000 to 0b111")
            original_byte = self.read_byte(0x01)
        await self.write_byte(0x01, (self.read_byte(0x01) & 0b10001111) + ((noise_floor & 0x07) << 4))

    async def lower_noise_floor(self, min_noise=0b000):
        """
        Lowers the noise floor threshold by one step (subtracts 1 to the current NF_LEV)
        if it is currently higher than min_noise.
        Can raise a ValueError if not 0 <= min_noise <= 0b111

        :param min_noise: (int, optional) the minimum NF_LEV the device should be set at. Default = 0b000
        :return: (int) the new noise floor threshold
        """
        if not 0 <= min_noise <= 0b1111:
            raise ValueError("min_noise should be from 0b000 to 0b111")
        floor = self.get_noise_floor()
        if floor > min_noise:
            floor = floor - 1
            await self.set_noise_floor(floor)
        return floor

    async def raise_noise_floor(self, max_noise=0b111):
        """
        Raises the noise floor threshold by one step (adds 1 to the current NF_LEV)
        if it is currently lower than max_noise
        Can raise a ValueError if not 0 <= max_noise <= 0b111

        :param max_noise: (int, optional) the maximum  NF_LEV the device should be set at. Default 0b111
        :return: (int) the new noise floor threshold
        """
        if not 0 <= max_noise <= 0b1111:
            raise ValueError("max_noise should be from 0b000 to 0b111")
        floor = self.get_noise_floor()
        if floor < max_noise:
            floor = floor + 1
            await self.set_noise_floor(floor)
        return floor

    # ------------- 8.9- LIGHTNING ALGORITHM ------------ #
    # ------------- 8.9.1- SIGNAL VALIDATION ------------ #

    async def get_spike_rejection(self):
        """
        Checks the current spike rejection settings (SREJ)

        :return: (int) the current spike rejection setting (SREJ)
        """
        return await self.read_byte(0x02) & 0b00001111

    async def set_spike_rejection(self, value=0b0010):
        """
        Sets a new setting for the spike rejection algorithm (SREJ). If the function is called without any parameter,
        it sets it to the default value of 0b0010
        Can raise a ValueError if not 0 <= value <= 0b1111

        :param value: (int, optional) the value to set SREJ. Default = 0b0010
        """
        if not 0 <= value <= 0b1111:
            raise ValueError("Value should be from 0b0000 to 0b1111")
        clean_byte = self.read_byte(0x02) & 0b11110000
        await self.write_byte(0x02, clean_byte | value)

    # ------------- 8.9.2- ENERGY CALCULATION ------------ #

    async def get_energy(self):
        """
        Checks the last lightning strike's energy calculation. It does not have any physical meaning.
        (Energy of the Single Lightning *SBYTE)

        :return: (int) last strike's energy
        """
        return ((await self.read_byte(0x06) & 0x1F) << 16) | (await self.read_byte(0x05) << 8) | await self.read_byte(0x04)

    # ------------- 8.9.3- DISTANCE ESTIMATION ------------ #

    async def get_distance(self):
        """
        Checks the estimation of the last lightning strike's distance in km (DISTANCE).

        :return: (int/None) last strike's distance in km. None if out of range, 0 if overhead
        """
        dist = await self.read_byte(0x07) & 0b00111111
        if dist == 0b111111:
            return None
        elif dist == 0b000001:
            return 0
        return dist

    # ------------- 8.9.4- INTERRUPTION MANAGEMENT ------------ #

    async def get_interrupt(self):
        """
        Checks the reason of the interruption (INT). To know what it is, use the constants:
            INT_NH: noise level too high
            INT_D: disturber detected
            INT_L: lightning strike detected

        It sleeps for 2 ms before retrieving the value, as specified at the datasheet.

        :return: (int) the interruption reason
        """
        asyncio.sleep(0.002)
        return await self.read_byte(0x03) & 0x0F

    async def set_mask_disturber(self, mask_dist):
        """
        Sets whether disturbers should be masked (MASK_DIST).

        :param mask_dist: (bool) whether disturbers should be masked
        """
        if mask_dist:
            await self.write_byte(0x03, self.read_byte(0x03) | 0b100000)
        else:
            await self.write_byte(0x03, self.read_byte(0x03) & 0b11011111)

    async def get_mask_disturber(self):
        """
        Checks whether disturbers are currently masked (MASK_DIST).

        :return: (bool) whether disturbers are currently masked
        """
        return await self.read_byte(0x03) & 0b100000 == 0b100000

    async def get_min_strikes(self):
        """
        Checks the current configuration of how many strikes AS3935 has to detect in 15 minutes to issue an interrupt
        (MIN_NUM_LIG).
        In case of an error, it raises a LookupError

        :return: (int) number of strikes. Possible values: 1, 5, 9, 16
        """
        bin_min = await self.read_byte(0x02) & 0b00110000
        if bin_min == 0b00000000:
            return 1
        elif bin_min == 0b00010000:
            return 5
        elif bin_min == 0b00100000:
            return 9
        elif bin_min == 0b00110000:
            return 16
        raise LookupError("Could not get MIN_NUM_LIGH")

    async def set_min_strikes(self, min_strikes):
        """
        Sets the minumum number of lightning strikes the AS3935 has to detect in 15 minutes to issue an interrupt
        (MIN_NUM_LIG).
        Can raise a ValueError if min_strikes is not an accepted value.

        :param min_strikes: (int) min number of strikes to issue an interrupt. Possible values: 1, 5, 9, 16
        """
        if min_strikes == 1:
            bin_min = 0b00000000
        elif min_strikes == 5:
            bin_min = 0b00010000
        elif min_strikes == 9:
            bin_min = 0b00100000
        elif min_strikes == 16:
            bin_min = 0b00110000
        else:
            raise ValueError("Allowed values for min_strikes: 1, 5, 9, 16.")
        await self.write(0x02, (self.read_byte(0x02) & 0b11001111) | bin_min)

    async def clear_lightning_stats(self):
        """
        Clears the statistics built up by the lightning distance estimation algorithm (CL_STAT)
        """
        original_byte = await self.read_byte(0x02)
        await self.write_byte(0x02, original_byte & 0b10111111)
        asyncio.sleep(0.001)
        await self.write_byte(0x02, original_byte)

    # ------------- 8.10- ANTENNA TUNNING ------------ #

    async def get_display_lco(self):
        """
        Checks whether the antenna resonance frequency is currently displayed on the IRQ pin (DISP_LCO)

        :return: (bool) whether the antenna resonance frequency is currently displayed
        """
        return await self.read_byte(0x08) & 0b10000000 == 0b100000000

    async def set_display_lco(self, display_lco):
        """
        Sets whether the antenna resonance frequency should be displayed on the IRQ pin(DISP_LCO).

        :param display_lco: (bool) whether the antenna resonance frequency should be displayed
        """
        current_value = self.read_byte(0x08)
        if display_lco:
            await self.write_byte(0x08, (current_value | 0x80))
        else:
            await self.write_byte(0x08, (current_value & 0x7F))

    async def set_tune_antenna(self, tuning_cap):
        """
        Sets the antenna calibration. It adds or removes internal capacitors according to tuning_cap (TUN_CAP).
        If tuning_cap is unknown, this could be calculated by calculate_tuning_cap(self, frequency_divisor, tries_frequency)
        Can raise a ValueError if not 0 <= tuning_cap <= 15

        :param tuning_cap: (int) the number to calibrate the antenna
        """
        if not 0 <= tuning_cap <= 15:
            raise ValueError("The value of the tuning_cap should be less than 15.")
        await self.write_byte(0x08, (self.read_byte(0x08) & 0b11110000) | tuning_cap)

    async def calculate_tuning_cap(self, frequency_divisor=16, tries_frequency=3, seconds_try=4):
        """
        Measures the frequency of the LC resonator for every possible tuning_cap and returns the best value.
        If possible, use the default values for frequency_divisor, tries_frequency and seconds_try.
        This function takes a long time. It should take about tries_frequency*seconds_try*16 seconds given that
        there are 16 tuning possibilities.

        The ideal frequency is of 500 kHz

        Can raise ValueError if frequency_divisor is not a valid number.

        :param frequency_divisor: (int) the divisor the AS3935 uses to divide the frequency before displaying it on the IRQ
        :param tries_frequency: (int) number of times the current frequency is calculated during *seconds_try* seconds
                                to calculate an average
        :param seconds_try: (float) seconds during which pulses on IRQ will be counted to calculate the internal frequency
        :return: (int) a tuning number between 0 and 15
        """
        print("Please allow a long time for this function to stop. It should take 16*seconds_try*tries_frequency seconds")
        await self.set_frequency_division_ratio(frequency_divisor)
        frequency_target = 500000 / frequency_divisor
        best_tuner = 0
        best_diff = 500000000
        for current_tuner in range(0b0, 0b10000):
            await self.set_tune_antenna(current_tuner)
            freqs = []
            for i in range(tries_frequency):
                freqs.append(self.calculate_resonance_frequency(seconds_try))
            freq = sum(freqs)/tries_frequency
            print("For tuning {tun}: average frequency of {freq} Hz".format(tun=hex(current_tuner),
                                                                            freq=freq*frequency_divisor))
            diff = abs(frequency_target - freq)
            if diff < best_diff:
                best_tuner = current_tuner
                best_diff = diff
        self.set_tune_antenna(best_tuner)
        return best_tuner

    async def calculate_resonance_frequency(self, seconds):
        """
        Sets the AS3935 to display the antenna resonance frequency on the IRQ during *seconds* and counts the number
        of pulses in this time to calculate the internal frequency.
        To get the real frequency multiply this value by the frequency divisor ratio.

        :param seconds: (int) number of seconds while it should count spikes
        :return: (int) internal frequency
        """
        cb = self.pi.callback(self.irq)

        # Count pulses
        await self.set_display_lco(True)
        start = time.time()
        asyncio.sleep(seconds)
        await self.set_display_lco(False)
        end = time.time()

        # Calculate the frequency. Not with seconds, because it is not exact
        freq = cb.tally() / (end-start)
        cb.cancel()
        return freq

    async def get_frequency_division_ratio(self):
        """
        Gets the current frequency division ratio. Number by which the real antenna resonance frequency is divided to
        display on the IRQ pin (LCO_FDIV).
        Can raise a LookupError if there is an error checkig the configuration.

        :return: (int) frequency division ratio. Possible numbers: 16, 32, 64, 128
        """
        lco_fdiv = await self.read_byte(0x03) & 0b11000000
        if lco_fdiv == 0:
            return 16
        elif lco_fdiv == 64:
            return 32
        elif lco_fdiv == 128:
            return 64
        elif lco_fdiv == 192:
            return 128
        raise LookupError("Could not get the LCO_FDIV value.")

    async def set_frequency_division_ratio(self, divisor=16):
        """
        Sets a new frequency division ration by which the antenna resonance frequency is divided to display on the IRQ pin
        (LCO_FDIV).If called with no parameter, it defaults to 16.
        Can raise a ValueError if *divisor* is not an accepted number.

        :param divisor: (int, optional) frequency divisor ratio. Accepted values = (16, 32, 64, 128). Default = 16
        """
        values = {16: 0b0, 32: 0b01000000, 64: 0b10000000, 128: 0b11000000}
        if divisor not in values:
            raise ValueError("Accepted values: 16, 32, 64, 128")
        new_lco_fdiv = (self.read_byte(0x03) & 0b00111111) | values[divisor]
        await self.write_byte(0x03, new_lco_fdiv)

    # ------------- 8.11- CLOCK GENERATION ------------ #

    async def get_display_srco(self):
        """
        Checks whether the SRCO frequency is being displayed on the IRQ pin.

        :return: (bool) whether the SRCO frequency is currently displayed
        """
        return await self.read_byte(0x08) & 0b01000000 == 0b01000000

    async def set_display_srco(self, display_srco):
        """
        Sets whether the SRCO frequency should be displayed on the IRQ pin.

        :param display_srco: (bool) whether the SRCO frequency should be displayed
        """
        current_value = self.read_byte(0x08)
        if display_srco:
            await self.write_byte(0x08, (current_value | 0b1000000))
        else:
            await self.write_byte(0x08, (current_value & 0b10111111))

    async def get_display_trco(self):
        """
        Checks' whether the TRCO frequency is being displayed on the IRQ pin.

        :return: (bool) whether the TRCO frequency is currently displayed
        """
        return await self.read_byte(0x08) & 0b00100000 == 0b00100000

    async def set_display_trco(self, display_trco):
        """
        Sets whether the TRCO frequency should be displayed on the IRQ pin.

        :param display_srco: (bool) whether the TRCO frequency should be displayed
        """
        current_value = await self.read_byte(0x08)
        if display_trco:
            await self.write_byte(0x08, (current_value | 0b100000))
        else:
            await self.write_byte(0x08, (current_value & 0b11011111))

    async def calibrate_trco(self):
        """
        Calibrates the TRCO by sending the direct command CALIB_RCO and toggling the DIS_TRCO bit (low-high-low)
        """
        listen_task = asyncio.create_task(self.listening_mode())
        calibrate_task = asyncio.create_task(self.calibrate_rco())
        enable_trco_task = asyncio.create_task(self.set_display_trco(True))
        asyncio.wait({listen_task, calibrate_task, enable_trco_task})
        await self.set_display_trco(False)
