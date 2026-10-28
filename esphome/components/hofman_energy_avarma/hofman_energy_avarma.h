#pragma once

#include "esphome/core/component.h"
#include "esphome/core/defines.h"

#ifdef USE_HOFMAN_ENERGY_AVARMA_PASSIVE
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/modbus/modbus.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/core/helpers.h"

#include <span>
#endif

#ifdef USE_HOFMAN_ENERGY_AVARMA_ACTIVE
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/modbus_controller/modbus_controller.h"
#include "esphome/components/number/number.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/switch/switch.h"

#include <span>
#endif

namespace esphome::hofman_energy_avarma {

#ifdef USE_HOFMAN_ENERGY_AVARMA_ACTIVE
// Entities polled through modbus_controller. They live here rather than using the modbus_controller
// platforms, whose sources are only compiled when a YAML entry uses them. Every AVARMA register is a
// single holding register.

/// Sets up a SensorItem for one holding register at its own address.
inline void init_holding_item(modbus_controller::SensorItem &item, uint16_t address, uint32_t bitmask,
                              modbus::helpers::SensorValueType value_type) {
  item.register_type = modbus::EntityType::HOLDING;
  item.set_address(address);
  item.set_offset_from_start_address(0);
  item.bitmask = bitmask;
  item.sensor_value_type = value_type;
}

class ActiveSensor : public sensor::Sensor, public modbus_controller::SensorItem {
 public:
  ActiveSensor(uint16_t address, modbus::helpers::SensorValueType value_type) {
    init_holding_item(*this, address, 0xFFFFFFFF, value_type);
  }
  void parse_and_publish(std::span<const uint8_t> data) override {
    this->publish_state(modbus_controller::payload_to_float(data, *this, this->offset));
  }
};

class ActiveBinarySensor : public binary_sensor::BinarySensor, public modbus_controller::SensorItem {
 public:
  ActiveBinarySensor(uint16_t address, uint32_t bitmask) {
    init_holding_item(*this, address, bitmask, modbus::helpers::SensorValueType::BIT);
  }
  void parse_and_publish(std::span<const uint8_t> data) override {
    this->publish_state((modbus::helpers::get_data<uint16_t>(data.data(), this->offset) & this->bitmask) != 0);
  }
};

class ActiveSwitch : public switch_::Switch,
                     public modbus_controller::SensorItem,
                     public modbus_controller::WriterEntity {
 public:
  explicit ActiveSwitch(uint16_t address) {
    init_holding_item(*this, address, 0xFFFFFFFF, modbus::helpers::SensorValueType::BIT);
  }
  void set_parent(modbus_controller::ModbusController *parent) { this->set_controller_(parent); }
  void parse_and_publish(std::span<const uint8_t> data) override {
    this->publish_state((modbus::helpers::get_data<uint16_t>(data.data(), this->offset) & this->bitmask) != 0);
  }

 protected:
  void write_state(bool state) override;
};

class ActiveNumber : public number::Number,
                     public modbus_controller::SensorItem,
                     public modbus_controller::WriterEntity {
 public:
  ActiveNumber(uint16_t address, modbus::helpers::SensorValueType value_type) {
    init_holding_item(*this, address, 0xFFFFFFFF, value_type);
  }
  void set_parent(modbus_controller::ModbusController *parent) { this->set_controller_(parent); }
  /// The register holds the value times this factor.
  void set_write_multiply(float factor) { this->multiply_by_ = factor; }
  void parse_and_publish(std::span<const uint8_t> data) override {
    this->publish_state(modbus_controller::payload_to_float(data, *this, this->offset) / this->multiply_by_);
  }

 protected:
  void control(float value) override;

  float multiply_by_{1.0f};
};
#endif

#ifdef USE_HOFMAN_ENERGY_AVARMA_PASSIVE
/// An entity fed from the holding register values the heat pump sends to its display.
class PassiveItem {
 public:
  explicit PassiveItem(uint16_t address) : address_(address) {}
  uint16_t get_address() const { return this->address_; }
  virtual void publish_register(uint16_t value) = 0;

 protected:
  uint16_t address_;
};

class PassiveSensor : public sensor::Sensor, public PassiveItem {
 public:
  explicit PassiveSensor(uint16_t address) : PassiveItem(address) {}
  void publish_register(uint16_t value) override;

 protected:
  // The display polls far more often than the values change; publish changes only.
  uint16_t last_value_{0};
  bool has_value_{false};
};

class PassiveBinarySensor : public binary_sensor::BinarySensor, public PassiveItem {
 public:
  PassiveBinarySensor(uint16_t address, uint16_t bitmask) : PassiveItem(address), bitmask_(bitmask) {}
  void publish_register(uint16_t value) override { this->publish_state((value & this->bitmask_) != 0); }

 protected:
  uint16_t bitmask_;
};
#endif

class HofmanEnergyAvarmaComponent : public Component {
 public:
  void setup() override;
  void dump_config() override;

#ifdef USE_HOFMAN_ENERGY_AVARMA_PASSIVE
  /// Listen on a server-role hub (which never transmits) for the heat pump's replies to the display.
  void set_passive_source(modbus::ModbusServerHub *hub, uint8_t address) {
    this->hub_ = hub;
    this->address_ = address;
  }
  void add_passive_item(PassiveItem *item) { this->passive_items_.push_back(item); }

 protected:
  void on_bus_response_(uint8_t address, std::span<const uint8_t> request, std::span<const uint8_t> response);
  void publish_registers_(uint16_t start_address, std::span<const uint8_t> values);

  modbus::ModbusServerHub *hub_{nullptr};
  StaticVector<PassiveItem *, HOFMAN_ENERGY_AVARMA_PASSIVE_ITEMS> passive_items_;
  uint8_t address_{1};
#endif
};

}  // namespace esphome::hofman_energy_avarma
