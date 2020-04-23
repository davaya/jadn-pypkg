**********************************
JSON Abstract Data Notation (JADN)
**********************************

This Python package contains software for processing and using JADN Information Models
to serialize and validate application data.  The software is organized by function:

* **core:** Load, validate, and save a JADN schema.  Defined constants for the JADN data format.
* **codec:** Validate, encode, and decode application data using a JADN schema
* **convert:** Convert a JADN schema to a documentation format

  * text-based Interface Definition Language (IDL)
  * html tables
  * markdown tables
  * JSON with JADN whitespacing

* **transform:** Process a JADN schema to produce another JADN schema

  * resolve definitions from separate schemas into a single schema (include/import)
  * split a schema that defines multiple objects into separate schemas for each object
  * remove unreferenced definitions
  * remove or truncate comments to a fixed width

* **translate:** Convert a JADN schema into a concrete schema language

  * JSON Schema
  * XSD
  * CDDL
  * Protobuf

The JADN schema language is defined in https://github.com/oasis-tcs/openc2-jadn/blob/working/jadn-v1.0-wd01.md.

Quickstart
##########

The quickstart.py script in https://github.com/davaya/jadn-pypkg/tree/master/distribution
illustrates how to use these functions:

* define and validate a small schema
* display the schema in IDL format
* truncate comments
* translate to JSON Schema (translator requires metadata for scheme $id and the type to be validated)
* validate and serialize test messages:

  * JSON data format
  * Optimized (minified) JSON data format