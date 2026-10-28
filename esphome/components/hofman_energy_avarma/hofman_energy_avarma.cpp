#include "hofman_energy_avarma.h"
#include "esphome/core/log.h"

#include <cmath>

namespace esphome::hofman_energy_avarma {

ESPHOME_LOG_TAG(TAG, "hofman_energy_avarma");

#ifdef USE_HOFMAN_ENERGY_AVARMA_ACTIVE
void ActiveSwitch::write_state(bool state) {
  // A new write supersedes this entity's own not-yet-sent writes.
  this->clear_tx_queue_for_device();
  if (!this->write_single_register(this->write_address(), state ? 0xFFFF : 0)) {
    ESP_LOGW(TAG, "Write to 0x%04X was refused by the hub", this->write_address());
    return;
  }
  this->publish_state(state);
}

void ActiveNumber::control(float value) {
  this->clear_tx_queue_for_device();
  const auto raw = static_cast<int16_t>(lroundf(value * this->multiply_by_));
  if (!this->write_single_register(this->write_address(), static_cast<uint16_t>(raw))) {
    ESP_LOGW(TAG, "Write to 0x%04X was refused by the hub", this->write_address());
    return;
  }
  this->publish_state(value);
}
#endif

#ifdef USE_HOFMAN_ENERGY_AVARMA_PASSIVE
void PassiveSensor::publish_register(uint16_t value) {
  if (this->has_value_ && this->last_value_ == value)
    return;
  this->last_value_ = value;
  this->has_value_ = true;
  this->publish_state(static_cast<int16_t>(value));
}
#endif

void HofmanEnergyAvarmaComponent::setup() {
#ifdef USE_HOFMAN_ENERGY_AVARMA_PASSIVE
  this->hub_->add_on_response_callback(
      [this](uint8_t address, std::span<const uint8_t> request, std::span<const uint8_t> response) {
        this->on_bus_response_(address, request, response);
      });
#endif
}

void HofmanEnergyAvarmaComponent::dump_config() {
#ifdef USE_HOFMAN_ENERGY_AVARMA_PASSIVE
  ESP_LOGCONFIG(TAG,
                "Hofman Energy AVARMA:\n"
                "  Mode: passive (read only)\n"
                "  Address: 0x%02X\n"
                "  Entities: %zu",
                this->address_, this->passive_items_.size());
#else
  ESP_LOGCONFIG(TAG, "Hofman Energy AVARMA:\n"
                     "  Mode: active (modbus_controller)");
#endif
}

#ifdef USE_HOFMAN_ENERGY_AVARMA_PASSIVE
void HofmanEnergyAvarmaComponent::on_bus_response_(uint8_t address, std::span<const uint8_t> request,
                                                   std::span<const uint8_t> response) {
  // The hub pairs each reply with its request by address and function code, so both share response[0].
  if (address != this->address_ || request.size() < 5 || response.empty())
    return;

  switch (static_cast<modbus::FunctionCode>(response[0])) {
    case modbus::FunctionCode::READ_HOLDING_REGISTERS:
      // Function code, byte count, register values
      if (response.size() < 2 || response[1] != response.size() - 2) {
        ESP_LOGW(TAG, "Malformed read response from 0x%02X", address);
        return;
      }
      this->publish_registers_(encode_uint16(request[1], request[2]), response.subspan(2));
      break;
    case modbus::FunctionCode::WRITE_SINGLE_REGISTER:
      // The display changed a setting; the reply echoes register address and value.
      if (response.size() == 5)
        this->publish_registers_(encode_uint16(response[1], response[2]), response.subspan(3));
      break;
    default:
      break;
  }
}

void HofmanEnergyAvarmaComponent::publish_registers_(uint16_t start_address, std::span<const uint8_t> values) {
  const size_t count = values.size() / 2;
  for (auto *item : this->passive_items_) {
    const uint16_t address = item->get_address();
    if (address < start_address || address - start_address >= count)
      continue;
    const size_t index = address - start_address;
    item->publish_register(encode_uint16(values[index * 2], values[index * 2 + 1]));
  }
}
#endif

}  // namespace esphome::hofman_energy_avarma
