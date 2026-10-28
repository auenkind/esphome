import esphome.codegen as cg
from esphome.components import binary_sensor, modbus, number, sensor, switch
from esphome.components.modbus_controller import ModbusController, SensorItem
from esphome.components.modbus_controller.const import CONF_MODBUS_CONTROLLER_ID
import esphome.config_validation as cv
from esphome.const import (
    CONF_ADDRESS,
    CONF_DISABLED_BY_DEFAULT,
    CONF_ID,
    CONF_MULTIPLY,
    CONF_NAME,
)
from esphome.types import ConfigType

from .registers.avarma_registers import (
    AVARMA_BINARY_REGISTERS,
    AVARMA_NUMBER_REGISTERS,
    AVARMA_SENSOR_REGISTERS,
    AVARMA_SWITCH_REGISTERS,
)

DEPENDENCIES = ["modbus"]
DOMAIN = "hofman_energy_avarma"
# Without these the entity platforms' base classes are not compiled.
AUTO_LOAD = ["binary_sensor", "number", "sensor", "switch"]
MULTI_CONF = False

avarma_component_ns = cg.esphome_ns.namespace("hofman_energy_avarma")
HofmanEnergyAvarmaComponent = avarma_component_ns.class_(
    "HofmanEnergyAvarmaComponent", cg.Component
)
ActiveSensor = avarma_component_ns.class_("ActiveSensor", sensor.Sensor, SensorItem)
ActiveBinarySensor = avarma_component_ns.class_(
    "ActiveBinarySensor", binary_sensor.BinarySensor, SensorItem
)
ActiveSwitch = avarma_component_ns.class_("ActiveSwitch", switch.Switch, SensorItem)
ActiveNumber = avarma_component_ns.class_("ActiveNumber", number.Number, SensorItem)
PassiveSensor = avarma_component_ns.class_("PassiveSensor", sensor.Sensor)
PassiveBinarySensor = avarma_component_ns.class_(
    "PassiveBinarySensor", binary_sensor.BinarySensor
)

# Shares the hub's on_response slot count with modbus_monitor (the define is keyed by name).
_request_on_response_slot = cg.slot_counter("MODBUS_ON_RESPONSE_COUNT")


def _flag_key(register, flag) -> str:
    return f"{register.parameter_id.replace('-', '_')}_{flag.bitmask}"


def _entity_defaults(register, name: str) -> ConfigType:
    defaults = {CONF_NAME: name}
    if register.deactivated:
        defaults[CONF_DISABLED_BY_DEFAULT] = True
    return defaults


def _sensor_schemas(sensor_class) -> dict:
    return {
        cv.Optional(
            register.parameter_id, default=_entity_defaults(register, register.name)
        ): sensor.sensor_schema(
            sensor_class,
            unit_of_measurement=register.unit_of_measurement,
            accuracy_decimals=register.accuracy_decimals,
            entity_category=register.entity_category,
            device_class=register.device_class,
            filters=[{CONF_MULTIPLY: register.register_factor}],
        )
        for register in AVARMA_SENSOR_REGISTERS
    }


def _flag_schemas(binary_sensor_class) -> dict:
    return {
        cv.Optional(
            _flag_key(register, flag),
            default=_entity_defaults(register, f"{register.name} {flag.name}"),
        ): binary_sensor.binary_sensor_schema(
            binary_sensor_class,
            entity_category=register.entity_category,
        )
        for register in AVARMA_BINARY_REGISTERS
        for flag in register.flags
    }


ACTIVE_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(HofmanEnergyAvarmaComponent),
        cv.Required(CONF_MODBUS_CONTROLLER_ID): cv.use_id(ModbusController),
        **_sensor_schemas(ActiveSensor),
        **_flag_schemas(ActiveBinarySensor),
        **{
            cv.Optional(
                register.parameter_id,
                default=_entity_defaults(register, register.name),
            ): switch.switch_schema(
                ActiveSwitch,
                entity_category=register.entity_category,
                device_class=register.device_class,
                default_restore_mode="DISABLED",
            )
            for register in AVARMA_SWITCH_REGISTERS
        },
        **{
            cv.Optional(
                register.parameter_id,
                default=_entity_defaults(register, register.name),
            ): number.number_schema(ActiveNumber)
            for register in AVARMA_NUMBER_REGISTERS
        },
    }
).extend(cv.COMPONENT_SCHEMA)

