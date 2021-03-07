
class Sensors:
    def __init__ (self, expanders):
        self.available_expanders = expanders
        self.sensors = (len(expanders) * 8) * [False]

    def sensor_on (self, sensor):
        ""
        i = self.sensor_index (sensor)
        self.sensors[i] = True

    def sensor_off (self, sensor):
        ""
        i = self.sensor_index (sensor)
        self.sensors[i] = False

    def sensor_index (self, sensor):
        if sensor <= 16:
            raise ValueError
        sensor -= 1 # to be zero-indexed
        expander = int((sensor - 16) / 8) + 1
        expander_i = self.available_expanders.index(expander)
        return (expander_i * 8) + ((sensor - 16) % 8)

    def get_sensors_from_expander (self, expander):
        expander_i = self.available_expanders.index(expander)
        return self.sensors[expander_i * 8:(expander_i *8)+8]

    def expanders (self):
        return self.available_expanders
