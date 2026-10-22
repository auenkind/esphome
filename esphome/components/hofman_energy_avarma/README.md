# Hofman Energy AVARMA ESPHome Component

Reads and writes the registers of a Hofman Energy AVARMA heat pump via Modbus.
All registers listed in [AVARMA_REGISTERS.md](AVARMA_REGISTERS.md) are created as
sensors, binary sensors, switches and numbers on top of ESPHome's built-in
`modbus_controller` component (tested with ESPHome 2026.9).

## Example Config (connected to Comm 3 of the Heat-Pump)
```
# your ESP Config here

# include this component as an external Component
external_components:
  - source:
      type: git
      url: https://github.com/jfmennedy/esphome
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
    address: 0x1
    modbus_id: modbus1
    setup_priority: -10
    update_interval: 10s

# activate the component
hofman_energy_avarma:
  id: avarma_12kw_heatpump
  modbus_controller_id: modbus_device
```

The dummy `sensor`/`binary_sensor`/`switch`/`number` entries older versions of this
README required are no longer needed (keeping them does no harm).

## Customizing single registers

Every register entity accepts the usual options of the matching
`modbus_controller` platform, keyed by its parameter id (binary sensors use
`<parameter id>_<bitmask>`, with `-` replaced by `_`):

```
hofman_energy_avarma:
  id: avarma_12kw_heatpump
  modbus_controller_id: modbus_device
  C00:
    name: "Coil temperature"
  C04:
    disabled_by_default: false
  C31_C35_1:
    internal: true
```

## Passive Mode (Comm 4, in parallel with the Display)

Passive mode relied on patched `modbus` / `modbus_controller` components in this
fork. ESPHome reworked Modbus in 2026 and these patches are not compatible with
current ESPHome versions, so passive mode is currently not supported.
