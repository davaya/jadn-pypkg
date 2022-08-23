# JADN TODO Items

## Bugs
* ArrayOf(Enum[Etype]) fails when Etype is Enumerated.  Needed to add/remove ID option.

## Minor
* load and save - dict options with string serialization
* convert/
  - add logical/information detail styles to dot
* transform/resolve - actuator profile integration
  - resolver unit tests

## Major
* Class inheritance pre-processor:
  - Link(type, key) -- for mixed types in container - unique key 
  - Array-major or Choice-major style
* Verbose/Compact/Concise instance conversion
* Classes for JADN types, pull parser deserializer interface
* Web tool / playground