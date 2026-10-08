# Changelog

## [2.2.0](https://github.com/g4bri3lDev/kaco-modbus-hass/compare/v2.1.0...v2.2.0) (2026-10-08)


### Features

* reject inverters from other brands, matching core ([3f321da](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/3f321da0c8171c4989d46e550f9186192622de4f))
* require Home Assistant 2026.10.0 for the shared Modbus connection ([1f5efa7](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/1f5efa76d84efa8cf103027af85a82035bb0c416))


### Bug fixes

* require kaco-modbus as a minimum, as hassfest asks ([7a7b4c4](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/7a7b4c48380c1f1b306d29eca0ff86b5c34426b8))

## [2.1.0](https://github.com/g4bri3lDev/kaco-modbus-hass/compare/v2.0.0...v2.1.0) (2026-09-02)


### Features

* name the integration KACO Modbus, matching core ([b6404de](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/b6404de0312328bf5f2ab3ad69d38185503ba12f))

## [2.0.0](https://github.com/g4bri3lDev/kaco-modbus-hass/compare/v1.0.1...v2.0.0) (2026-08-25)


### ⚠ BREAKING CHANGES

* the domain changed, so Home Assistant treats this as a different integration. Delete the old `kaco` config entry before adding this one, or the entities collide and come back suffixed, which breaks anything referencing them — the Energy dashboard included.

### Features

* rename the domain to kaco_modbus ([a314870](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/a3148703d37d0f9a7d8ffcde1ed6fcd9589fec82))


### Documentation

* add AGENTS.md ([a507d19](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/a507d19a7080efab86fe8a1d4ce0ab505b19ded2))
* correct how the two integrations divide ([11ad2c0](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/11ad2c0e4205f25c003fe199368362ebef79bc61))
* say where the domain-naming rule actually comes from ([835072c](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/835072ce7eafe12072198224800f995b13ec27be))

## [1.0.1](https://github.com/g4bri3lDev/kaco-modbus-hass/compare/v1.0.0...v1.0.1) (2026-08-23)


### Bug fixes

* stop publishing readings the inverter parks at zero overnight ([1c104ea](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/1c104ea787afb606a37b11b8e1ac6ceb2127f782))

## 1.0.0 (2026-08-23)


### Features

* monitor and control KACO inverters in Home Assistant ([976e675](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/976e67545809151e12c638ed3ef4d317c5959f40))


### CI

* add HACS manifest, release-please and CI ([1ce859e](https://github.com/g4bri3lDev/kaco-modbus-hass/commit/1ce859e0e53e4aca507f460e53ea8cadaee03ea9))
