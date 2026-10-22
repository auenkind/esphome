import esphome.codegen as cg
from esphome.components.modbus_controller import ModbusController
from esphome.components.modbus_controller import (
    binary_sensor as modbus_binary_sensor,
    number as modbus_number,
    sensor as modbus_sensor,
    switch as modbus_switch,
)
from esphome.components.modbus_controller.const import (
    CONF_BITMASK,
    CONF_MODBUS_CONTROLLER_ID,
    CONF_REGISTER_TYPE,
    CONF_VALUE_TYPE,
)
import esphome.config_validation as cv
from esphome.const import (
    CONF_ACCURACY_DECIMALS,
    CONF_ADDRESS,
    CONF_DEVICE_CLASS,
    CONF_DISABLED_BY_DEFAULT,
    CONF_ENTITY_CATEGORY,
    CONF_FILTERS,
    CONF_ID,
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_MULTIPLY,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_STEP,
    CONF_UNIT_OF_MEASUREMENT,
)
from esphome.core import CORE

from .registers.avarma_registers import (
    AVARMA_BINARY_REGISTERS,
    AVARMA_NUMBER_REGISTERS,
    AVARMA_SENSOR_REGISTERS,
    AVARMA_SWITCH_REGISTERS,
)

DEPENDENCIES = ["modbus_controller"]
AUTO_LOAD = ["modbus_controller", "sensor", "binary_sensor", "switch", "number"]
MULTI_CONF = False

MODBUS_CONTROLLER = "modbus_controller"

avarma_component_ns = cg.esphome_ns.namespace("hofman_energy_avarma")
HofmanEnergyAvarmaComponent = avarma_component_ns.class_(
    "HofmanEnergyAvarmaComponent", cg.Component
)


def _common_defaults(register, **extra):
    defaults = {
        CONF_NAME: register.name,
        CONF_ADDRESS: register.address,
        CONF_REGISTER_TYPE: "holding",
        **extra,
    }
    if register.entity_category:
        defaults[CONF_ENTITY_CATEGORY] = register.entity_category
    if register.deactivated:
        defaults[CONF_DISABLED_BY_DEFAULT] = True
    return defaults


def _entities():
    """Yield (config key, entity domain, modbus_controller platform, defaults) per register entity."""
    for register in AVARMA_SENSOR_REGISTERS:
        defaults = _common_defaults(
            register,
            **{
                CONF_VALUE_TYPE: register.value_type,
                CONF_UNIT_OF_MEASUREMENT: register.unit_of_measurement,
                CONF_ACCURACY_DECIMALS: register.accuracy_decimals,
                CONF_FILTERS: [{CONF_MULTIPLY: register.register_factor}],
            },
        )
        if register.device_class:
            defaults[CONF_DEVICE_CLASS] = register.device_class
        yield register.parameter_id, "sensor", modbus_sensor, defaults

    for register in AVARMA_BINARY_REGISTERS:
        for flag in register.flags:
            key = f"{register.parameter_id.replace('-', '_')}_{flag.bitmask}"
            defaults = _common_defaults(register, **{CONF_BITMASK: flag.bitmask})
            defaults[CONF_NAME] = f"{register.name} {flag.name}"
            yield key, "binary_sensor", modbus_binary_sensor, defaults

    for register in AVARMA_SWITCH_REGISTERS:
        defaults = _common_defaults(register)
        if register.device_class:
            defaults[CONF_DEVICE_CLASS] = register.device_class
        yield register.parameter_id, "switch", modbus_switch, defaults

    for register in AVARMA_NUMBER_REGISTERS:
        defaults = _common_defaults(
            register,
            **{
                CONF_VALUE_TYPE: register.value_type,
                CONF_MIN_VALUE: register.min,
                CONF_MAX_VALUE: register.max,
                CONF_STEP: register.step,
                CONF_MULTIPLY: register.register_factor,
            },
        )
        yield register.parameter_id, "number", modbus_number, defaults


ENTITIES = list(_entities())


def _entity_overrides(value):
    """Per-register options from the YAML, e.g. `C00: {name: ..., internal: true}`."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise cv.Invalid("expected a dictionary of entity options")
    return value


def _validate_entities(config):
    """Validate every register entity with the matching modbus_controller platform schema."""
    errors = []
    for key, _, platform, defaults in ENTITIES:
        entity = {
            **defaults,
            CONF_MODBUS_CONTROLLER_ID: config[CONF_MODBUS_CONTROLLER_ID],
            **config[key],
        }
        try:
            config[key] = platform.CONFIG_SCHEMA(entity)
        except cv.Invalid as err:
            err.prepend([key])
            errors.append(err)
    if errors:
        raise cv.MultipleInvalid(errors)
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(HofmanEnergyAvarmaComponent),
            cv.Required(CONF_MODBUS_CONTROLLER_ID): cv.use_id(ModbusController),
            **{
                cv.Optional(key, default={}): _entity_overrides
                for key, _, _, _ in ENTITIES
            },
        }
    ).extend(cv.COMPONENT_SCHEMA),
    _validate_entities,
)


def _final_validate(config):
    for key, _, platform, _ in ENTITIES:
        platform_final_validate = getattr(platform, "FINAL_VALIDATE_SCHEMA", None)
        if platform_final_validate is not None:
            with cv.prepend_path(key):
                platform_final_validate(config[key])
    return config


FINAL_VALIDATE_SCHEMA = _final_validate


def _ensure_platform_sources(domain):
    """ESPHome only copies a platform's C++ sources when the platform appears in the config.

    The register entities are generated here instead of under `sensor:` etc., so register the
    modbus_controller platform for each entity domain unless the user config already has it.
    """
    platforms = CORE.config.setdefault(domain, [])
    if not any(conf.get(CONF_PLATFORM) == MODBUS_CONTROLLER for conf in platforms):
        platforms.append({CONF_PLATFORM: MODBUS_CONTROLLER})


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    for key, domain, platform, _ in ENTITIES:
        _ensure_platform_sources(domain)
        await platform.to_code(config[key])
