# Hofman Energy AVARMA ESPHome Component

## Example Config (connected to Comm 3 of the Heat-Pump)
```
# your ESP Config here

# include this compoent as an external Component
external_components:
  - source:
      type: git
      url: https://github.com/auenkind/esphome
      ref: dev
    components: [ hofman_energy_avarma ]
    refresh: 1h

# your uart Config
uart:
  tx_pin: GPIO1
  rx_pin: GPIO3
  baud_rate: 9600

# your modbus Config
modbus:
  flow_control_pin: GPIO4
  id: modbus1

# your modbus_controller config
modbus_controller:
  - id: modbus_device
    address: 0x1 ##
    modbus_id: modbus1
    setup_priority: -10
    update_interval: 10s

# active the component
hofman_energy_avarma:
  id: avarma_12kw_heatpump
  modbus_controller_id: modbus_device

# These dummys are needed at the moment due to compile issues
sensor:
  - platform: modbus_controller
    name: dummy
    address: 0x01
    register_type: holding
    internal: true
binary_sensor:
  - platform: modbus_controller
    name: dummy
    address: 0x01
    register_type: holding
    internal: true
switch:
  - platform: modbus_controller
    modbus_controller_id: modbus_device
    name: "dummy"
    register_type: holding
    address: 0x01
    internal: true
    restore_mode: DISABLED
number:
  - platform: modbus_controller
    name: dummy
    address: 0x01
    register_type: holding
    internal: true

```

## Example Config Passive Mode (connected to Comm 4 of the Heat-Pump) in parallel with the Display
```
# your ESP Config here

# include this compoent as an external Component
external_components:
  - source:
      type: git
      url: https://github.com/auenkind/esphome
      ref: dev
    components: [ hofman_energy_avarma, modbus, modbus_controller ]
    refresh: 1h

# your uart Config
uart:
  tx_pin: GPIO1
  rx_pin: GPIO3
  baud_rate: 9600

# your modbus Config
modbus:
  flow_control_pin: GPIO4
  id: modbus1
  disable_crc: "false"
  passive_mode: "true"

# your modbus_controller config
modbus_controller:
  - id: modbus_device
    address: 0x1 ##
    modbus_id: modbus1
    setup_priority: -10
    update_interval: 10s
    passive_mode: "true"

# active the component
hofman_energy_avarma:
  id: avarma_12kw_heatpump
  modbus_controller_id: modbus_device

# These dummys are needed at the moment due to compile issues
sensor:
  - platform: modbus_controller
    name: dummy
    address: 0x01
    register_type: holding
    internal: true
binary_sensor:
  - platform: modbus_controller
    name: dummy
    address: 0x01
    register_type: holding
    internal: true
switch:
  - platform: modbus_controller
    modbus_controller_id: modbus_device
    name: "dummy"
    register_type: holding
    address: 0x01
    internal: true
    restore_mode: DISABLED
number:
  - platform: modbus_controller
    name: dummy
    address: 0x01
    register_type: holding
    internal: true

```