# Passive mode only listens, so the writable registers become read-only entities.
PASSIVE_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(HofmanEnergyAvarmaComponent),
        cv.Required(modbus.CONF_MODBUS_ID): cv.use_id(modbus.ModbusServer),
        cv.Optional(CONF_ADDRESS, default=0x01): cv.hex_uint8_t,
        **_sensor_schemas(PassiveSensor),
        **_flag_schemas(PassiveBinarySensor),
        **{
            cv.Optional(
                register.parameter_id,
                default=_entity_defaults(register, register.name),
            ): binary_sensor.binary_sensor_schema(
                PassiveBinarySensor,
                entity_category=register.entity_category,
            )
            for register in AVARMA_SWITCH_REGISTERS
        },
        **{
            cv.Optional(
                register.parameter_id,
                default=_entity_defaults(register, register.name),
            ): sensor.sensor_schema(
                PassiveSensor,
                accuracy_decimals=0 if register.step >= 1 else 1,
                entity_category=register.entity_category,
                # ModbusNumber divides the raw value by its write multiplier when reading.
                filters=[{CONF_MULTIPLY: 1 / register.register_factor}],
            )
            for register in AVARMA_NUMBER_REGISTERS
        },
    }
).extend(cv.COMPONENT_SCHEMA)


def _validate_mode(config: ConfigType) -> ConfigType:
    if modbus.CONF_MODBUS_ID in config:
        return PASSIVE_SCHEMA(config)
    return ACTIVE_SCHEMA(config)


CONFIG_SCHEMA = cv.All(
    cv.has_exactly_one_key(CONF_MODBUS_CONTROLLER_ID, modbus.CONF_MODBUS_ID),
    _validate_mode,
)


async def to_code(config: ConfigType) -> None:
    component = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(component, config)

    if modbus.CONF_MODBUS_ID in config:
        await _passive_to_code(component, config)
    else:
        await _active_to_code(config)


async def _passive_to_code(component: cg.MockObj, config: ConfigType) -> None:
    hub = await cg.get_variable(config[modbus.CONF_MODBUS_ID])
    cg.add(component.set_passive_source(hub, config[CONF_ADDRESS]))
    _request_on_response_slot(str(hub))
    cg.add_define("USE_HOFMAN_ENERGY_AVARMA_PASSIVE")

    item_count = 0

    async def add_item(var: cg.MockObj) -> None:
        nonlocal item_count
        cg.add(component.add_passive_item(var))
        item_count += 1

    for register in AVARMA_SENSOR_REGISTERS + AVARMA_NUMBER_REGISTERS:
        conf = config[register.parameter_id]
        var = cg.new_Pvariable(conf[CONF_ID], register.address)
        await sensor.register_sensor(var, conf)
        await add_item(var)

    for register in AVARMA_BINARY_REGISTERS:
        for flag in register.flags:
            conf = config[_flag_key(register, flag)]
            var = cg.new_Pvariable(conf[CONF_ID], register.address, flag.bitmask)
            await binary_sensor.register_binary_sensor(var, conf)
            await add_item(var)

    for register in AVARMA_SWITCH_REGISTERS:
        conf = config[register.parameter_id]
        var = cg.new_Pvariable(conf[CONF_ID], register.address, 0xFFFF)
        await binary_sensor.register_binary_sensor(var, conf)
        await add_item(var)

    cg.add_define("HOFMAN_ENERGY_AVARMA_PASSIVE_ITEMS", item_count)


async def _active_to_code(config: ConfigType) -> None:
    controller = await cg.get_variable(config[CONF_MODBUS_CONTROLLER_ID])
    cg.add_define("USE_HOFMAN_ENERGY_AVARMA_ACTIVE")

    for register in AVARMA_SENSOR_REGISTERS:
        conf = config[register.parameter_id]
        var = cg.new_Pvariable(conf[CONF_ID], register.address, register.value_type)
        await sensor.register_sensor(var, conf)
        cg.add(controller.add_sensor_item(var))

    for register in AVARMA_BINARY_REGISTERS:
        for flag in register.flags:
            conf = config[_flag_key(register, flag)]
            var = cg.new_Pvariable(conf[CONF_ID], register.address, flag.bitmask)
            await binary_sensor.register_binary_sensor(var, conf)
            cg.add(controller.add_sensor_item(var))

    for register in AVARMA_SWITCH_REGISTERS:
        conf = config[register.parameter_id]
        var = cg.new_Pvariable(conf[CONF_ID], register.address)
        await switch.register_switch(var, conf)
        cg.add(var.set_parent(controller))
        cg.add(controller.add_sensor_item(var))

    for register in AVARMA_NUMBER_REGISTERS:
        conf = config[register.parameter_id]
        var = cg.new_Pvariable(conf[CONF_ID], register.address, register.value_type)
        await number.register_number(
            var,
            conf,
            min_value=register.min,
            max_value=register.max,
            step=register.step,
        )
        cg.add(var.set_parent(controller))
        cg.add(controller.add_sensor_item(var))
        cg.add(var.set_write_multiply(register.register_factor))
