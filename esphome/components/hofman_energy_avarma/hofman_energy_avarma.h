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

namespace esphome::hofman_energy_avarma {

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
